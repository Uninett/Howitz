============================================
Howitz - Zino web client with HTMx and Flask
============================================

Play around
===========

Install safely
--------------

Make and activate a virtualenv, install dependencies in that virtualenv::

    $ python3 -m venv howitzvenv
    $ source howitzvenv/bin/activate
    $ pip install -e .


Tip:

    Howitz is deeply dependent on the library ``zinolib``. When developing Howitz,
    it might be prudent to add zinolib manually to the virtualenv by downloading
    the source, entering the directory and running ``pip install -e .``. This will
    make it very easy to switch between versions and branches of zinolib.


Run in development-mode
-----------------------

You need to have either a minimal configuration file or set two environment variables, see `Configuration`_.
Tip for quickly setting up an extensive config file for dev:

    Check out the `Example config-file for development`_ section.


After both installation (see `Install safely`_) and `Configuration`_ are done, you can run Howitz by running
either::

    $ python3 -m howitz

or::

    $ flask --app howitz run

This will get you a web interface running on http://127.0.0.1:5000/.
The database (see `User management`_) is by default put in the current directory.

**NB!**:

    If you get an error when attempting to log in for the first time, make sure you have created a user in the Howitz
    database, see `Managing the Howitz user database`_.


Run in production
-----------------

You need to have either a minimal configuration file or set two environment variables, see `Configuration`_.

Tip for quickly setting up an extensive config file:

    Check out the `Example config-file for development`_ section. Make sure config file is appropriate for production,
    see `Config file for production`_.


Always use an installed howitz.

* gunicorn: ``gunicorn 'howitz:create_app()'``
* waitress: ``waitress-serve --call howitz:create_app``

See https://flask.palletsprojects.com/en/3.0.x/deploying/ for more options and
additional details, and the respective server's docs for server-specific
details.

User management
===============

Due to how Zino protocol 1 does logins, the password (here called token) needs
to be stored in plain text in every client. For security-reasons it is not
desirable to ever store this token in a cookie or otherwise in a browser, so
instead the token is stored where the browser cannot get to it, in a user
database local to the frontend server.

When logging in to Howitz a user uses a normal password (not the token) which
is used to safely fetch the token for connecting to the zino protocol 1 server.
This password can be treated like any other password and be put in a vault or
a password-manager.

The mapping from websafe password to legacy token is done via a user database.
The Zino backend server admin creates a token and username. The frontend server
admin creates a local user with the backend username and token, and a password
preferrably chosen by the users themselves.

We are planning to allow users to change the frontend password eventually but
we do not wish for the backend token to ever be seen by a browser in any
fashion.

Managing the Howitz user database
---------------------------------

Users are by default stored in the file "./howitz.sqlite3", this can be changed
in the configuration file.

While it is possible to use an sqlite3-client to alter the database, setting
the password should be done via the command line, to ensure that the password
is hashed correctly.

Get a list of the possible commands by running::

    $ flask --app howitz user
    Usage: flask user [OPTIONS] COMMAND [ARGS]...

    Options:
      --help  Show this message and exit.

    Commands:
      create
      delete
      list
      update

Get help for each sub-command with appending "--help", for instance::

    $ flask -A howitz user update --help
    Usage: flask user update [OPTIONS] USERNAME

    Options:
      -p, --password TEXT
      -t, --token TEXT
      --help               Show this message and exit.

All available commands
----------------------

``create``
    creates a user, the username needs to be unique

``delete``
    removes an existing user

``list``
    shows all known usernames

``update``
    is used to change the web password or zino token for an existing user


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
    server = "zino.server.domain"

Directly via environment variables::

    HOWITZ_SECRET_KEY="long string!" HOWITZ_ZINO1_SERVER="zino.server.domain"

All config options can be overruled by environment variables. Prefix with
"HOWITZ\_" for Flask-specific options and "HOWITZ_ZINO1\_" for Zino-specific
options. It is also possible to override logging by setting "HOWITZ_LOGGING" to
a string of a python dict but we do not recommend it, use a config file instead.

Poll interval for events table can be changed by adding for example ``poll_interval = 30`` to
the ``[howitz]``-section or setting the environment variable ``HOWITZ_POLL_INTERVAL`` to a new value.
Poll interval values represented seconds and must be integers. The default value is ``60`` seconds.

Debugging can be turned on either by adding ``DEBUG = true`` to the
``[flask]``-section or setting the environment variable ``HOWITZ_DEBUG`` to ``1``.

Default timezone for timestamps is ``UTC``. Timezone information can be changed by adding ``timezone = "LOCAL"`` to
the ``[howitz]``-section or setting the environment variable ``HOWITZ_TIMEZONE`` to ``LOCAL``. Timezone values other
than ``LOCAL`` and ``UTC`` provided in config will be ignored and fall back to ``UTC``.


Example config-file for development
-----------------------------------

For development, copy the contents of the included file ``dev-howitz.toml`` to ``.howitz.toml`` in the same directory.

1. Set ``[flask] -> SECRET_KEY`` to some long string.
2. Set ``[zino.connections.default] -> server`` to a Zino 1 server.
3. Optionally set ``[zino.connections.other] -> server`` to a fallback Zino
   1 server. If the default server stops working you can swap "other" with
   "default" in the config-file and keep on working. If you don't set it to
   anything, comment it out/remove it.

There's a handler "debug" that will copy everything DEBUG or higher to a file
``debug.log``, you might want to use this handler for your code.

The handler ``error`` will likewise put everything WARNING or higher in the
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
