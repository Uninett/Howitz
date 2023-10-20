import os

import flask
from flask import Flask, render_template, request, make_response
from flask_login import LoginManager, login_user, current_user, logout_user
from flask_assets import Bundle, Environment
from logging.config import dictConfig

from datetime import datetime, timezone
from pathlib import Path

from zinolib.controllers.zino1 import Zino1EventManager
from zinolib.event_types import Event, AdmState, PortState, BFDState, ReachabilityState
from zinolib.compat import StrEnum
from zinolib.config.zino1 import ZinoV1Config

from howitz.users.db import UserDB
from howitz.users.utils import authenticate_user, update_token
from .utils import login_check


class EventColor(StrEnum):
    RED = "red"
    BLUE = "cyan"
    GREEN = "green"
    YELLOW = "yellow"
    DEFAULT = ""


dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '%(levelname)-8s in %(funcName)-20s %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

app = Flask(__name__)

app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE=os.path.join(app.instance_path, 'howitz.sqlite3'),
)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

assets = Environment(app)
css = Bundle("main.css", output="dist/main.css")

assets.register("css", css)
css.build()

DB_URL = Path('howitz.sqlite3')
database = UserDB(DB_URL)
database.initdb()
app.logger.info('Connected to database %s', database)

config = ZinoV1Config.from_tcl('ritz.tcl')
app.logger.debug('ZinoV1Config %s', config)
event_manager = Zino1EventManager.configure(config)
app.logger.debug('Zino1EventManager %s', event_manager)


def connect_to_zino():
    event_manager.configure(config)
    event_manager.connect()
    app.logger.info('Connected to Zino %s', event_manager.is_connected)


@login_manager.user_loader
def load_user(user_id):
    user = database.get(user_id)
    app.logger.info('User "%s" logged in', user.username)
    app.logger.debug('User "%s"', user)
    return user


with app.app_context():
    expanded_events = []


@login_manager.unauthorized_handler
def unauthorized():
    logout_user()
    try:
        if event_manager.is_connected and not event_manager.is_authenticated:
            event_manager.disconnect()
            app.logger.debug("Zino session was disconnected")
    except ValueError:
        app.logger.debug("Zino session was not established")

    return flask.redirect(flask.url_for('login'))


def auth_handler(username, password):
    user = authenticate_user(username, password)
    if user:  # is authenticated
        app.logger.debug('User %s', user)

        update_token(user, zino_session.authChallenge, password)
        zino_session.authenticate(user.username, password)
        app.logger.debug('User connected to Zino %s', zino_session.connStatus)

        login_user(user)
        flask.flash('Logged in successfully.')
        return user
    return None


def get_current_events():
    event_manager.get_events()
    events = event_manager.events
    app.logger.debug('EVENTS %s', events)

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
    event = event_manager.create_event_from_id(int(id))
    attr_list = [':'.join([str(i[0]), str(i[1])]) for i in event]

    # fixme is there a better way to do switch statements in Python?
    return {
        list: attr_list,
        dict: vars(event),
    }[res_format]


def get_event_details(id):
    event_attr = get_event_attributes(int(id))
    event_logs = event_manager.get_log_for_id(int(id))
    event_history = event_manager.get_history_for_id(int(id))
    app.logger.debug('Event: attrs %s, logs %s, history %s', event_attr, event_logs, event_history)

    event_msgs = event_logs + event_history

    return event_attr, event_logs, event_history, event_msgs


@app.route('/')
@app.route('/hello-world')
@login_check(current_user, event_manager, unauthorized)
def index():
    exemplify_loop = list('abracadabra')
    return render_template('index.html', example_list=exemplify_loop)


@app.route('/login')
def login():
    app.logger.debug('current user is authenticated %s', current_user.is_authenticated)
    try:
        if current_user.is_authenticated and event_manager.is_authenticated:
            default_url = flask.url_for('index')
            return flask.redirect(default_url)
    except:
        return render_template('/views/login.html')
    return render_template('/views/login.html')


@app.route('/sign_in_form')
def sign_in_form():
    return render_template('/components/login/sign-in-form.html')


@app.route('/events')
@login_check(current_user, event_manager, unauthorized)
def events():
    # current_app["expanded_events"] = []
    return render_template('/views/events.html')


@app.route('/auth', methods=["POST"])
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


@app.route('/events-table.html')
def events_table():
    return render_template('/components/table/events-table.html')


@app.route('/get_events')
def get_events():
    table_events = get_current_events()

    return render_template('/components/table/event-rows.html', event_list=table_events)


@app.route('/events/<i>/expand_row', methods=["GET"])
def expand_event_row(i):
    with app.app_context():
        expanded_events.append(i)
    app.logger.debug('EXPANDED EVENTS %s', expanded_events)

    event_attr, event_logs, event_history, event_msgs = get_event_details(i)
    event = create_table_event(event_manager.create_event_from_id(int(i)))

    return render_template('/components/row/expanded-row.html', event=event, id=i, event_attr=event_attr,
                           event_logs=event_logs,
                           event_history=event_history, event_msgs=event_msgs)


@app.route('/events/<i>/collapse_row', methods=["GET"])
def collapse_event_row(i):
    with app.app_context():
        expanded_events.remove(i)
    app.logger.debug('EXPANDED EVENTS %s', expanded_events)

    event = create_table_event(event_manager.create_event_from_id(int(i)))

    return render_template('/responses/collapse-row.html', event=event, id=i)


@app.route('/event/<i>/update_status', methods=['GET', 'POST'])
def update_event_status(i):
    event_id = int(i)
    current_state = get_event_attributes(event_id)['adm_state']

    if request.method == 'POST':
        new_state = request.form['event-state']
        new_history = request.form['event-history']

        if not current_state == new_state:
            set_state_res = event_manager.change_admin_state_for_id(event_id, AdmState(new_state))

        if new_history:
            add_history_res = event_manager.add_history_entry_for_id(event_id, new_history)

        event_attr, event_logs, event_history, event_msgs = get_event_details(event_id)
        event = create_table_event(event_manager.create_event_from_id(event_id))

        return render_template('/components/row/expanded-row.html', event=event, id=event_id, event_attr=event_attr,
                               event_logs=event_logs,
                               event_history=event_history, event_msgs=event_msgs)

    elif request.method == 'GET':
        return render_template('/responses/get-update-event-status-form.html', id=i, current_state=current_state)


@app.route('/event/<i>/update_status/cancel', methods=["GET"])
def cancel_update_event_status(i):
    return render_template('/responses/hide-update-event-status-form.html', id=i)


# TODO: replace this with some other HTMX pattern
@app.route('/get_none', methods=["GET"])
def get_none():
    return render_template('/responses/generic-hidden.html')
