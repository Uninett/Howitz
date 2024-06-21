import os
from enum import Enum

from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import login_user, current_user, logout_user

from datetime import datetime, timezone, timedelta

from werkzeug.exceptions import BadRequest, InternalServerError, MethodNotAllowed
from zinolib.controllers.zino1 import Zino1EventManager, RetryError, EventClosedError, UpdateHandler, LostConnectionError
from zinolib.event_types import Event, AdmState, PortState, BFDState, ReachabilityState, LogEntry, HistoryEntry
from zinolib.compat import StrEnum
from zinolib.ritz import AuthenticationError

from howitz.users.utils import authenticate_user

from .config.defaults import DEFAULT_TIMEZONE
from .utils import login_check, date_str_without_timezone, shorten_downtime, calculate_event_age_no_seconds

main = Blueprint('main', __name__)


# TODO: Should be configurable
class EventColor(StrEnum):
    RED = "red"
    BLUE = "cyan"
    GREEN = "green"
    YELLOW = "yellow"
    DEFAULT = ""


# Inspired by https://stackoverflow.com/a/54732120
class EventSort(Enum):
    # Name, relevant event attribute, is_reversed, displayed name, description
    AGE = "age", "opened", True, "Age", "Newest events first"
    AGE_REV = "age-rev", "opened", False, "Age reversed", "Oldest events first"
    UPD = "upd", "updated", False, "Activity", "Events with the oldest update date first"
    UPD_REV = "upd-rev", "updated", True, "Activity reversed", "Events with the most recent update date first"
    DOWN = "down", "get_downtime", True, "Downtime", "Events with longest downtime first"
    DOWN_REV = "down-rev", "get_downtime", False, "Downtime reversed", "Events with shortest/none downtime first"

    LASTTRANS = ("lasttrans", "updated", True, "Last transaction",
                 "Events with the most recent update date first, all IGNORED events are at the bottom")
    SEVERITY = "severity", "", True, "Severity", "Events with highest priority first, grouped by event type. Priority takes into account both whether event signifies any disturbance, event's administrative phase and event's type, so there might not be continuous blocks of color"
    DEFAULT = "raw", "", None, "Raw", "The same order in which Zino server sends events (by ID, ascending)"

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    def __init__(self, _: str, attribute: str = None, reversed: bool = None, display_name: str = None, description: str = None):
        self._attribute = attribute
        self._reversed = reversed
        self._display_name = display_name
        self._description = description

    def __str__(self):
        return self.value

    @property
    def attribute(self):
        return self._attribute

    @property
    def reversed(self):
        return self._reversed

    @property
    def display_name(self):
        return self._display_name

    @property
    def description(self):
        return self._description


def auth_handler(username, password):
    # check user credentials in database
    with current_app.app_context():
        user = authenticate_user(current_app.database, username, password)
        current_app.logger.debug('User %s', user)

        connect_to_zino(user.username, user.token)

        if current_app.event_manager.is_authenticated:  # is zino authenticated
            current_app.logger.debug('User is Zino authenticated %s', current_app.event_manager.is_authenticated)
            current_app.logger.debug('HOWITZ CONFIG %s', current_app.howitz_config)
            login_user(user, remember=True)
            flash('Logged in successfully.')
            session["selected_events"] = {}
            session["expanded_events"] = {}
            session["errors"] = {}
            session["event_ids"] = []
            session["sort_by"] = current_app.howitz_config.get("sort_by", "raw")
            session["events_last_refreshed"] = None
            return user

        raise AuthenticationError('Unexpected error on Zino authentication')


def logout_handler():
    with current_app.app_context():
        logged_out = logout_user()
        current_app.logger.debug('User logged out %s', logged_out)
        current_app.event_manager.disconnect()
        current_app.logger.debug("Zino session was disconnected")
        flash('Logged out successfully.')
        session.pop('expanded_events', {})
        session.pop('selected_events', {})
        session.pop('errors', {})
        session.pop('event_ids', [])
        session.pop('sort_by', "raw")
        session.pop('events_last_refreshed', None)
        current_app.cache.clear()
        current_app.logger.info("Logged out successfully.")


def connect_to_updatehandler():
    if current_app.event_manager.is_authenticated:  # is zino authenticated
        current_app.updater = UpdateHandler(current_app.event_manager, autoremove=current_app.zino_config.autoremove)
        current_app.updater.connect()
        current_app.logger.debug('UpdateHandler %s', current_app.updater)
        return True
    return False


def connect_to_zino(username, token):
    if not current_app.event_manager.is_connected:
        current_app.event_manager = Zino1EventManager.configure(current_app.zino_config)
        current_app.event_manager.connect()
        current_app.logger.info('Connected to Zino %s', current_app.event_manager.is_connected)

    if not current_app.event_manager.is_authenticated:
        current_app.event_manager.authenticate(username=username, password=token)
        current_app.logger.info('Authenticated in Zino %s', current_app.event_manager.is_authenticated)

    connect_to_updatehandler()


def clear_ui_state():
    with current_app.app_context():
        session["selected_events"] = {}
        session["expanded_events"] = {}
        session["errors"] = {}
        session["event_ids"] = []
        session["events_last_refreshed"] = None
        session.modified = True

        current_app.cache.clear()


def get_current_events():
    try:
        current_app.event_manager.get_events()
    except RetryError as retryErr:  # Intermittent error in Zino
        current_app.logger.exception('RetryError when fetching current events %s', retryErr)
        try:
            current_app.event_manager.get_events()
        except RetryError as retryErr:  # Intermittent error in Zino
            current_app.logger.exception('RetryError when fetching current events after retry, %s', retryErr)
            raise
    events = current_app.event_manager.events

    # Cache current events
    current_app.cache.set("events", events)
    # Save current events' IDs
    session["event_ids"] = list(events.keys())
    session.modified = True

    table_events = get_sorted_table_event_list(events)
    return table_events


def get_sorted_table_event_list(events: dict):
    events_sorted = sort_events(events, sort_by=EventSort(session["sort_by"]))
    table_events = []
    for c in events_sorted.values():
        table_events.append(create_table_event(c, expanded=str(c.id) in session["expanded_events"],
                                               selected=str(c.id) in session["selected_events"]))

    session["events_last_refreshed"] = datetime.now(timezone.utc)
    return table_events


def update_events():
    updated_ids = set()
    if current_app.updater is None:
        return updated_ids

    while True:
        updated = current_app.updater.get_event_update()
        if not updated:
            break
        updated_ids.add(updated)

    return updated_ids


def refresh_current_events():
    if current_app.updater is None:
        updates_ok = connect_to_updatehandler()
        if not updates_ok:
            raise LostConnectionError("Could not establish connection to UpdateHandler")

    event_ids = update_events()
    current_app.logger.debug('UPDATED EVENT IDS %s', event_ids)

    removed_events = []
    modified_events = []
    added_events = []
    removed = current_app.event_manager.removed_ids
    existing = session["event_ids"]
    current_events = current_app.cache.get("events") or {}
    is_resort = None  # Re-sort cached events list if any new events added, or any modified
    for i in event_ids:
        if i in removed:
            removed_events.append(i)
            if i in existing:
                existing.remove(i)
            current_events.pop(i, None)
        elif i not in existing:
            c = current_app.event_manager.create_event_from_id(int(i))
            added_event = create_table_event(c, expanded=False, selected=False)
            added_events.append(added_event)
            existing.insert(0, int(i))
            current_events.update({i: c})
            is_resort = True
        else:
            c = current_app.event_manager.create_event_from_id(int(i))
            modified_events.append(create_table_event(c,
                                                      expanded=str(c.id) in session["expanded_events"],
                                                      selected=str(c.id) in session["selected_events"]))
            current_events.update({i: c})
            is_resort = True

    session["event_ids"] = existing
    session.modified = True
    current_app.cache.set("events", current_events)

    table_events = []
    has_stale_data = session["events_last_refreshed"] is None or (
            datetime.now(timezone.utc) - session["events_last_refreshed"]).total_seconds() > 60
    if is_resort or has_stale_data:
        table_events = get_sorted_table_event_list(current_events)

    return removed_events, modified_events, added_events, table_events


def sort_events(events_dict, sort_by: EventSort = EventSort.DEFAULT):
    current_app.logger.debug("SORTING BY %s", sort_by)

    sortmap = {
        EventSort.LASTTRANS: sort_on_lasttrans,
        EventSort.SEVERITY: sort_on_severity,
        EventSort.DOWN: sort_on_downtime,
        EventSort.DOWN_REV: sort_on_downtime,
    }

    if sort_by == EventSort.DEFAULT:
        return events_dict
    if (sort := sort_by) in sortmap:
        return sortmap.get(sort)(events_dict=events_dict, sort_by=sort)
    else:
        return general_sort_on(events_dict, sort_by)


def sort_on_lasttrans(events_dict, sort_by: EventSort.LASTTRANS):
    return {k: events_dict[k] for k in
            reversed(
                sorted(events_dict,
                       key=lambda k: (
                           0 if events_dict[k].adm_state == AdmState.IGNORED else 1,
                           getattr(events_dict[k], sort_by.attribute),
                       ), ))
            }


def sort_on_severity(events_dict, sort_by: EventSort.SEVERITY):
    return {k: events_dict[k] for k in sorted(events_dict,
                                              key=lambda k: (
                                                  get_priority(events_dict[k]),
                                                  events_dict[k].type,
                                              ), reverse=sort_by.reversed)}


def sort_on_downtime(events_dict, sort_by: EventSort in [EventSort.DOWN, EventSort.DOWN_REV]):
    return {k: events_dict[k] for k in sorted(events_dict,
                                              key=lambda k: (
                                                  timedelta() if not hasattr(events_dict[k], sort_by.attribute) else
                                                  events_dict[k].get_downtime(),
                                              ), reverse=sort_by.reversed)}


def general_sort_on(events_dict, sort_by: EventSort):
    return {k: events_dict[k] for k in sorted(events_dict,
                                              key=lambda k: (
                                                  getattr(events_dict[k], sort_by.attribute),
                                              ), reverse=sort_by.reversed)}


def get_priority(event: Event):
    """
    Priorities are as follows:
      - `0` = Lowest
      - `1` = Low
      - `2` = Medium
      - `3` = High
      - `4` = Highest
    :param event:
    :return: priority as int, where `0` is lowest, and `4` is the highest priority
    """
    if event.is_down() and event.adm_state == AdmState.OPEN:
        return 4
    if event.adm_state in [AdmState.WORKING, AdmState.WAITING]:
        return 3
    if event.adm_state == AdmState.IGNORED:
        return 1
    if event.adm_state == AdmState.CLOSED:
        return 0
    return 2


# todo remove all use of helpers from curitz
def create_table_event(event, expanded=False, selected=False):
    common = {}

    try:
        common["color"] = color_code_event(event)
        common["op_state"] = event.op_state
        common["description"] = event.description
        common["port"] = event.port

        common["age"] = calculate_event_age_no_seconds(event.opened)

        if event.type == Event.Type.PORTSTATE:
            common["downtime"] = shorten_downtime(event.get_downtime())
        else:
            common["downtime"] = ""
    except Exception:
        raise

    common.update(vars(event))
    table_event = {
        "event": common
    }
    if expanded:
        table_event["event_attr"], table_event["event_logs"], table_event["event_history"], table_event["event_msgs"] = (
            get_event_details(int(event.id)))
        table_event["expanded"] = expanded

    if selected:
        table_event["selected"] = selected

    return table_event


# fixme implementation copied from curitz
def color_code_event(event):
    if event.adm_state == AdmState.IGNORED:
        return EventColor.BLUE
    elif event.adm_state == AdmState.CLOSED:
        return EventColor.GREEN
    elif ((event.type == Event.Type.PORTSTATE and event.port_state in [PortState.DOWN,
                                                                       PortState.LOWER_LAYER_DOWN])
          or (event.type == Event.Type.BGP and event.bgp_OS == "down")
          or (event.type == Event.Type.BFD and event.bfd_state == BFDState.DOWN)
          or (event.type == Event.Type.REACHABILITY and event.reachability == ReachabilityState.NORESPONSE)
          or (event.type == Event.Type.ALARM and event.alarm_count > 0)):
        if event.adm_state == AdmState.OPEN:
            return EventColor.RED
        elif event.adm_state in [AdmState.WORKING, AdmState.WAITING]:
            return EventColor.YELLOW
    else:
        return EventColor.DEFAULT


def format_dt_event_attrs(event: dict):
    if event["lasttrans"]:
        event.update(lasttrans=date_str_without_timezone(event["lasttrans"]))

    if event["opened"]:
        event.update(opened=date_str_without_timezone(event["opened"]))

    if event["updated"]:
        event.update(updated=date_str_without_timezone(event["updated"]))

    return event


def format_dt_message_entries(messages: list):
    res = []
    for m in messages:
        if type(m) == LogEntry:
            res.append(LogEntry(date=date_str_without_timezone(m.date), log=m.log))
        elif type(m) == HistoryEntry:
            res.append(HistoryEntry(date=date_str_without_timezone(m.date), log=m.log, user=m.user))

    return res


def get_event_details(id):
    try:
        event_attr = vars(current_app.event_manager.create_event_from_id(int(id)))
        format_dt_event_attrs(event_attr)
    except RetryError as retryErr:  # Intermittent error in Zino
        current_app.logger.exception('RetryError when fetching event details %s', retryErr)
        try:
            event_attr = vars(current_app.event_manager.create_event_from_id(int(id)))
            format_dt_event_attrs(event_attr)
        except RetryError as retryErr:  # Intermittent error in Zino
            current_app.logger.exception('RetryError when fetching event details after retry, %s', retryErr)
            raise

    event_logs = current_app.event_manager.get_log_for_id(int(id))
    event_history = current_app.event_manager.get_history_for_id(int(id))

    event_msgs = format_dt_message_entries(event_logs + event_history)

    return event_attr, event_logs, event_history, event_msgs


@main.route('/')
@main.route('/events')
@login_check()
def index():
    clear_ui_state()
    return render_template('/views/events.html')


@main.get('/footer')
def footer():
    tz = current_app.howitz_config["timezone"]  # Get raw string from config. Accepted values are 'UTC' or 'LOCAL'.
    if tz == 'LOCAL':  # Change to a specific timezone name if 'LOCAL'
        tz = datetime.now(timezone.utc).astimezone().tzinfo
    elif not tz == DEFAULT_TIMEZONE:  # Fall back to default if invalid value is provided
        tz = f"{DEFAULT_TIMEZONE} (default)"

    return render_template('/components/footer/footer-info.html',
                           refresh_interval=current_app.howitz_config["refresh_interval"],
                           timezone=tz)


@main.route('/login')
def login():
    with current_app.app_context():
        current_app.logger.debug('current user is authenticated %s', current_user.is_authenticated)
        try:
            if current_user.is_authenticated and current_app.event_manager.is_authenticated:
                default_url = url_for('main.index')
                return redirect(default_url)
        except Exception:
            current_app.logger.exception('An error occurred at login')
            return render_template('/views/login.html')
        return render_template('/views/login.html')


@main.route('/logout')
@login_check()
def logout():
    try:
        logout_handler()
    except Exception:
        current_app.logger.exception('An error occurred at log out')
        return redirect(url_for('main.login'))
    return redirect(url_for('main.login'))


@main.route('/sign_in_form')
def sign_in_form():
    return render_template('/components/login/sign-in-form.html')


@main.route('/auth', methods=["POST"])
def auth():
    username = request.form["username"]
    password = request.form["password"]
    user = auth_handler(username, password)
    res = make_response()

    if user:  # is both zino and flask authenticated
        # redirect to /events
        res.headers['HX-Redirect'] = '/'
        return res

    res.headers['HX-Redirect'] = '/login'
    return res


@main.route('/get_events')
def get_events():
    table_events = get_current_events()

    return render_template('components/table/events-table-body.html', event_list=table_events, refresh_interval=current_app.howitz_config["refresh_interval"])


@main.route('/refresh_events')
def refresh_events():
    removed_events, modified_events, added_events, event_list = refresh_current_events()

    if event_list:
        response = make_response(render_template('/components/table/event-rows.html', event_list=event_list))
        response.headers['HX-Reswap'] = 'innerHTML'
        return response
    else:
        return render_template('/responses/updated-rows.html', modified_event_list=modified_events,
                           removed_event_list=removed_events, added_event_list=added_events)


@main.route('/events/<event_id>/expand_row', methods=["GET"])
def expand_event_row(event_id):
    event_id = int(event_id)
    selected_events = session.get("selected_events", {})

    event_attr, event_logs, event_history, event_msgs = get_event_details(event_id)
    try:
        eventobj = current_app.event_manager.create_event_from_id(event_id)
    except RetryError as retryErr:  # Intermittent error in Zino
        current_app.logger.exception('RetryError on row expand %s', retryErr)
        try:
            eventobj = current_app.event_manager.create_event_from_id(event_id)
        except RetryError as retryErr:  # Intermittent error in Zino
            current_app.logger.exception('RetryError on row expand after retry, %s', retryErr)
            raise
    event = create_table_event(eventobj)["event"]

    session["expanded_events"][str(event_id)] = ""
    session.modified = True
    current_app.logger.debug('EXPANDED EVENTS %s', session["expanded_events"])

    return render_template('/components/row/expanded-row.html', event=event, id=event_id, event_attr=event_attr,
                           event_logs=event_logs,
                           event_history=event_history, event_msgs=event_msgs,
                           is_selected=str(event_id) in selected_events)


@main.route('/events/<event_id>/collapse_row', methods=["GET"])
def collapse_event_row(event_id):
    event_id = int(event_id)
    selected_events = session.get("selected_events", {})

    try:
        eventobj = current_app.event_manager.create_event_from_id(event_id)
    except RetryError as retryErr:  # Intermittent error in Zino
        current_app.logger.exception('RetryError on row collapse %s', retryErr)
        try:
            eventobj = current_app.event_manager.create_event_from_id(event_id)
        except RetryError as retryErr:  # Intermittent error in Zino
            current_app.logger.exception('RetryError on row collapse %s', retryErr)
            raise
    event = create_table_event(eventobj)["event"]

    session["expanded_events"].pop(str(event_id), None)
    session.modified = True
    current_app.logger.debug('EXPANDED EVENTS %s', session["expanded_events"])

    return render_template('/responses/collapse-row.html', event=event, id=event_id,
                           is_selected=str(event_id) in selected_events)


@main.route('/event/<event_id>/update_status', methods=['GET', 'POST'])
def update_event_status(event_id):
    event_id = int(event_id)
    event = current_app.event_manager.create_event_from_id(int(event_id))
    current_state = event.adm_state

    if request.method == 'POST':
        selected_events = session.get("selected_events", {})

        new_state = request.form['event-state']
        new_history = request.form['event-history']

        try:
            if not current_state == new_state:
                set_state_res = current_app.event_manager.change_admin_state_for_id(event_id, AdmState(new_state))
        except EventClosedError as closedErr:
            current_app.logger.exception('EventClosedError %s', closedErr)
            raise BadRequest(description=closedErr.args[0]) from closedErr

        if new_history:
            add_history_res = current_app.event_manager.add_history_entry_for_id(event_id, new_history)

        event_attr, event_logs, event_history, event_msgs = get_event_details(event_id)
        event = create_table_event(current_app.event_manager.create_event_from_id(event_id))["event"]

        return render_template('/responses/update-event-response.html', event=event, id=event_id, event_attr=event_attr,
                               event_logs=event_logs,
                               event_history=event_history, event_msgs=event_msgs,
                               is_selected=str(event_id) in selected_events)

    elif request.method == 'GET':
        return render_template('/components/popups/modals/update-singular-event-status-modal.html',
                               id=event_id, current_state=current_state)


@main.route('/event/bulk_update_status', methods=['POST'])
def bulk_update_events_status():
    selected_events = session.get("selected_events", {})
    expanded_events = session.get("expanded_events", {})
    current_app.logger.debug('SELECTED EVENTS %s', selected_events)
    current_app.logger.debug('EXPANDED EVENTS %s', expanded_events)

    # Get new values from the requests
    new_state = request.form['event-state']
    new_history = request.form['event-history']

    # Update each selected event with new values
    for event_id in selected_events:
        try:
            if new_state:
                set_state_res = current_app.event_manager.change_admin_state_for_id(int(event_id), AdmState(new_state))
        except EventClosedError as closedErr:
            current_app.logger.exception('EventClosedError %s', closedErr)
            raise BadRequest(description=closedErr.args[0]) from closedErr

        if new_history:
            add_history_res = current_app.event_manager.add_history_entry_for_id(int(event_id), new_history)

    # Clear selected events
    session["selected_events"] = {}
    session.modified = True  # Necessary when modifying arrays/dicts/etc in flask session
    current_app.logger.debug("SELECTED EVENTS %s", session["selected_events"])

    # Rerender whole events table
    event_list = get_current_events()
    return render_template('/responses/bulk-update-events-status.html', event_list=event_list)


@main.route('/show_update_status_modal', methods=['GET'])
def show_update_events_status_modal():
    return render_template('/components/popups/modals/update-event-status-modal.html', current_state='open')


@main.route('/event/<i>/poll', methods=["POST"])
def poll(i):
    selected_events = session.get("selected_events", {})
    event_id = int(i)

    poll_res = current_app.event_manager.poll(event_id)

    if poll_res:
        event_attr, event_logs, event_history, event_msgs = get_event_details(event_id)
        event = create_table_event(current_app.event_manager.create_event_from_id(event_id))["event"]

        return render_template('/responses/update-event-response.html', event=event, id=event_id, event_attr=event_attr,
                               event_logs=event_logs,
                               event_history=event_history, event_msgs=event_msgs,
                               is_selected=str(event_id) in selected_events)
    else:
        raise InternalServerError(description=f"Unexpected error when polling event #{event_id}")


@main.route('/event/bulk_poll', methods=['POST'])
def bulk_poll():
    selected_events = session.get("selected_events", {})
    expanded_events = session.get("expanded_events", {})
    current_app.logger.debug('SELECTED EVENTS %s', selected_events)
    current_app.logger.debug('EXPANDED EVENTS %s', expanded_events)

    # Update each selected event with new values
    for event_id in selected_events:
        poll_res = current_app.event_manager.poll(int(event_id))

        if not poll_res:
            raise InternalServerError(description=f"Unexpected error when polling event #{event_id}")

    # Clear selected events
    session["selected_events"] = {}
    session.modified = True  # Necessary when modifying arrays/dicts/etc in flask session
    current_app.logger.debug("SELECTED EVENTS %s", session["selected_events"])

    # Rerender whole events table
    event_list = get_current_events()
    return render_template('/responses/bulk-update-events-status.html', event_list=event_list)


@main.route('/event/<event_id>/unselect', methods=["POST"])
def unselect_event(event_id):
    session["selected_events"].pop(event_id, None)
    session.modified = True
    current_app.logger.debug("SELECTED EVENTS %s", session["selected_events"])

    show_clear_flapping = False
    selected_event_types = session["selected_events"].values()
    if selected_event_types:  # selected events dict contains event types
        # Allow bulk clear flapping only if all of selected events are confirmed portstate events
        show_clear_flapping = all(event_type == 'portstate' for event_type in selected_event_types)

    return render_template('/responses/toggle-select.html', id=event_id, is_checked=False,
                           is_menu=len(session["selected_events"]) > 0, show_clear_flapping=show_clear_flapping)


@main.route('/event/<event_id>/select', methods=["POST"])
def select_event(event_id):
    event_type = request.form.get('eventtype')

    # Store selected event id and its type in session
    session["selected_events"][event_id] = event_type
    session.modified = True
    current_app.logger.debug("SELECTED EVENTS %s", session["selected_events"])

    selected_event_types = session["selected_events"].values()
    if not selected_event_types:  # selected events dict is empty, should not happen
        raise RuntimeError(f"Event {event_id} was not selected. Please try again.")

    # Allow bulk clear flapping only if all of selected events are confirmed portstate events
    show_clear_flapping = all(event_type == 'portstate' for event_type in selected_event_types)

    return render_template('/responses/toggle-select.html', id=event_id, is_checked=True,
                           is_menu=len(session["selected_events"]) > 0, show_clear_flapping=show_clear_flapping)


@main.route('/event/bulk_clear_flapping', methods=['POST'])
def bulk_clear_flapping():
    selected_events = session.get("selected_events", {})
    expanded_events = session.get("expanded_events", {})
    current_app.logger.debug('SELECTED EVENTS %s', selected_events)
    current_app.logger.debug('EXPANDED EVENTS %s', expanded_events)

    # Update each selected event with new values
    for event_id in selected_events:
        flapping_res = current_app.event_manager.clear_flapping(int(event_id))

        if not flapping_res:
            raise MethodNotAllowed(description='Cant clear flapping on a non-port event.')

    # Clear selected events
    session["selected_events"] = {}
    session.modified = True  # Necessary when modifying arrays/dicts/etc in flask session
    current_app.logger.debug("SELECTED EVENTS %s", session["selected_events"])

    # Rerender whole events table
    event_list = get_current_events()
    return render_template('/responses/bulk-update-events-status.html', event_list=event_list)


@main.route('/event/<i>/clear-flapping', methods=["POST"])
def clear_flapping(i):
    selected_events = session.get("selected_events", {})
    event_id = int(i)

    flapping_res = current_app.event_manager.clear_flapping(event_id)

    if flapping_res:
        event_attr, event_logs, event_history, event_msgs = get_event_details(event_id)
        event = create_table_event(current_app.event_manager.create_event_from_id(event_id))["event"]

        return render_template('/responses/update-event-response.html', event=event, id=event_id, event_attr=event_attr,
                               event_logs=event_logs,
                               event_history=event_history, event_msgs=event_msgs,
                               is_selected=str(event_id) in selected_events)
    else:
        raise MethodNotAllowed(description='Cant clear flapping on a non-port event.')


@main.route('/events/table/change_sort_by', methods=['GET', 'POST'])
def change_events_order():
    if request.method == 'POST':
        # Get new sort method from the request
        new_sort = request.form['sort-method']
        session["sort_by"] = new_sort
        session.modified = True

        # Rerender whole events table
        events = current_app.cache.get("events")
        if events:
            table_events = get_sorted_table_event_list(events)
        else:
            table_events = get_current_events()

        return render_template('/responses/resort-events.html', event_list=table_events)

    elif request.method == 'GET':
        return render_template('/components/popups/modals/forms/sort-table-form.html', sort_methods=EventSort,
                               current_sort=EventSort(session["sort_by"]))


@main.route('/navbar/show-user-menu', methods=["GET"])
def show_user_menu():
    return render_template('/responses/show-user-menu.html')


@main.route('/navbar/hide-user-menu', methods=["GET"])
def hide_user_menu():
    return render_template('/responses/hide-user-menu.html')


@main.route('/alert/<alert_id>/show-minimized-error', methods=["GET"])
def show_minimized_error_alert(alert_id):
    return render_template('/responses/collapse-error-alert.html', alert_id=alert_id)


@main.route('/alert/<alert_id>/show-maximized-error', methods=["GET"])
def show_maximized_error_alert(alert_id):
    err_description = session["errors"][alert_id]

    return render_template('/responses/expand-error-alert.html', alert_id=alert_id, err_description=err_description)


# TODO: replace this with some other HTMX pattern
@main.route('/get_none', methods=["GET"])
def get_none():
    return render_template('/responses/generic-hidden.html')
