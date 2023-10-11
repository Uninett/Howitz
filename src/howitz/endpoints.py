import os

import flask
from flask import Flask, render_template, request, make_response
from flask_login import LoginManager, login_required, login_user, current_user
from flask_assets import Bundle, Environment
from logging.config import dictConfig

from enum import StrEnum
from datetime import datetime, timezone
from pathlib import Path

from zinolib.ritz import ritz, parse_tcl_config
from zinolib.zino1 import Zino1EventEngine, EventAdapter, HistoryAdapter
from zinolib.event_types import EventType, Event, HistoryEntry, LogEntry, AdmState, PortState, BFDState, ReachabilityState

from howitz.users.db import UserDB
from howitz.users.utils import authenticate_user

# todo remove all use of curitz when zinolib is ready
from curitz import cli
# todo remove
import time

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

conf = parse_tcl_config("~/.ritz.tcl")['default']
session = ritz(
    conf['Server'],
    username=conf['User'],
    password=conf['Secret'],
    timeout=30,
)
session.connect()

event_engine = Zino1EventEngine(session)


@login_manager.user_loader
def load_user(user_id):
    user = database.get(user_id)
    app.logger.info('User "%s" logged in', user.username)
    app.logger.debug('User "%s"', user)
    return user


with app.app_context():
    expanded_events = []


class EventColor(StrEnum):
    RED = "red"
    BLUE = "cyan"
    GREEN = "green"
    YELLOW = "yellow"
    DEFAULT = ""


def get_current_events():
    event_engine.get_events()
    events = event_engine.events
    # app.logger.debug('EVENTS %s', events)

    events_sorted = {k: events[k] for k in sorted(events,
                                                  key=lambda k: (
                                                      0 if events[k].adm_state == AdmState.IGNORED else 1,
                                                      events[k].updated,
                                                  ), reverse=True)}

    table_events = []
    for c in events_sorted.values():
        # app.logger.debug('EVENT %s', c)
        table_events.append(create_table_event(c))

    # app.logger.debug('Table events %s', table_events)

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
    event = event_engine.create_event_from_id(int(id))
    attr_list = [':'.join([str(i[0]), str(i[1])]) for i in event]
    # app.logger.debug('EVENT %s', attr_list)

    # fixme is there a better way to do switch statements in Python?
    return {
        list: attr_list,
        dict: vars(event),
    }[res_format]


def get_event_details(id):
    event_attr = get_event_attributes(int(id))
    event_logs = event_engine.get_log_for_id(int(id))
    event_history = event_engine.get_history_for_id(int(id))
    # app.logger.debug('EVENT ATTRIBUTES %s', event_attr)
    # app.logger.debug('EVENT LOGS %s', event_logs)
    # app.logger.debug('EVENT HISTORY %s', event_history)

    event_msgs = event_logs + event_history

    # app.logger.debug('EVENT MESSAGES %s', event_msgs)

    return event_attr, event_logs, event_history, event_msgs


@app.route('/')
@app.route('/hello-world')
@login_required
def index():
    exemplify_loop = list('abracadabra')
    return render_template('index.html', example_list=exemplify_loop)


@app.route('/events')
@login_required
def events():
    # current_app["expanded_events"] = []
    return render_template('/views/events.html')

@app.route('/login')
def login():
    app.logger.debug('current user is authenticated %s', current_user.is_authenticated)
    if current_user.is_authenticated:
        default_url = flask.url_for('index')
        # app.logger.debug('DEFAULT URL %s', default_url)
        return flask.redirect(default_url)
    else:
        return render_template('/views/login.html')

@app.route('/sign_in_form')
def sign_in_form():
    return render_template('/components/login/sign-in-form.html')

@app.route('/auth', methods=["POST"])
def auth():
    username = request.form["username"]
    password = request.form["password"]

    user = authenticate_user(username, password)
    if user:
        app.logger.debug('User %s', user)
        login_user(user)
        flask.flash('Logged in successfully.')

        # redirect to /events
        resp = make_response()
        resp.headers['HX-Redirect'] = '/events'
        return resp
    else:
        pass
        # raise error
        # show login form again with error?
        # todo fix swap with err
        resp = make_response()
        resp.headers['HX-Redirect'] = '/login'
        return resp


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
    # app.logger.debug('EXPANDED EVENTS %s', expanded_events)

    event_attr, event_logs, event_history, event_msgs = get_event_details(i)
    event = create_table_event(event_engine.create_event_from_id(int(i)))

    return render_template('/components/row/expanded-row.html', event=event, id=i, event_attr=event_attr,
                           event_logs=event_logs,
                           event_history=event_history, event_msgs=event_msgs)


@app.route('/events/<i>/collapse_row', methods=["GET"])
def collapse_event_row(i):
    with app.app_context():
        expanded_events.remove(i)
    # app.logger.debug('EXPANDED EVENTS %s', expanded_events)

    event = create_table_event(event_engine.create_event_from_id(int(i)))

    return render_template('/responses/collapse-row.html', event=event, id=i)


@app.route('/event/<i>/update_status', methods=['GET', 'POST'])
def update_event_status(i):
    event_id = int(i)
    current_state = get_event_attributes(event_id)['adm_state']

    if request.method == 'POST':
        new_state = request.form['event-state']
        new_history = request.form['event-history']
        # app.logger.debug('NEW STATE %s', new_state)
        # app.logger.debug('NEW HISTORY %s', new_history)

        if not current_state == new_state:
            set_state_res = EventAdapter.set_admin_state(session, event_engine.events.get(event_id),
                                                         AdmState(new_state))
            # app.logger.debug('SET_STATE RES %s', set_state_res)

        if new_history:
            add_history_res = HistoryAdapter.add(session, new_history,
                                                 event_engine.events.get(event_id))
            # app.logger.debug('ADD_HISTORY RES %s', add_history_res)

        event_attr, event_logs, event_history, event_msgs = get_event_details(event_id)
        event = create_table_event(event_engine.create_event_from_id(event_id))

        return render_template('/components/row/expanded-row.html', event=event, id=event_id, event_attr=event_attr,
                               event_logs=event_logs,
                               event_history=event_history, event_msgs=event_msgs)

    elif request.method == 'GET':
        # app.logger.debug('CURRENT STATE %s', current_state)
        return render_template('/responses/get-update-event-status-form.html', id=i, current_state=current_state)


@app.route('/event/<i>/update_status/cancel', methods=["GET"])
def cancel_update_event_status(i):
    return render_template('/responses/hide-update-event-status-form.html', id=i)


# TODO: replace this with some other HTMX pattern
@app.route('/get_none', methods=["GET"])
def get_none():
    return render_template('/responses/generic-hidden.html')
