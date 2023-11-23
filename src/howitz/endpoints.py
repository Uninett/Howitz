import os

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
from logging.config import dictConfig

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
                login_user(user)
                flash('Logged in successfully.')
                session["selected_events"] = []
                return user
    return None


def logout_handler():
    with current_app.app_context():
        logged_out = logout_user()
        current_app.logger.debug('User logged out %s', logged_out)
        current_app.event_manager.disconnect()
        current_app.logger.debug("Zino session was disconnected")
        flash('Logged out successfully.')
        session.pop('selected_events', [])
        current_app.logger.info("Logged out successfully.")


def get_current_events():
    current_app.event_manager.get_events()
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

    return table_events


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
@main.route('/hello-world')
@login_check()
def index():
    exemplify_loop = list('abracadabra')
    return render_template('index.html', example_list=exemplify_loop)


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


@main.route('/events')
@login_check()
def events():
    # current_app["expanded_events"] = []
    return render_template('/views/events.html')


@main.route('/auth', methods=["POST"])
def auth():
    username = request.form["username"]
    password = request.form["password"]
    user = auth_handler(username, password)
    res = make_response()

    if user:  # is both zino and flask authenticated
        # redirect to /events
        res.headers['HX-Redirect'] = '/events'
        return res

    res.headers['HX-Redirect'] = '/login'
    return res


@main.route('/events-table.html')
def events_table():
    return render_template('/components/table/events-table.html')


@main.route('/get_events')
def get_events():
    session["expanded_events"] = session.get("expanded_events", []) or []
    table_events = get_current_events()

    return render_template('/components/table/event-rows.html', event_list=table_events)


@main.route('/events/<event_id>/expand_row', methods=["GET"])
def expand_event_row(event_id):
    event_id = int(event_id)
    expanded_events = session.get("expanded_events", []) or []
    expanded_events.append(event_id)
    current_app.logger.debug('EXPANDED EVENTS %s', expanded_events)

    event_attr, event_logs, event_history, event_msgs = get_event_details(event_id)
    event = create_table_event(current_app.event_manager.create_event_from_id(event_id))

    return render_template('/components/row/expanded-row.html', event=event, id=event_id, event_attr=event_attr,
                           event_logs=event_logs,
                           event_history=event_history, event_msgs=event_msgs)

    return render_template('/components/row/expanded-row.html', event=event, id=i, event_attr=event_attr,
                           event_logs=event_logs,
                           event_history=event_history, event_msgs=event_msgs, is_selected=i in selected_events)

@main.route('/events/<event_id>/collapse_row', methods=["GET"])
def collapse_event_row(event_id):
    event_id = int(event_id)
    expanded_events = session.get("expanded_events", []) or []
    try:
        expanded_events.remove(event_id)
    except ValueError:
        pass
    session["expanded_events"] = expanded_events
    current_app.logger.debug('EXPANDED EVENTS %s', expanded_events)

    event = create_table_event(current_app.event_manager.create_event_from_id(event_id))

    return render_template('/responses/collapse-row.html', event=event, id=event_id)


@main.route('/event/<event_id>/update_status', methods=['GET', 'POST'])
def update_event_status(event_id):
    event_id = int(event_id)
    event = current_app.event_manager.create_event_from_id(int(event_id))
    current_state = event.adm_state

    if request.method == 'POST':
        new_state = request.form['event-state']
        new_history = request.form['event-history']

        if not current_state == new_state:
            set_state_res = current_app.event_manager.change_admin_state_for_id(event_id, AdmState(new_state))

        if new_history:
            add_history_res = current_app.event_manager.add_history_entry_for_id(event_id, new_history)

        event_attr, event_logs, event_history, event_msgs = get_event_details(event_id)
        event = create_table_event(current_app.event_manager.create_event_from_id(event_id))

        return render_template('/components/row/expanded-row.html', event=event, id=event_id, event_attr=event_attr,
                               event_logs=event_logs,
                               event_history=event_history, event_msgs=event_msgs)

    elif request.method == 'GET':
        return render_template('/responses/get-update-event-status-form.html', id=event_id, current_state=current_state)


@main.route('/event/<event_id>/update_status/cancel', methods=["GET"])
def cancel_update_event_status(event_id):
    return render_template('/responses/hide-update-event-status-form.html', id=event_id)



@main.route('/event/<i>/unselect', methods=["GET"])
def unselect_event(i):
    with current_app.app_context():
        session["selected_events"].remove(i)
    print("SELECTED EVENTS", session["selected_events"])

    return render_template('/components/row/event-unchecked-box.html', id=i)


@main.route('/event/<i>/select', methods=["GET"])
def select_event(i):
    with current_app.app_context():
        session["selected_events"].append(i)
    print("SELECTED EVENTS", session["selected_events"])

    return render_template('/components/row/event-checked-box.html', id=i)


# TODO: replace this with some other HTMX pattern
@main.route('/get_none', methods=["GET"])
def get_none():
    return render_template('/responses/generic-hidden.html')
