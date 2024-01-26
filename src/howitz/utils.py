import functools
import traceback
from datetime import datetime, timezone

from flask import current_app
from flask_login import current_user


def login_check():
    """Check authentication status in both zino and flask session.
    """

    def _login_check(func):
        @functools.wraps(func)
        def __login_check(*args):
            with current_app.app_context():
                if current_user.is_authenticated and current_app.event_manager.is_authenticated:
                    current_app.logger.info("User authorized")
                    return func(*args)

            return current_app.login_manager.unauthorized(*args)

        return __login_check

    return _login_check


def serialize_exception(exc):
    return ''.join(traceback.format_exception(exc))


def utc_to_local(dt: datetime):
    """
    Find out local timezone.
    Copied from: https://stackoverflow.com/a/13287083
    """
    return dt.replace(tzinfo=timezone.utc).astimezone(tz=None)


def set_correct_timezone(dt: datetime):
    if current_app.howitz_config["timezone"] == 'LOCAL':
        res = utc_to_local(dt)
        current_app.logger.debug('UTC_TO_LOCAL %s', res)
    # fixme is this else statement even needed? this makes sure that datetime is aware in Howitz
    else:
        res = dt.replace(
            tzinfo=timezone.utc)  # Set UTC as timezone in case none or invalid timezone is provided in config
        current_app.logger.debug('UTC %s', res)

    return res


def date_str_without_timezone(dt: datetime):
    dt_aware = set_correct_timezone(dt)
    current_app.logger.debug('AWARE DATETIME %s', dt_aware)
    return dt_aware.strftime("%Y-%m-%d %H:%M:%S")
