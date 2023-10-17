import functools


def login_check(current_user, zino_session, fallback_func):
    """Check authentication status in both zino and flask session.
    """

    def _login_check(func):

        @functools.wraps(func)
        def __login_check(*args):
            if current_user.is_authenticated and zino_session.authenticated:
                return func(*args)

            return fallback_func(*args)
        
        return __login_check

    return _login_check
