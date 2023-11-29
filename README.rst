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

Howitz is deeply dependent on the library ``zinolib``. When developing Howitz,
it might be prudent to add zinolib manually to the virtualenv by downloading
the source, entering the directory and running ``pip install -e .``. This will
make it very easy to switch between versions and branches of zinolib.

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
listen-address (127.0.0.1), port (5000) and storage location
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

Example config-file for development
-----------------------------------

For development, copy the included file ``dev-howitz.toml`` to ``.howitz.toml`` in the same directory.

1. Set ``[flask] -> SECRET_KEY`` to some long string.
2. Set ``[zino.connections.default] -> server`` to a Zino 1 server.
3. Optionally set ``[zino.connections.other] -> server`` to a fallback Zino
   1 server. If the server in 2 stops working ypu can swap "other" with
   "deafult" in the config-file and keep on working.

There's a handler "debug" that will copy everything DEBUG or higher to a file
``debug.log``, you might want to use this handler for your code.

The handler ``error`` will likewisse put everything WARNING or higher in the
``error.log`` file.

Config file for production
--------------------------

It is better to control ``[flask] -> SECRET_KEY`` and
``[zino.connections.default] -> server`` via environment variables than
hardcoding them in the config file. It's best to delete them from the config
file.

``[flask] -> DEBUG`` should be ``false``. You can stil override it via an
environment variable.

``[logging]`` will need adjustments. Increase the level of the ``wsgi``-handler
or only use the ``error`` handler. Change the error-handler to ship its log
somewhere else, via syslog or Sentry or similar.


Run tests
=========

Linting: ``tox -e lint``

Tests: ``tox``
