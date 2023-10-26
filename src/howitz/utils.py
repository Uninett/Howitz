import functools

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
