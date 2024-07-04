import uuid

from flask import render_template, session, current_app, make_response, request
from flask_login import current_user
from werkzeug.exceptions import HTTPException, BadGateway

from howitz.endpoints import reconnect_to_zino, test_zino_connection
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


def handle_403(e):
    current_app.logger.exception("403 Forbidden has occurred %s", e)

    response = make_response(render_template('/responses/403.html',
                                             err_msg=e.description))

    response.headers['HX-Trigger'] = 'htmx:responseError'

    return response, 403


def handle_bad_gateway(e):
    current_app.logger.exception("502 Bad Gateway has occurred %s", e)
    description = BadGateway.description
    try:
        description = e.description
    except AttributeError:
        pass

    response = make_response(render_template('responses/502.html', err_msg=description))
    response.headers['HX-Retarget'] = 'body'
    response.headers['HX-Reswap'] = 'innerHTML'
    return response, 502


def handle_lost_connection(e):
    if isinstance(e, BrokenPipeError):
        current_app.logger.exception("Lost connection to Zino server: %s", e)
    else:
        current_app.logger.error("Lost connection to Zino server: %s", e.args[0])

    if current_user.is_authenticated:  # Re-connect to Zino with existing credentials and inform user that there was an error via alert pop-up
        alert_random_id = str(uuid.uuid4())
        try:
            short_err_msg = e.args[0]
        except IndexError:
            short_err_msg = 'Lost connection to Zino server'

        if not "errors" in session:
            session["errors"] = dict()
        session["errors"][str(alert_random_id)] = serialize_exception(e)
        session.modified = True

        # Check if connection is still down
        should_attempt_reconnect = test_zino_connection()
        if should_attempt_reconnect is not False:  # Both True or None options are acceptable
            reconnect_to_zino()  # Ensure a clean reconnect to Zino server and re-populate the events data
            short_err_msg = 'Temporarily lost connection to Zino server, please retry your action'

        response = make_response(render_template('/components/popups/alerts/error/error-alert.html',
                                                 alert_id=alert_random_id, short_err_msg=short_err_msg))
        response.headers['HX-Reswap'] = 'beforeend'
        return response, 503
    else:  # Redirect to /login for complete re-authentication
        current_app.event_manager.disconnect()
        res = make_response()
        res.headers['HX-Redirect'] = '/login'
        return res, 401
