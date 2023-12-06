import uuid

from flask import json, render_template, session, current_app
from werkzeug.exceptions import HTTPException


# Fixme add non-generic error handling as well
def handle_generic_http_exception(e):
    """Return JSON instead of HTML for HTTP errors."""
    # start with the correct headers and status code from the error
    response = e.get_response()
    # replace the body with JSON
    response.data = json.dumps({
        "code": e.code,
        "name": e.name,
        "description": e.description,
    })
    response.content_type = "application/json"
    return response


def handle_generic_exception(e):
    # pass through HTTP errors
    if isinstance(e, HTTPException):
        return e

    # now you're handling non-HTTP exceptions only
    alert_random_id = str(uuid.uuid4())
    short_err_msg = 'An error has occurred'

    session["errors"][str(alert_random_id)] = e.__repr__()
    session.modified = True
    current_app.logger.debug('ERRORS %s', session["errors"])

    return render_template('/components/popups/alerts/error/error-alert.html',
                           alert_id=alert_random_id, short_err_msg=short_err_msg)
