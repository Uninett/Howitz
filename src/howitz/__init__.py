__version__ = '0.1'

from flask import Flask
from flask_assets import Bundle, Environment

from zinolib.zino1 import Zino1EventEngine
from zinolib.ritz import ritz, parse_tcl_config

app = Flask(__name__)

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
