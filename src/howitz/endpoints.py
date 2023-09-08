from enum import StrEnum

from flask import Flask, render_template, request
from flask_assets import Bundle, Environment

import logging
from datetime import datetime, timezone

# todo remove all use of curitz when zinolib is ready
from curitz import cli

from zinolib.zino1 import Zino1EventEngine, EventAdapter, HistoryAdapter, convert_timestamp
from zinolib.event_types import EventType, Event, EventEngine, HistoryEntry, LogEntry, AdmState, PortState, BFDState, \
    ReachabilityState
from zinolib.ritz import ritz, parse_tcl_config

# todo remove
import time

app = Flask(__name__)
LOG = logging.getLogger(__name__)

with app.app_context():
    expanded_events = []

assets = Environment(app)
css = Bundle("main.css", output="dist/main.css")

assets.register("css", css)
css.build()

conf = parse_tcl_config("~/.ritz.tcl")['default']
session = ritz(
    conf['Server'],
    username=conf['User'],
    password=conf['Secret'],
    timeout=30,
)
session.connect()

event_engine = Zino1EventEngine(session)


class EventColor(StrEnum):
    RED = "red"
    BLUE = "cyan"
    GREEN = "green"
    YELLOW = "yellow"
    DEFAULT = ""


def get_current_events():
    event_engine.get_events()
    events = event_engine.events
    # print("EVENTS", events)

    events_sorted = {k: events[k] for k in sorted(events,
                                                  key=lambda k: (
                                                      0 if events[k].adm_state == AdmState.IGNORED else 1,
                                                      events[k].updated,
                                                  ), reverse=True)}

    table_events = []
    for c in events_sorted.values():
        # print("EVENT", c)
        table_events.append(create_table_event(c))

    # print('Table events', table_events)

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
        # common["age"] = cli.strfdelta(age, "{days:2d}d {hours:02}:{minutes:02}")
        # common["age"] = '{day:2d}d {hours:02}:{minutes:02}'.format(age, "day", "hours", "minutes")
        common["age"] = age
        # common["age"] = age.strftime('{days:2d}d {hours:02}:{minutes:02}')

        if event.type == Event.Type.PORTSTATE:
            # common["downtime"] = cli.downtimeShortner(event.get_downtime())
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
    # print('EVENT', attr_list)

    # fixme is there a better way to do switch statements in Python?
    return {
        list: attr_list,
        dict: vars(event),
        # dict: session.clean_attributes(vars(event)),
        # dict: dict(filter(lambda i: i[1] is not None, session.clean_attributes(event_adapter.attrlist_to_attrdict(attr_list)).items())),
    }[res_format]


def get_event_details(id):
    event_attr = get_event_attributes(int(id))
    event_logs = event_engine.get_log_for_id(int(id))
    event_history = event_engine.get_history_for_id(int(id))
    # print('EVENT ATTR', event_attr)
    # print('EVENT LOGS', event_logs)
    # print('EVENT HISTORY', event_history)

    event_msgs = event_logs + event_history

    # print('EVENT MSGS', event_msgs)

    return event_attr, event_logs, event_history, event_msgs


@app.route('/')
@app.route('/hello-world')
def index():
    exemplify_loop = list('abracadabra')
    return render_template('index.html', example_list=exemplify_loop)


@app.route('/events')
def events():
    # current_app["expanded_events"] = []
    return render_template('/views/events.html')


@app.route('/events-table.html')
def events_table():
    return render_template('/components/table/events-table.html')


@app.route('/get_events')
def get_events():
    table_events = get_current_events()

    # return render_template('/ui/components/event-list.html', event_list=table_events)
    return render_template('/components/table/event-rows.html', event_list=table_events)


@app.route('/events/<i>/expand_row', methods=["GET"])
def expand_event_row(i):
    with app.app_context():
        expanded_events.append(i)
    # print("EXPANDED EVENTS", expanded_events)

    event_attr, event_logs, event_history, event_msgs = get_event_details(i)
    event = create_table_event(event_engine.create_event_from_id(int(i)))

    return render_template('/components/row/expanded-row.html', event=event, id=i, event_attr=event_attr,
                           event_logs=event_logs,
                           event_history=event_history, event_msgs=event_msgs)


@app.route('/events/<i>/collapse_row', methods=["GET"])
def collapse_event_row(i):
    with app.app_context():
        expanded_events.remove(i)
    # print("EXPANDED EVENTS", expanded_events)

    event = create_table_event(event_engine.create_event_from_id(int(i)))

    return render_template('/responses/collapse-row.html', event=event, id=i)
    # return render_template('ui/components/event-row-collapsed.html', event=event, id=i)


@app.route('/event/<i>/update_status', methods=['GET', 'POST'])
def update_event_status(i):
    event_id = int(i)
    current_state = get_event_attributes(event_id)['adm_state']

    if request.method == 'POST':
        new_state = request.form['event-state']
        new_history = request.form['event-history']
        # print('NEW STATE', new_state)
        # print('NEW HISTORY', new_history)

        if not current_state == new_state:
            set_state_res = EventAdapter.set_admin_state(session, event_engine.events.get(event_id),
                                                         AdmState(new_state))
            # print("SET_STATE RES", set_state_res)

        if new_history:
            add_history_res = HistoryAdapter.add(session, new_history,
                                                 event_engine.events.get(event_id))
            # print("ADD_HISTORY RES", add_history_res)

        event_attr, event_logs, event_history, event_msgs = get_event_details(event_id)
        event = create_table_event(event_engine.create_event_from_id(event_id))

        return render_template('/components/row/expanded-row.html', event=event, id=event_id, event_attr=event_attr,
                               event_logs=event_logs,
                               event_history=event_history, event_msgs=event_msgs)

    elif request.method == 'GET':
        # print("CURRENT STATE", current_state)
        return render_template('/responses/get-update-event-status-form.html', id=i, current_state=current_state)


@app.route('/event/<i>/update_status/cancel', methods=["GET"])
def cancel_update_event_status(i):
    return render_template('/responses/hide-update-event-status-form.html', id=i)


# TODO: replace this with some other HTMX pattern
@app.route('/get_none', methods=["GET"])
def get_none():
    return render_template('ui-generic-hidden.html')
