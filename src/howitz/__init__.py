__version__ = '0.1'

import os

from flask_login import LoginManager
from flask import Flask
from flask_assets import Bundle, Environment

from zinolib.zino1 import Zino1EventEngine
from zinolib.ritz import ritz, parse_tcl_config

from pathlib import Path
from howitz.users.db import UserDB
from howitz.users.model import User

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
    u = database.get(user_id)
    print("USER loaded", u)
    return u
