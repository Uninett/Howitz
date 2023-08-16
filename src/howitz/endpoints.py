from flask import Flask, render_template, make_response, request
from flask_assets import Bundle, Environment

from itertools import product
import logging
from pathlib import Path
from datetime import datetime, timezone
import curitz

from zinolib.ritz import ritz, notifier, parse_tcl_config, caseState
from curitz import cli
from zinolib.zino1 import Zino1EventEngine, EventAdapter, HistoryAdapter

app = Flask(__name__)
LOG = logging.getLogger(__name__)

assets = Environment(app)
css = Bundle("main.css", output="dist/main.css")

assets.register("css", css)
css.build()

#
# class Obj:
#     pass

#
# class Engine:
#
#     @classmethod
#     def _get_filename(cls):
#         locations = ['.', '~/.local', '~']
#         filenames = ['.ritz.tcl', 'ritz.tcl']
#         filename = None
#         paths = [Path(f'{p}/{f}') for f, p in product(locations, filenames)]
#         for filename in paths:
#             if filename.exists():
#                 break
#         if filename is None:
#             error = 'Config file not found, looked for {}'.format(', '.join(paths))
#             raise ValueError(error)
#         return filename
#
#     @classmethod
#     def get_config(cls):
#         filename = cls._get_filename()
#         conf = parse_tcl_config(filename)
#         obj = Obj()
#         for key, value in conf['default'].items():
#             setattr(obj, key, value)
#         obj.autoremove = True
#         return obj
#
#     def __init__(self, config, server=None, username=None, password=None, timeout=30):
#         self.config = config
#         self.timeout = timeout
#         self.server = server or config.Server
#         self.username = username or config.User
#         self.password = password or config.Secret
#         self.cases = {}
#         self.cases_selected = {}
#
#     def connect(self):
#         self.session = ritz(
#             self.server, username=self.username, password=self.password, timeout=30
#         )
#         self.session.connect()
#         self.notifier = notifier(self.session)
#         self.notifier.connect()
#
#     def close(self):
#         self.session.close()
#         self.notifier = None
#         del self.notifier
#         del self.session
#
#     def load_current_cases(self):
#         if not self.session:
#             raise ValueError('Not connected')
#         caselist = self.session.get_caseids()
#         for c in caselist:
#             try:
#                 case = self.session.case(c)
#             except Exception as e:
#                 continue
#             self.cases[case.id] = case
#
#     def get_event_attributes(self, id):
#         pass


# config = Engine.get_config()
# engine = Engine(config)
# print('Connecting..', engine)
# engine.connect()
# print('Connected')


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


# print("EVENTS FROM EVENTENGINE", event_engine.events.get(77049))


def get_current_cases():
    event_engine.get_events()
    # engine.load_current_cases()
    cases = event_engine.events
    # print("CASES ITEMS", cases)

    cases_sorted = cases

    # cases_sorted = {k: cases[k] for k in sorted(cases,
    #                                             key=lambda k: (
    #                                                 0 if cases[k]._attrs("state") == caseState.IGNORED else 1,
    #                                                 # cases[k].history[-1]['date'],
    #                                                 cases[k]._attrs["updated"],
    #                                             ), reverse=True)}

    # print("CASES SORTED", cases_sorted)

    # for key, value in cases.items():
    #     print(f'Event {key}: {value.keys()}')

    # print('EVENTS ', len(cases))

    table_cases = []
    for c in cases_sorted.values():
        # print('CASE RAW', c.history[-1])
        table_cases.append(create_case(c))

    # print('Table cases', table_cases)

    return table_cases, cases_sorted


def create_case(case):
    common = {}

    print("CASE", case.type)

    try:
        age = datetime.now(timezone.utc) - case.opened
        common["id"] = case.id
        common["router"] = case.router
        common["admstate"] = case.adm_state.value[:7]
        common["age"] = cli.strfdelta(age, "{days:2d}d {hours:02}:{minutes:02}")
        common["priority"] = case.priority
        if "downtime" in vars(case):
            common["downtime"] = cli.downtimeShortner(case.downtime)
        else:
            common["downtime"] = ""

        if case.type == cli.caseType.PORTSTATE:
            print("IS PORTSTATE")
            common["opstate"] = "PORT %s" % case.port_state[0:5]
            common["port"] = cli.interfaceRenamer(case.port)
            common["description"] = case.get("descr", "")
        elif case.type == cli.caseType.BGP:
            common["opstate"] = "BGP  %s" % case.bgpos[0:5]
            common["port"] = "AS{}".format(case.remote_as)
            common["description"] = "%s %s" % (
                cli.dns_reverse_resolver(str(case.remote_addr)),
                case.get("lastevent", ""),
            )
        elif case.type == cli.caseType.BFD:
            try:
                port = case.bfdaddr
            except Exception:
                port = "ix {}".format(case.bfdix)

            common["opstate"] = "BFD  %s" % case.bfd_state[0:5]
            common["port"] = str(port)
            common["description"] = "{}, {}".format(
                case.get("neigh_rdns"), case.get("lastevent")
            )
        elif case.type == cli.caseType.REACHABILITY:
            common["opstate"] = case.reachability
            common["port"] = ""
            common["description"] = ""
        elif case.type == cli.caseType.ALARM:
            common["opstate"] = "ALRM {}".format(case.alarm_type)
            common["port"] = ""
            common["description"] = case.lastevent
    except Exception:
        raise

    return common


# def get_event_attributes(id):
#     # config = Engine.get_config()
#     # engine = Engine(config)
#     # engine.connect()
#
#     case_attr = engine.session.get_attributes(int(id))
#     print('CASE ATTR', case_attr)
#
#     return case_attr


def get_event_details(id):
    # config = Engine.get_config()
    # engine = Engine(config)
    # engine.connect()

    case_attr = event_adapter.get_attrlist(session, int(id))
    event_logs = event_engine.get_log_for_id(int(id))
    event_history = event_engine.get_history_for_id(int(id))
    # print('CASE ATTR', case_attr)
    # print('EVENT LOGS', event_logs)
    # print('EVENT HISTORY', event_history)

    event_msgs = []
    for log in event_logs:
        msg = {'date': log['date'], 'msg': log['header'], 'user': ''}
        event_msgs.append(msg)

    for history in event_history:
        msg = {'date': history['date'], 'user': history['user']}
        if history['log']:
            msg['msg'] = ' '.join(history['log'])
        else:
            msg['msg'] = history['header']

        event_msgs.append(msg)

    # print('EVENT MSGS', event_msgs)

    return case_attr, event_logs, event_history, event_msgs


@app.route('/')
@app.route('/hello-world')
def index():
    exemplify_loop = list('abracadabra')
    return render_template('index.html', example_list=exemplify_loop)


@app.route('/events')
def events_table():
    case_list = []
    table_cases, cases = get_current_cases()
    for case in cases.values():
        if hasattr(case, 'descr'):
            case_list.append(case)

    return render_template('events-table.html', case_list=table_cases, datetime=datetime, curitz=curitz, cli=cli)


@app.route('/get_events')
def events_list():
    case_list = []
    table_cases, cases = get_current_cases()
    for case in cases.values():
        if hasattr(case, 'descr'):
            case_list.append(case)

    return render_template('event-list.html', case_list=table_cases, datetime=datetime, curitz=curitz, cli=cli)


@app.route('/show_details/<i>', methods=["GET"])
def read_details(i):
    case_attr, event_logs, event_history, event_msgs = get_event_details(i)

    return render_template('event-details.html', id=i, case_attr=case_attr, event_logs=event_logs,
                           event_history=event_history, event_msgs=event_msgs)


@app.route('/hide_details/<i>', methods=["GET"])
def hide_details(i):
    return render_template('hide-event-details.html', id=i)


@app.route('/event/<i>/update_status', methods=['GET', 'POST'])
def update_event_status(i):
    case_id = int(i)
    case_attr_current = get_event_details(i)[0]
    event_current_state = case_attr_current['adm_state'].value
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
            set_state_res = event_adapter.set_admin_state(session, event_engine.events.get(case_id), event_state_val)
            print("SET_STATE RES", set_state_res)

        if event_history_val:
            add_history_res = history_adapter.add(session, event_history_val, event_engine.events.get(case_id))
            print("ADD_HISTORY RES", add_history_res)

        case_attr, event_logs, event_history, event_msgs = get_event_details(i)

        return render_template('event-details.html', id=i, case_attr=case_attr, event_logs=event_logs,
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
