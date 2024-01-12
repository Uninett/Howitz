from howitz.config import flask, howitz, log, zino1
from zinolib.config.toml import parse_toml_config


def make_flask_config_dict(raw_config_dict):
    config_dict = {}
    flask_dict = flask.get_config_dict(raw_config_dict)
    config_dict.update(**flask_dict)

    howitz_config = howitz.Config.from_dict(raw_config_dict)
    howitz_dict = flask.convert_to_flask_config_dict(vars(howitz_config), "HOWITZ")
    config_dict.update(**howitz_dict)

    log_dict = log.get_config_dict(raw_config_dict)
    config_dict['LOGGING'] = log_dict

    zino_dict = zino1.get_config_dict(raw_config_dict)
    zino_dict.pop("username", None)
    zino_dict.pop("password", None)
    zino_dict = flask.convert_to_flask_config_dict(zino_dict, "ZINO1")
    config_dict.update(**zino_dict)

    return config_dict


def set_config(app, config_filename, config=None):
    if config is None:
        try:
            config = parse_toml_config(config_filename)
        except FileNotFoundError:
            app.config.from_prefixed_env(prefix="HOWITZ")
            return app
    config_dict = make_flask_config_dict(config)
    app.config.from_mapping(**config_dict)
    app.config.from_prefixed_env(prefix="HOWITZ")
    return app


def validate_config(config_dict):
    needed_keys = ('ZINO1_SERVER', 'HOWITZ_STORAGE', 'SECRET_KEY')
    found_keys = set(config_dict.keys())
    missing_keys = set(needed_keys) - found_keys
    if not missing_keys:
        return True
    return False


def load_config(app, config=None):
    config_filename = "howitz.toml"
    app = set_config(app, config_filename, config)
    validate_config(app.config)
    return app
