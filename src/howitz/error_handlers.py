import uuid

from flask import json, render_template, session, current_app
from werkzeug.exceptions import HTTPException

from howitz.utils import serialize_exception


# Fixme add non-generic error handling as well
def handle_generic_http_exception(e):
    current_app.logger.exception("An unexpected HTTP exception has occurred %s", e)

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
    short_err_msg = 'An unexpected error has occurred'

    if not "errors" in session:
        session["errors"] = dict()
    session["errors"][str(alert_random_id)] = serialize_exception(e)
    session.modified = True
    current_app.logger.debug('ERRORS %s', session["errors"])
    current_app.logger.exception("An unexpected exception has occurred %s", e)

    return render_template('/components/popups/alerts/error/error-alert.html',
                           alert_id=alert_random_id, short_err_msg=short_err_msg)


def handle_400(e):
    current_app.logger.exception("400 Bad Request has occurred %s", e)

    return render_template('/responses/400-generic.html',
                           err_msg=e.description), 400
