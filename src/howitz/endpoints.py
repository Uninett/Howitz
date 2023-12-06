import os
import uuid

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

from datetime import datetime, timezone

from zinolib.controllers.zino1 import Zino1EventManager
from zinolib.event_types import Event, AdmState, PortState, BFDState, ReachabilityState
from zinolib.compat import StrEnum

from howitz.users.utils import authenticate_user
from .utils import login_check

main = Blueprint('main', __name__)


# TODO: Should be configurable
class EventColor(StrEnum):
    RED = "red"
    BLUE = "cyan"
    GREEN = "green"
    YELLOW = "yellow"
    DEFAULT = ""


def auth_handler(username, password):
    # check user credentials in database
    with current_app.app_context():
        user = authenticate_user(current_app.database, username, password)
        if user:  # is registered in database
            current_app.logger.debug('User %s', user)

            if not current_app.event_manager.is_connected:
                current_app.event_manager = Zino1EventManager.configure(current_app.zino_config)
                current_app.event_manager.connect()
                current_app.logger.info('Connected to Zino %s', current_app.event_manager.is_connected)

            if not current_app.event_manager.is_authenticated:
                current_app.event_manager.authenticate(username=user.username, password=user.token)
                current_app.logger.info('Authenticated in Zino %s', current_app.event_manager.is_authenticated)

            if current_app.event_manager.is_authenticated:  # is zino authenticated
                current_app.logger.debug('User is Zino authenticated %s', current_app.event_manager.is_authenticated)
                current_app.logger.debug('HOWITZ CONFIG %s', current_app.howitz_config)
                login_user(user, remember=True)
                flash('Logged in successfully.')
                session["selected_events"] = []
                session["expanded_events"] = {}
                session["errors"] = {}
                return user
    return None


def logout_handler():
    with current_app.app_context():
        logged_out = logout_user()
        current_app.logger.debug('User logged out %s', logged_out)
        current_app.event_manager.disconnect()
        current_app.logger.debug("Zino session was disconnected")
        flash('Logged out successfully.')
        session.pop('expanded_events', {})
        session.pop('selected_events', [])
        session.pop('errors', {})
        current_app.logger.info("Logged out successfully.")


def get_current_events():
    try:
        current_app.event_manager.get_events()
    except Exception:
        current_app.logger.exception('An error ocurred on event fetch')
    events = current_app.event_manager.events
    current_app.logger.debug('EVENTS %s', events)

    events_sorted = {k: events[k] for k in sorted(events,
                                                  key=lambda k: (
                                                      0 if events[k].adm_state == AdmState.IGNORED else 1,
                                                      events[k].updated,
                                                  ), reverse=True)}

    table_events = []
    for c in events_sorted.values():
        table_events.append(create_table_event(c))

    current_app.logger.debug('TABLE EVENTS %s', table_events[0])

    return table_events


def poll_current_events():
    try:
        current_app.event_manager.get_events()
    except Exception:
        current_app.logger.exception('An error ocurred on event poll')

    events = current_app.event_manager.events

    events_sorted = {k: events[k] for k in sorted(events,
                                                  key=lambda k: (
                                                      0 if events[k].adm_state == AdmState.IGNORED else 1,
                                                      events[k].updated,
                                                  ), reverse=True)}

    poll_events = []
    for c in events_sorted.values():
        poll_events.append(create_polled_event(create_table_event(c), expanded=str(c.id) in session["expanded_events"],
                                               selected=str(c.id) in session["selected_events"]))

    return poll_events


# todo remove all use of helpers from curitz
def create_table_event(event):
    common = {}

    try:
        common["color"] = color_code_event(event)
        common["op_state"] = event.op_state
        common["description"] = event.description
        common["port"] = event.port

        age = datetime.now(timezone.utc) - event.opened
        common["age"] = age

        if event.type == Event.Type.PORTSTATE:
            common["downtime"] = event.get_downtime()
        else:
            common["downtime"] = ""
    except Exception:
        raise

    common.update(vars(event))

    return common


def create_polled_event(table_event, expanded=False, selected=False):
    poll_event = {
        "event": table_event
    }
    if expanded:
        poll_event["event_attr"], poll_event["event_logs"], poll_event["event_history"], poll_event["event_msgs"] = (
            get_event_details(int(table_event["id"])))
        poll_event["expanded"] = expanded

    if selected:
        poll_event["selected"] = selected

    return poll_event


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


def get_event_attributes(id, res_format=dict):
    event = current_app.event_manager.create_event_from_id(int(id))
    event_dict = vars(event)
    attr_list = [f"{k}:{v}" for k, v in event_dict.items()]

    # fixme is there a better way to do switch statements in Python?
    return {
        list: attr_list,
        dict: event_dict,
    }[res_format]


def get_event_details(id):
    event_attr = vars(current_app.event_manager.create_event_from_id(int(id)))
    event_logs = current_app.event_manager.get_log_for_id(int(id))
    event_history = current_app.event_manager.get_history_for_id(int(id))
    current_app.logger.debug('Event: attrs %s, logs %s, history %s', event_attr, event_logs, event_history)

    event_msgs = event_logs + event_history

    return event_attr, event_logs, event_history, event_msgs


@main.route('/')
@main.route('/events')
@login_check()
def index():
    return render_template('/views/events.html', poll_interval=current_app.howitz_config["poll_interval"])


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


@main.route('/events-table.html')
def events_table():
    return render_template('/components/table/events-table.html',
                           poll_interval=current_app.howitz_config["poll_interval"])


@main.route('/get_events')
def get_events():
    table_events = get_current_events()

    return render_template('/components/table/event-rows.html', event_list=table_events)


@main.route('/poll_events')
def poll_events():
    poll_events_list = poll_current_events()

    return render_template('/components/poll/poll-rows.html', poll_event_list=poll_events_list)


@main.route('/events/<event_id>/expand_row', methods=["GET"])
def expand_event_row(event_id):
    try:
        session["expanded_events"][str(event_id)] = ""
        session.modified = True
        current_app.logger.debug('EXPANDED EVENTS %s', session["expanded_events"])
    except ValueError:
        pass

    event_id = int(event_id)
    selected_events = session.get("selected_events") or []

    event_attr, event_logs, event_history, event_msgs = get_event_details(event_id)
    event = create_table_event(current_app.event_manager.create_event_from_id(event_id))

    return render_template('/components/row/expanded-row.html', event=event, id=event_id, event_attr=event_attr,
                           event_logs=event_logs,
                           event_history=event_history, event_msgs=event_msgs,
                           is_selected=str(event_id) in selected_events)


@main.route('/events/<event_id>/collapse_row', methods=["GET"])
def collapse_event_row(event_id):
    try:
        session["expanded_events"].pop(str(event_id), None)
        session.modified = True
        current_app.logger.debug('EXPANDED EVENTS %s', session["expanded_events"])
    except ValueError:
        pass

    event_id = int(event_id)
    selected_events = session.get("selected_events") or []

    event = create_table_event(current_app.event_manager.create_event_from_id(event_id))

    return render_template('/responses/collapse-row.html', event=event, id=event_id,
                           is_selected=str(event_id) in selected_events)


@main.route('/event/<event_id>/update_status', methods=['GET', 'POST'])
def update_event_status(event_id):
    event_id = int(event_id)
    event = current_app.event_manager.create_event_from_id(int(event_id))
    current_state = event.adm_state

    if request.method == 'POST':
        selected_events = session.get("selected_events", [])

        new_state = request.form['event-state']
        new_history = request.form['event-history']

        if not current_state == new_state:
            set_state_res = current_app.event_manager.change_admin_state_for_id(event_id, AdmState(new_state))

        if new_history:
            add_history_res = current_app.event_manager.add_history_entry_for_id(event_id, new_history)

        event_attr, event_logs, event_history, event_msgs = get_event_details(event_id)
        event = create_table_event(current_app.event_manager.create_event_from_id(event_id))

        return render_template('/responses/update-event-response.html', event=event, id=event_id, event_attr=event_attr,
                               event_logs=event_logs,
                               event_history=event_history, event_msgs=event_msgs,
                               is_selected=str(event_id) in selected_events)

    elif request.method == 'GET':
        return render_template('/components/popups/modals/update-singular-event-status-modal.html',
                               id=event_id, current_state=current_state)


@main.route('/event/bulk_update_status', methods=['POST'])
def bulk_update_events_status():
    selected_events = session.get("selected_events", [])
    expanded_events = session.get("expanded_events", [])
    current_app.logger.debug('SELECTED EVENTS %s', selected_events)
    current_app.logger.debug('EXPANDED EVENTS %s', expanded_events)

    # Get new values from the requests
    new_state = request.form['event-state']
    new_history = request.form['event-history']

    # Update each selected event with new values
    for event_id in selected_events:
        if new_state:
            set_state_res = current_app.event_manager.change_admin_state_for_id(int(event_id), AdmState(new_state))

        if new_history:
            add_history_res = current_app.event_manager.add_history_entry_for_id(int(event_id), new_history)

    # Clear selected events
    session["selected_events"] = []
    session.modified = True  # Necessary when modifying arrays/dicts/etc in flask session
    current_app.logger.debug("SELECTED EVENTS %s", session["selected_events"])

    # Rerender whole events table
    poll_events_list = poll_current_events()  # Calling poll events method is needed to preserve info about which events are expanded
    return render_template('/responses/bulk-update-events-status.html', poll_event_list=poll_events_list)


@main.route('/show_update_status_modal', methods=['GET'])
def show_update_events_status_modal():
    return render_template('/components/popups/modals/update-event-status-modal.html', current_state='open')


@main.route('/event/<i>/unselect', methods=["GET"])
def unselect_event(i):
    try:
        session["selected_events"].remove(i)
        session.modified = True
        current_app.logger.debug("SELECTED EVENTS %s", session["selected_events"])
    except ValueError:
        pass

    return render_template('/responses/toggle-select.html', id=i, is_checked=False,
                           is_menu=len(session["selected_events"]) > 0)


@main.route('/event/<i>/select', methods=["GET"])
def select_event(i):
    try:
        session["selected_events"].append(i)
        session.modified = True
        current_app.logger.debug("SELECTED EVENTS %s", session["selected_events"])
    except ValueError:
        pass

    return render_template('/responses/toggle-select.html', id=i, is_checked=True,
                           is_menu=len(session["selected_events"]) > 0)


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
