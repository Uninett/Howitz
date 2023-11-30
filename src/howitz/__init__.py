__version__ = '0.1'


from logging.config import dictConfig

from flask import Flask, g, redirect, url_for, current_app
from flask.logging import default_handler
from flask_assets import Bundle, Environment
from flask_login import LoginManager, logout_user

from howitz.config.utils import set_config, validate_config
from howitz.config.zino1 import make_zino1_config
from howitz.config.howitz import make_howitz_config
from howitz.users.db import UserDB
from zinolib.controllers.zino1 import Zino1EventManager


__all__ = ["create_app"]


def create_app(test_config=None):
    app = Flask(__name__)

    config_filename = "howitz.toml"
    app = set_config(app, config_filename)
    validate_config(app.config)
    zino_config = make_zino1_config(app.config)
    app.zino_config = zino_config
    howitz_config = make_howitz_config(app.config)
    app.howitz_config = howitz_config

    app.logger.removeHandler(default_handler)
    logging_dict = app.config.get("LOGGING", {})
    if logging_dict:
        dictConfig(logging_dict)
        app.logger.debug('Logging config -> %s', logging_dict)
    else:
        app.logger.addHandler(default_handler)
        app.logger.warn('Logging not set up, config not found')

    app.logger.debug('ZinoV1Config %s', zino_config)
    event_manager = Zino1EventManager.configure(zino_config)
    app.event_manager = event_manager
    app.logger.debug('Zino1EventManager %s', event_manager)

    database = UserDB(app.config["HOWITZ_STORAGE"])
    database.initdb()
    app.database = database
    app.logger.info('Connected to database %s', database)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"

    @login_manager.user_loader
    def load_user(user_id):
        with current_app.app_context():
            user = current_app.database.get(user_id)
            current_app.logger.info('User "%s" logged in', user.username)
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

    from . import endpoints
    app.register_blueprint(endpoints.main)

    return app
