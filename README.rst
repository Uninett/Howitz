============================================
Howitz - Zino web client with HTMx and Flask
============================================

Play around
===========

Install safely
--------------

Make and activate a virtualenv, install dependencies in that virtualenv::

    $ python3 -m venv howitz
    $ source howitz/bin/activate
    $ pip install -e .

On this branch you need a version of zinolib that is still a work-in-progress (hmpf's decoupling branch).
Build it with f.e. `pyproject-build`. Make sure that zinolib dependency is reinstalled as the newly built wheel file.

::

    pip install --force-reinstall zinolib-example.whl

Run in development-mode
-----------------------

You need to have either a minimal configuration file or set two environment varibles, see `Configuration`_.

Either of::

    $ python3 -m howitz

or::

    $ flask --app howitz run

should get you a server running on http://127.0.0.1:5000/ The database is by
default put in the current directory.

Run in production
-----------------

Always use an installed howitz.

* gunicorn: ``gunicorn 'howitz:create_app()'``
* waitress: ``waitress-serve --call howitz:create_app``

See https://flask.palletsprojects.com/en/3.0.x/deploying/ for more options and
additional details, and the respective server's docs for server-specific
details.

Configuration
=============

Howitz *can* run without a configuration file. Default values will be used for
listen-address (127.0.0.1), port (9000) and storage location
(./howitz.sqlite3). However, at minimum you also need to pass in a SECRET_KEY
for Flask and a zino server to fetch events from.

These can be passed via a configuration file, ".howitz.toml" (in the current directory or user home directory) or via environment variables.

Via configuration file::

    [flask]
    SECRET_KEY = "long string!"

    [zino.connections.default]
    server = "some.server.tld"

Directly via environment variables::

    HOWITZ_SECRET_KEY="long string!" HOWITZ_ZINO1_SERVER="some.server.tld"

All config options can be overruled by environment variables. Prefix with
"HOWITZ_" for Flask-specific options and "HOWITZ_ZINO1_" for Zino-specific
options. It is also possible to override logging by setting "HOWITZ_LOGGING" to
a string of a python dict but we do not recommend it, use a config file instead.

Debugging can be turned on either by adding ``DEBUG = true`` to the
``[flask]``-section or setting the environment variable ``HOWITZ_DEBUG`` to ``1``.


Run tests
=========

Linting: ``tox -e lint``

Tests: currently, just run ``pytest``
