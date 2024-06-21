============================================
Howitz - Zino web client with HTMx and Flask
============================================


Running Howitz step-by-step overview
====================================

1. Preparation step:
    1. Make sure you have ``python3``, ``pip`` and ``git`` installed.
    2. Download `Howitz from the GitHub repo <https://github.com/Uninett/Howitz>`_.

2. Installation step:
    1. Create and activate `venv`, from the project root folder run::

        $ python3 -m venv howitzvenv
        $ source howitzvenv/bin/activate

    2. Install dependencies, from the project root folder run::

        $ pip install -e .

    Read more about installation in the `Install safely`_ section.

3. Configuration step:
    The easiest way to configure Howitz is via a ``toml`` file.

    1. Create an empty ``.howitz.toml`` file in the project root folder.
    2. Copy the values from the preferred example config file ``howitz.*.example`` to ``.howitz.toml``. Here using the ``howitz.min.toml.example``::

        $ cp howitz.min.toml.example .howitz.toml

    3. Open ``.howitz.toml`` and fill out at least the config values: ``SECRET_KEY`` and ``server``. Those values are left empty in the example config file.
    4. Play around with the config values in ``.howitz.toml``, if desired.

    Read more about other configuration methods, different configurations options and variables in the `Configuration`_ section.

    **NB!**:

        When configuring for production, make sure that ``.howitz.toml`` is appropriately adjusted as described in the `Config file for production`_ section.

4. User management step:
    1. Check if you have an existing user in the Howitz database, from the project root folder run::

        $ flask --app howitz user list

    2. Create a new user if you do not have one already, from the project root folder run::

        $ flask --app howitz user create USERNAME PASSWORD TOKEN

    Read more about user management and other commands in the `User management`_ section.

5. Run Howitz:
    1. Start Howitz as a flask app, from the project root folder run::

        $ python3 -m howitz

    2. Open Howitz in the browser. By default in dev, Howitz will be accessible at http://127.0.0.1:5000.

    Read more about running Howitz in the `Play around`_ section.


Play around
===========

Install safely
--------------

Create and activate a virtualenv, install dependencies in that virtualenv::

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

    Check out the `Example config-file (for development)`_ section.


After both installation (see `Install safely`_) and `Configuration`_ are done, you can run Howitz by running
either::

    $ python3 -m howitz

or::

    $ flask --app howitz run

This will get you a web interface running at http://127.0.0.1:5000/.
The database (see `User management`_) is by default put in the current directory.

**NB!**:

    If you get an error when attempting to log in for the first time, make sure you have created a user in the Howitz
    database, see `Managing the Howitz user database`_.


Run in production
-----------------

You need to have either a minimal configuration file or set two environment variables, see `Configuration`_.

Tip for quickly setting up an extensive config file:

    Check out the `Example config-file (for development)`_ section. Make sure the config file is appropriate for
    production, see `Config file for production`_.


Always use an installed Howitz.

* gunicorn: ``gunicorn 'howitz:create_app()'``
* waitress: ``waitress-serve --call howitz:create_app``

See https://flask.palletsprojects.com/en/3.0.x/deploying/ for more options and
additional details, and the respective server's docs for server-specific
details.

User management
===============

Due to how Zino protocol 1 does logins, the password (here called token) needs
to be stored in plain text in every client. For security reasons it is not
desirable to ever store this token in a cookie or otherwise in a browser, so
instead the token is stored where the browser cannot get to it, in a user
database local to the frontend server.

When logging in to Howitz a user uses a normal password (not the token) which
is used to safely fetch the token for connecting to the Zino protocol 1 server.
This password can be treated like any other password and be put in a vault or
a password manager.

The mapping from websafe password to legacy token is done via a user database.
The Zino backend server admin creates a token and username. The frontend server
admin creates a local user with the backend username and token, and a password
preferrably chosen by the users themselves.

We are planning to allow users to change the frontend password eventually but
we do not wish for the backend token to ever be seen by a browser in any
fashion.

Managing the Howitz user database
---------------------------------

Users are by default stored in the file ``./howitz.sqlite``, this can be changed
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

About username, password and token values
-----------------------------------------

When running `commands <All available commands>`_ to Howitz user database, you may need to provide all or some of the options.

``USERNAME``
    an **existing** username on your Zino server. **You will need to provide it when logging in to Howitz on web.**

``TOKEN``
    token assigned to a given username on your Zino server. In the original Zino protocol this value is referred to as a *Secret*.
    Store it in the Howitz database once and forget about it when logging in to Howitz on web.

``PASSWORD``
    a password of your choice. This one is purely Howitz-specific. **You will need to provide it when logging in to Howitz on web.**



All available commands
----------------------

``create``
    creates a user, the username needs to be unique

``delete``
    removes an existing user

``list``
    shows all known usernames

``update``
    is used to change the web password or Zino token for an existing user


Configuration
=============

Howitz *can* run without a configuration file. Default values will be used for
listen-address (127.0.0.1), port (5000) and storage location
(./howitz.sqlite3). However, at minimum you also need to pass in a SECRET_KEY
for Flask and a Zino server address to fetch events from.

These can be passed via a configuration file, ``.howitz.toml`` (stored in the current directory or user home
directory) or via environment variables.

Via a ``.howitz.toml`` configuration file::

    [flask]
    SECRET_KEY = "long string!"

    [zino.connections.default]
    server = "zino.server.domain"

Directly via environment variables::

    HOWITZ_SECRET_KEY="long string!" HOWITZ_ZINO1_SERVER="zino.server.domain"

All config options can be overruled by environment variables. Prefix them with
"HOWITZ\_" for Flask-specific options and "HOWITZ_ZINO1\_" for Zino-specific
options. It is also possible to override logging by setting "HOWITZ_LOGGING" to
a string of a Python dict but we do not recommend it, use a config file instead.

The refresh interval value specifies the frequency with which events are checked for updates, i.e., are synchronized. This value can be modified by adding, for example, ``refresh_interval = 10`` to
the ``[howitz]``-section, or by setting the environment variable ``HOWITZ_REFRESH_INTERVAL`` to a new value.
Refresh interval values are in seconds and must be integers. The default value is ``5`` seconds.

Debugging can be turned on either by adding ``DEBUG = true`` to the
``[flask]``-section or setting the environment variable ``HOWITZ_DEBUG`` to ``1``.

The default timezone for timestamps is ``UTC``. Timezone information can be changed by adding ``timezone = "LOCAL"`` to
the ``[howitz]``-section or setting the environment variable ``HOWITZ_TIMEZONE`` to ``LOCAL``. Timezone values other
than ``LOCAL`` and ``UTC`` provided in config will be ignored and fall back to ``UTC``.

Howitz uses caching. You can configure preferred caching type under the ``[flask]``-section.
See `Flask-Caching's configuration docs <https://flask-caching.readthedocs.io/en/latest/#configuring-flask-caching>`_ for available configuration options.
Default cache type is `SimpleCache <https://flask-caching.readthedocs.io/en/latest/#simplecache>`_.


Configuring which Zino servers to use
-------------------------------------

Howitz will use the configuration in ``[zino.connections.default]``. There may
be other sections starting with ``zino.connections``, these are a holdover from
CLI clients being able to choose a specific server with a CLI flag on startup.
See `future plans`_.

In addition to ``server``, you can also set an explicit ``port``, as an
integer. The default is port ``8001``. In addition to this port there is
a hardcoded usage of port ``8002`` for the push update service. (You might find
mentions of NTIE, this is an internal name for the update service.)


Configuring order in which events are sorted
--------------------------------------------

Sorting method can be changed under the ``[howitz]``-section by adding::

    sort_by = "<valid sorting method>"

Valid sorting methods are:

* *raw* - The same order in which Zino server sends events (by ID, ascending).
* *lasttrans* - Newest transaction first, all IGNORED at the bottom. Default sorting in curitz.

* *severity* - Events with highest priority first, grouped by event type. Priority takes into account both whether event signifies any disturbance, event's administrative phase and event's type, so there might not be continuous blocks of color. Existing method in Ritz TK, but it is called 'default' there.
* *down-rev* - Shortest/none downtime first. Identical to an existing method in Ritz TK.
* *down* - Longest downtime first. Identical to an existing method in Ritz TK.
* *upd-rev* - Events with the most recent update date first. Identical to an existing method in Ritz TK.
* *upd* - Events with the oldest update date first. Identical to an existing method in Ritz TK.
* *age-rev* - Oldest events first. Identical to an existing method in Ritz TK.
* *age* - Newest events first. Identical to an existing method in Ritz TK.


Example config-file (for development)
-------------------------------------

For development, copy the contents of the included file ``howitz.toml.example`` to ``.howitz.toml`` in the same directory.

1. Set ``[flask] -> SECRET_KEY`` to some long string.
2. Set ``[zino.connections.default] -> server`` to the address of a Zino 1 server.
3. Optionally set ``[zino.connections.other] -> server`` to the address of a fallback Zino
   1 server. If the default server stops working you can swap "other" with
   "default" in the config-file and keep on working. If you don't set it to
   anything, keep it commented out or remove it.

As for logging, there is a handler ``debug`` that will copy everything DEBUG or higher to a file
``debug.log``, you might want to use this handler for your code.

The handler ``error`` will likewise put everything WARNING or higher in the
``error.log`` file.

Config file for production
--------------------------

It is better to control ``[flask] -> SECRET_KEY`` and
``[zino.connections.default] -> server`` via environment variables than
hardcoding them in the config file. It's best to delete them from the config
file.

``[flask] -> DEBUG`` must be ``false``. Keeping it as ``true`` may lead to
surprising bugs.

``[howitz] -> devmode`` must be ``false``. Due to ``devmode`` being ``false``
it becomes necessary to explicitly write in the ``[howitz]`` section which
IP-address and port to listen on::

    [howitz]
    devmode = false
    listen = "127.0.0.1"
    port = 5000

(127.0.0.1 and 5000 are the Flask defaults.)

``[logging]`` will need adjustments. Increase the level of the ``wsgi``-handler
or only use the ``error`` handler. Change the error-handler to ship its log
somewhere else, via syslog or Sentry or similar.


Run tests
=========

Linting: ``tox -e lint``

Tests: ``tox``


.. _future plans:

Future plans
============

We hope to be able to automatically failover to other servers in
``zino.connections``.
