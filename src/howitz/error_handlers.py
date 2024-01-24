import uuid

from flask import render_template, session, current_app, make_response, request
from werkzeug.exceptions import HTTPException

from howitz.utils import serialize_exception


def handle_generic_http_exception(e):
    current_app.logger.exception('Exception in %s: %s:', request.path, e)

    alert_random_id = str(uuid.uuid4())
    short_err_msg = f"{e.code} {e.name}: {e.description}"

    if not "errors" in session:
        session["errors"] = dict()
    session["errors"][str(alert_random_id)] = serialize_exception(e)
    session.modified = True

    response = make_response(render_template('/components/popups/alerts/error/error-alert.html',
                           alert_id=alert_random_id, short_err_msg=short_err_msg))

    response.headers['HX-Reswap'] = 'beforeend'

    return response, e.code


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
    current_app.logger.exception('Exception in %s: %s:', request.path, e)

    response = make_response(render_template('/components/popups/alerts/error/error-alert.html',
                           alert_id=alert_random_id, short_err_msg=short_err_msg))

    response.headers['HX-Reswap'] = 'beforeend'

    return response, 500


def handle_400(e):
    current_app.logger.exception("400 Bad Request has occurred %s", e)

    return render_template('/responses/400-generic.html',
                           err_msg=e.description), 400


def handle_404(e):
    IGNORE = set(['favicon.ico'])
    if request.path not in IGNORE:
        current_app.logger.warn('Path not found: %s', request.path)
    return render_template('/responses/404-not-found.html',
                           err_msg=e.description), 404
