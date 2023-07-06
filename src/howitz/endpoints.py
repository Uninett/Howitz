from flask import Flask, render_template
from flask_assets import Bundle, Environment

from itertools import product
import logging
from pathlib import Path
import time
import datetime
import curitz

from zinolib.ritz import ritz, notifier, parse_tcl_config
from curitz import cli

app = Flask(__name__)
LOG = logging.getLogger(__name__)

assets = Environment(app)
css = Bundle("main.css", output="dist/main.css")

assets.register("css", css)
css.build()

class Obj:
    pass


class Engine:

    @classmethod
    def _get_filename(cls):
        locations = ['.', '~/.local', '~']
        filenames = ['.ritz.tcl', 'ritz.tcl']
        filename = None
        paths = [Path(f'{p}/{f}') for f, p in product(locations, filenames)]
        for filename in paths:
            if filename.exists():
                break
        if filename is None:
            error = 'Config file not found, looked for {}'.format(', '.join(paths))
            raise ValueError(error)
        return filename

    @classmethod
    def get_config(cls):
        filename = cls._get_filename()
        conf = parse_tcl_config(filename)
        obj = Obj()
        for key, value in conf['default'].items():
            setattr(obj, key, value)
        obj.autoremove = True
        return obj

    def __init__(self, config, server=None, username=None, password=None, timeout=30):
        self.config = config
        self.timeout = timeout
        self.server = server or config.Server
        self.username = username or config.User
        self.password = password or config.Secret
        self.cases = {}
        self.cases_selected = {}

    def connect(self):
        self.session = ritz(
            self.server, username=self.username, password=self.password, timeout=30
        )
        self.session.connect()
        self.notifier = notifier(self.session)
        self.notifier.connect()

    def close(self):
        self.session.close()
        self.notifier = None
        del self.notifier
        del self.session

    def load_current_cases(self):
        if not self.session:
            raise ValueError('Not connected')
        caselist = self.session.get_caseids()
        for c in caselist:
            try:
                case = self.session.case(c)
            except Exception as e:
                continue
            self.cases[case.id] = case



def get_current_cases():
    config = Engine.get_config()
    engine = Engine(config)
    print('Connecting..', engine)
    engine.connect()
    print('Connected')
    engine.load_current_cases()
    cases = engine.cases

    # for key, value in cases.items():
    #     print(f'Event {key}: {value.keys()}')

    # print('EVENTS ', len(cases))

    table_cases = []
    for c in cases.values():
        table_cases.append(create_case(c))

    # print('Table cases', table_cases)

    return table_cases, cases, engine


def create_case(case):
    common = {}

    try:
        age = datetime.datetime.now() - case.opened
        common["id"] = case.id
        common["router"] = case.router
        common["admstate"] = case.state.value[:7]
        common["age"] = cli.strfdelta(age, "{days:2d}d {hours:02}:{minutes:02}")
        common["priority"] = case.priority
        if "downtime" in case.keys():
            common["downtime"] = cli.downtimeShortner(case.downtime)
        else:
            common["downtime"] = ""

        if case.type == cli.caseType.PORTSTATE:
            common["opstate"] = "PORT %s" % case.portstate[0:5]
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

            common["opstate"] = "BFD  %s" % case.bfdstate[0:5]
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

def get_event_attributes(id):
    config = Engine.get_config()
    engine = Engine(config)
    engine.connect()

    case_attr = engine.session.get_attributes(int(id))
    print('CASE ATTR', case_attr)

    return case_attr

@app.route('/')
@app.route('/hello-world')
def index():
    exemplify_loop = list('abracadabra')
    return render_template('index.html', example_list=exemplify_loop)



@app.route('/events')
def events_table():
    case_list = []
    table_cases, cases, engine = get_current_cases()
    for case in cases.values():
        if hasattr(case, 'descr'):
            case_list.append(case)

    return render_template('events-table.html', case_list=table_cases, datetime=datetime, curitz=curitz, cli=cli)


@app.route('/get_events')
def events_list():
    case_list = []
    table_cases, cases, engine = get_current_cases()
    for case in cases.values():
        if hasattr(case, 'descr'):
            case_list.append(case)

    return render_template('event-list.html', case_list=table_cases, datetime=datetime, curitz=curitz, cli=cli)


@app.route('/show_details/<i>', methods=["GET"])
def read_details(i):

    case_attr = get_event_attributes(i)

    return render_template('event-details.html', id=i, case_attr=case_attr)

@app.route('/hide_details/<i>', methods=["GET"])
def hide_details(i):

    return render_template('hide-event-details.html', id=i)
