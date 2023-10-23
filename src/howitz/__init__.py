__version__ = '0.1'


import os
from logging.config import dictConfig
from pathlib import Path

from flask import Flask, g, redirect, url_for, current_app
from flask_assets import Bundle, Environment
from flask_login import LoginManager, logout_user

from howitz.users.db import UserDB
from zinolib.controllers.zino1 import Zino1EventManager
from zinolib.config.zino1 import ZinoV1Config


__all__ = ["create_app"]


def create_app(test_config=None):
    app = Flask(__name__)

    # TODO: Read from config-file and translate to FLASK-style via dict
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'howitz.sqlite3'),
    )

    # TODO: Move actual dict to config file
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

    # TODO: Get from howitz config file, sans user
    config = ZinoV1Config.from_tcl('ritz.tcl')
    config.password = None
    config.username = None
    app.logger.debug('ZinoV1Config %s', config)
    event_manager = Zino1EventManager.configure(config)
    app.event_manager = event_manager
    app.logger.debug('Zino1EventManager %s', event_manager)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        with current_app.app_context():
            user = current_app.database.get(user_id)
            current_app.logger.info('User "%s" logged in', user.username)
            current_app.logger.debug('User "%s"', user)
            return user

    @login_manager.unauthorized_handler
    def unauthorized():
        logout_user()
        with current_app.app_context():
            try:
                if current_app.event_manager.is_connected and not current_app.event_manager.is_authenticated:
                    current_app.event_manager.disconnect()
                    current_app.logger.debug("Zino session was disconnected")
            except ValueError:
                current_app.logger.debug("Zino session was not established")

        return redirect(url_for('main.login'))

    assets = Environment(app)
    css = Bundle("main.css", output="dist/main.css")

    assets.register("css", css)
    css.build()

    DB_URL = Path('howitz.sqlite3')
    database = UserDB(DB_URL)
    database.initdb()
    app.database = database
    app.logger.info('Connected to database %s', database)

    from . import endpoints
    app.register_blueprint(endpoints.main)

    return app
