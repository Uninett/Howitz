import uuid

from flask import render_template, session, current_app, make_response, request
from flask_login import current_user
from werkzeug.exceptions import HTTPException

from howitz.endpoints import connect_to_zino
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


def handle_lost_connection(e):
    if isinstance(e, BrokenPipeError):
        current_app.logger.exception("Lost connection to Zino server: %s", e)
    else:
        current_app.logger.error("Lost connection to Zino server: %s", e.args[0])

    if current_user.is_authenticated:  # Re-connect to Zino with existing credentials and inform user that there was an error via alert pop-up
        if current_app.event_manager.is_connected:
            current_app.event_manager.disconnect()

        connect_to_zino(current_user.username, current_user.token)

        # Make sure that EventManager is populated with data after re-connect
        current_app.event_manager.get_events()

        # Re-fetch the event list and update event data in cache and session
        # This is needed in case there were NTIE updates that occurred while connection was down, so that they are not lost until manual page refresh
        events = current_app.event_manager.events
        current_app.cache.set("events", events)  # Update cache
        session["event_ids"] = list(events.keys())  # Update session
        session["events_last_refreshed"] = None  # Mark current event table in UI as outdated
        session.modified = True

        alert_random_id = str(uuid.uuid4())
        try:
            short_err_msg = e.args[0]
        except IndexError:
            short_err_msg = 'Temporarily lost connection to Zino server'

        if not "errors" in session:
            session["errors"] = dict()
        session["errors"][str(alert_random_id)] = serialize_exception(e)
        session.modified = True

        response = make_response(render_template('/components/popups/alerts/error/error-alert.html',
                                                 alert_id=alert_random_id, short_err_msg=short_err_msg))
        response.headers['HX-Reswap'] = 'beforeend'
        return response, 503
    else:  # Redirect to /login for complete re-authentication
        res = make_response()
        res.headers['HX-Redirect'] = '/login'
        return res
