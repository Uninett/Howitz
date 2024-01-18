import uuid

from flask import render_template, session, current_app
from werkzeug.exceptions import HTTPException

from howitz.utils import serialize_exception


def handle_generic_http_exception(e):
    current_app.logger.exception("An unexpected HTTP exception has occurred %s", e)

    alert_random_id = str(uuid.uuid4())
    short_err_msg = f"{e.code} {e.name}: {e.description}"

    session["errors"][str(alert_random_id)] = serialize_exception(e)
    session.modified = True
    current_app.logger.debug('ERRORS %s', session["errors"])

    return render_template('/components/popups/alerts/error/error-alert.html',
                           alert_id=alert_random_id, short_err_msg=short_err_msg), e.code


def handle_generic_exception(e):
    # pass through HTTP errors
    if isinstance(e, HTTPException):
        return e

    # now you're handling non-HTTP exceptions only
    alert_random_id = str(uuid.uuid4())
    try:
        short_err_msg = e.args[0]
    except IndexError:
        short_err_msg = 'An unexpected error has occurred'

    if not "errors" in session:
        session["errors"] = dict()
    session["errors"][str(alert_random_id)] = serialize_exception(e)
    session.modified = True
    current_app.logger.debug('ERRORS %s', session["errors"])
    current_app.logger.exception("An unexpected exception has occurred %s", e)

    return render_template('/components/popups/alerts/error/error-alert.html',
                           alert_id=alert_random_id, short_err_msg=short_err_msg), 500
