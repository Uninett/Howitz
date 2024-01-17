===============================================
Manual install on debian with nginx and certbot
===============================================

Log in, you need to be able to sudo to root.

Preparations
============

#. Install nginx:

    .. code-block:: console

        $ sudo apt install nginx
        .. output ..
        $

#. Start nginx:

    .. code-block:: console

        $ sudo systemctl start nginx
        $

#. Visit MYDOMAIN in a browser

    The default nginx page should now be up and running on MYDOMAIN, port 80.
    Double-check that the page is reachable *worldwide*, that there is no
    firewall or similar blocking port 80. This is needed for autogenerating the
    certificate later.

#. Install venv:

    .. code-block:: console

        $ sudo apt install python3-venv
        .. output ..
        $

#. Create a user for howitz:

    .. code-block:: console

        $ sudo useradd -m -s /bin/bash howitz
        $

   This creates a user "howitz" with the group "howitz" which owns the new
   directory "/home/howitz". The user has (and needs) no password and the shell
   is set to bash. The "howitz"-user should NOT have root/sudo-access.

#. Become howitz and create a venv:

    .. code-block:: console

        $ sudo su - howitz
        howitz@myserver:~$ python3 -m venv .venv
        howitz@myserver:~$

   This creates a directory ".venv"

#. Activate the venv:

    .. code-block:: console

        howitz@myserver:~$ source .venv/bin/activate
        (.venv) howitz@myserver:~$

   Now only the python libraries installed in the venv are easily available.


Get the source code and dependencies
====================================

Pick one of the below methods:

Use the raw source
------------------

This is the only way to install the locked dependencies.

#. Install git:

    .. code-block:: console

        $ sudo apt install git
        .. lots of stuff ..
        $

#. Switch to howitz-user and activate the venv:


    .. code-block:: console

        $ sudo su - howitz
        howitz@myserver:~$
        howitz@myserver:~$ source .venv/bin/activate
        (.venv) howitz@myserver:~$

#. Get source code via git:

    .. code-block:: console

        (.venv) howitz@myserver:~$ git clone https://github.com/Uninett/Howitz.git
        .. lots of stuff ..
        (.venv) howitz@myserver:~$

   This creates a directory "Howitz" with the source code.

#. Enter the Howitz directory:

    .. code-block:: console

        (.venv) howitz@myserver:~$ cd Howitz
        (.venv) howitz@myserver:~/Howitz$

#. Install the locked dependencies:

    .. code-block:: console

        (.venv) howitz@myserver:~/Howitz$ pip install -r requirements-frozen.txt
        .. lots of stuff ..
        (.venv) howitz@myserver:~/Howitz$

#. Install howitz into the venv:

    .. code-block:: console

        (.venv) howitz@myserver:~/Howitz$ pip install .
        .. lots of stuff ..
        (.venv) howitz@myserver:~/Howitz$

Install via pip
---------------

TBD

Configure howitz
================

See howitz's README.rst for how to configure howitz and create a user.

User database
-------------

Change ``[howitz] storage`` to ``/home/howitz/howitz.sqlite3``. Then ensure
that only the howitz-user has access.

#. If the file does not exist, create it by running:

    .. code-block:: console

        (.venv) howitz@myserver:~$ flask -A howitz user
        ..stuff ..
        (.venv) howitz@myserver:~$

#. Fix the permissions:

    .. code-block:: console

        (.venv) howitz@myserver:~$ chmod 600 howitz.sqlite3
        (.venv) howitz@myserver:~$

You can store the canonical user database somewhere else and copy it in to the
server after a change. Then the mode can be "400" instead of "600".

Logging
-------

We recommend storing the debug-log in ``/var/log/howitz/debug.log``.

#. Create the directory ``/var/log/howitz``:

    .. code-block:: console

        $ sudo mkdir var/log/howitz
        $

#. Change ``[logging.handlers.debug] filename`` to
    ``/var/log/howitz/debug.log`` in the howitz config file.

    You might want to change the handler to an ordinary ``logging.FileHandler``
    and set up rotation in the OS instead.

We recommend turning on the error.log, and sending it to a log accumulator
instead of a local file, be it via a ``logging.StreamHandler`` or something
else. Remember to activate the handler in ``[logging.loggers.*]``. Also, don't
forget to install any 3rd party handlers you wish to use into the venv.

Any further tips for logging is way beyond scope for this howto.

Set up the web server
=====================

This assumes that you will only be running a single domain on the server,
avoiding some extra steps.

Gunicorn
--------

#. As howitz, in the venv, install gunicorn:

    .. code-block:: console

        (.venv) howitz@myserver:~/Howitz$ pip install gunicorn

#. Switch back to your own user

    .. code-block:: console

        (.venv) howitz@myserver:~/Howitz$ exit
        .. output ..
        $

#. Make the necessary systemd service file to run gunicorn:

   .. literalinclude:: howitz-gunicorn.service
       :caption: /etc/systemd/system/howitz-gunicorn.service :download:`Download <howitz-gunicorn.service>`

#. Start and enable the systemd service:

    .. code-block:: console

        $ sudo systemctl start howitz-gunicorn
        $ sudo systemctl enable howitz-gunicorn
        .. output ..
        $

#. Check that gunicorn is running correctly:

    .. code-block:: console

        $ sudo systemctl status howitz-gunicorn
        .. lots of stuff ..
        $

Secure the web server
---------------------

You **will** need a SSL/TLS certificate in order to run securely. You can pay
for a certificate or get a free one from `letsencrypt
<https://letsencrypt.org/>`_.

How to get and install a third-party cerificate will not be described in this
howto.

Create a certificate with Certbot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``certbot`` is one of many systems to create and automatically update SSL/TLS
certificates from `letsencrypt <https://letsencrypt.org/>`_.

More documentation at `Certbot Documentation <https://eff-certbot.readthedocs.io/en/latest/>`_

#. Install certbot:

    .. code-block:: console

        $ sudo apt install python3-certbot-nginx

#. Create a certificate for your domain and hook it into nginx

    .. code-block:: console

        $ sudo certbot --nginx -d howitz.uninett.no
        .. lots of stuff, worth reading ..
        $

   If it is the first time running certbot on this server, you will be prompted
   to enter an email address and agree to the terms of service. Make sure that
   the email address is one that is actually read.

   Then, certbot will contact the letsencrypt server in order to create the
   certificate. The letsencrypt server will in turn contact MYDOMAIN on port
   80. If the server is not reachable from letsencrypt, you will get no
   certificate.

   A path looking like ``/etc/letsencrypt/live/MYDOMAIN/fullchain.pem`` will be
   part of the output. That's where the certificate to use is stored.

   Note that Certbot will have made changes to ``/etc/nginx/sites-available/default``

#. Test renewal:

    .. code-block:: console

        $ sudo certbot renew --dry-run
        .. lots of stuff ..
        $

#. Ensure that MYDOMAIN is reachable on port 443 from those machines that will
   have access to howitz.

Configure nginx
---------------

#. Edit ``/etc/nginx/sites-available/default``:

    Look for the line that contains ``server_name MYDOMAIN; # managed by
    Certbot``. This line is inside a block that starts with ``server {`` and
    ends with ``}``. All you'll change is inside this block.

#. Inside the block you found above, find the block starting with
   ``location / {`` and ending with another ``}``. Replace the entire block with::

        location / {
            include proxy_params;
            proxy_pass http://unix:/home/howitz/.venv/howitz.sock;
        }

    Save and exit the file.

#. Check for errors in the ``default``-file:

    .. code-block:: console

        $ sudo nginx -t
        .. output ..
        $

#. Restart nginx:

    .. code-block:: console

        $ sudo systemctl restart nginx
        $

#. Visit https://MYDOMAIN

TADA!

Troubleshooting
===============

I get a "500 Server Error" page instead of the howitz landing page!
-------------------------------------------------------------------

Did you remember to configure howitz? Double-check that you've set the
``[flask] SECRET_KEY`` and ``[zino.connection.default] server``. The values are
both strings so remember to quote them.

You'll need to restart gunicorn and nginx after any changes to this file, like
so:

.. code-block:: console

    $ sudo systemctl restart howitz-gunicorn
    $ sudo systemctl restart nginx
    $

I have a "502 Bad Gateway" page
-------------------------------

The problem is either in gunicorn or howitz. The gunicorn logs can be seen
with:

.. code-block:: console

    $ sudo journalctl --unit=howitz-gunicorn | more

The howitz-logs are whatever they were set to be in the howitz config file. It
might be that gunicorn does not have permission to write to them.

I can't find the howitz logs
----------------------------

The example config writes to a debug-log in ``/home/howitz/Howitz/debug.log``,
and does not write anything to the file ``/home/howitz/Howitz/error.log``. If
you've changed the logging config, check for the correct location there.
