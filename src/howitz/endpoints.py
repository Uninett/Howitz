from flask import Flask, render_template, make_response, request
from flask_assets import Bundle, Environment

import logging
from datetime import datetime, timezone
import curitz

from curitz import cli
from zinolib.zino1 import Zino1EventEngine, EventAdapter, HistoryAdapter, convert_timestamp
from zinolib.event_types import EventType, Event, EventEngine, HistoryEntry, LogEntry, AdmState

app = Flask(__name__)
LOG = logging.getLogger(__name__)

assets = Environment(app)
css = Bundle("main.css", output="dist/main.css")

assets.register("css", css)
css.build()

from zinolib.ritz import ritz, parse_tcl_config

conf = parse_tcl_config("~/.ritz.tcl")['default']
session = ritz(
    conf['Server'],
    username=conf['User'],
    password=conf['Secret'],
    timeout=30,
)
session.connect()

event_engine = Zino1EventEngine(session)
event_adapter = EventAdapter()
history_adapter = HistoryAdapter()


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

    # for c in events_sorted.values():
    #     setattr(c, '_age', cli.strfdelta(datetime.now(timezone.utc) - c.opened, "{days:2d}d {hours:02}:{minutes:02}"))
    #     setattr(c, '_downtime', cli.downtimeShortner(c.get_downtime()) if c.type == Event.Type.PORTSTATE else '')
    #     print("EVENT", c)
    #     table_events.append(c)

    # print('Table events', table_events)

    return table_events


# todo remove all use of helpers from curitz
def create_table_event(event):
    common = {}

    try:
        common["op_state"] = event.op_state
        common["description"] = event.description
        common["port"] = event.port

        age = datetime.now(timezone.utc) - event.opened
        common["age"] = cli.strfdelta(age, "{days:2d}d {hours:02}:{minutes:02}")

        if event.type == Event.Type.PORTSTATE:
            common["downtime"] = cli.downtimeShortner(event.get_downtime())
        else:
            common["downtime"] = ""
    except Exception:
        raise

    common.update(vars(event))

    return common


def get_event_attributes(id, res_format=dict):
    attr_list = event_adapter.get_attrlist(session, int(id))

    # fixme is there a better way to do switch statements in Python?
    return {
        list: attr_list,
        dict: event_adapter.attrlist_to_attrdict(attr_list),
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
def events_table():
    return render_template('events-table.html')


@app.route('/get_events')
def events_list():
    table_events = get_current_events()
    return render_template('event-list.html', event_list=table_events)


@app.route('/show_details/<i>', methods=["GET"])
def read_details(i):
    event_attr, event_logs, event_history, event_msgs = get_event_details(i)

    return render_template('event-details.html', id=i, event_attr=event_attr, event_logs=event_logs,
                           event_history=event_history, event_msgs=event_msgs)


@app.route('/hide_details/<i>', methods=["GET"])
def hide_details(i):
    return render_template('hide-event-details.html', id=i)


@app.route('/event/<i>/update_status', methods=['GET', 'POST'])
def update_event_status(i):
    event_id = int(i)
    event_attr_current = get_event_details(i)[0]
    event_current_state = event_attr_current['adm_state']
    print('STATE ENUM', event_current_state)

    if request.method == 'POST':

        event_state_val = request.form['event-state']
        event_history_val = request.form['event-history']
        print('EVENT_STATE', event_state_val)
        print('EVENT_HISTORY', event_history_val)

        # config = Engine.get_config()
        # engine = Engine(config)
        # engine.connect()

        if not event_current_state == event_state_val:
            set_state_res = event_adapter.set_admin_state(session, event_engine.events.get(event_id),
                                                          AdmState(event_state_val))
            print("SET_STATE RES", set_state_res)

        if event_history_val:
            add_history_res = history_adapter.add(session, event_history_val, event_engine.events.get(event_id))
            print("ADD_HISTORY RES", add_history_res)

        event_attr, event_logs, event_history, event_msgs = get_event_details(i)

        return render_template('event-details.html', id=i, event_attr=event_attr, event_logs=event_logs,
                               event_history=event_history, event_msgs=event_msgs)

    elif request.method == 'GET':
        print("CURRENT STATE", event_current_state)
        return render_template('ui-update-event-status-form.html', id=i, current_state=event_current_state)

    # # res = make_response(render_template('ui-update-event-status-form.html', id=i))
    # # res.headers['HX-Reswap'] = f'none show:#ol-event-{i}:bottom'
    # #
    # # return res
    #
    # return render_template('ui-update-event-status-form.html', id=i)


@app.route('/event/<i>/update_status/cancel', methods=["GET"])
def cancel_update_event_status(i):
    return render_template('ui-hidden-li.html', id=i)


# TODO: replace this with some other HTMX pattern
@app.route('/get_none', methods=["GET"])
def get_none():
    return render_template('ui-generic-hidden.html')
