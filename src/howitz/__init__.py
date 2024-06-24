__version__ = '0.1-a3'


from logging.config import dictConfig
from flask_caching import Cache

from flask import Flask, g, redirect, url_for, current_app
from flask.logging import default_handler
from flask_assets import Bundle, Environment
from flask_login import LoginManager, logout_user
from werkzeug.exceptions import HTTPException, BadRequest, NotFound, Forbidden

from howitz.config.utils import load_config
from howitz.config.zino1 import make_zino1_config
from howitz.config.howitz import make_howitz_config
from howitz.error_handlers import handle_generic_exception, handle_generic_http_exception, handle_400, handle_404, handle_403, handle_lost_connection
from howitz.users.db import UserDB
from howitz.users.commands import user_cli
from zinolib.controllers.zino1 import Zino1EventManager, LostConnectionError, NotConnectedError

__all__ = ["create_app"]


def create_app(test_config=None):
    app = Flask(__name__)

    # register error handlers
    app.register_error_handler(Exception, handle_generic_exception)
    app.register_error_handler(HTTPException, handle_generic_http_exception)
    app.register_error_handler(BadRequest, handle_400)
    app.register_error_handler(NotFound, handle_404)
    app.register_error_handler(Forbidden, handle_403)
    app.register_error_handler(LostConnectionError, handle_lost_connection)
    app.register_error_handler(BrokenPipeError, handle_lost_connection)
    app.register_error_handler(NotConnectedError, handle_lost_connection)

    # load config
    app = load_config(app, test_config)
    zino_config = make_zino1_config(app.config)
    app.zino_config = zino_config
    howitz_config = make_howitz_config(app.config)
    app.howitz_config = howitz_config

    # set up logging
    app.logger.removeHandler(default_handler)
    logging_dict = app.config.get("LOGGING", {})
    if logging_dict:
        dictConfig(logging_dict)
        app.logger.debug('Logging config -> %s', logging_dict)
    else:
        app.logger.addHandler(default_handler)
        app.logger.warn('Logging not set up, config not found')

    # set up zino controller
    app.logger.debug('ZinoV1Config %s', zino_config)
    event_manager = Zino1EventManager.configure(zino_config)
    app.event_manager = event_manager
    app.logger.debug('Zino1EventManager %s', event_manager)

    # set up placeholder for UpdateHandler
    app.updater = None
    app.logger.debug('UpdateHandler is None')

    # set up user database
    database = UserDB(app.config["HOWITZ_STORAGE"])
    database.initdb()
    app.database = database
    app.logger.info('Connected to database %s', database)

    # load extra commands
    app.cli.add_command(user_cli)

    # set up web auth
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

    # load css
    assets = Environment(app)
    css = Bundle("main.css", output="dist/main.css")

    assets.register("css", css)
    css.build()

    cache_type = app.config.get("CACHE_TYPE")
    if not cache_type:
        cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
        cache.init_app(app)
        app.logger.warn('Caching config not found, setting up simple caching')
    else:
        cache = Cache(app)
        app.logger.debug('Cache type -> %s', cache_type)
    app.cache = cache


    # import endpoints/urls
    from . import endpoints
    app.register_blueprint(endpoints.main)

    return app
