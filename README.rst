============================================
Howitz - Zino web client with HTMx and Flask
============================================

Play around
===========

Make and activate a virtualenv, install dependencies in that virtualenv::

    $ python3 -m venv howitz
    $ source howitz/bin/activate
    $ pip install -e .

On this branch you need a version of zinolib that is still a work-in-progress (hmpf's decoupling branch).
Build it with f.e. `pyproject-build`. Make sure that zinolib dependency is reinstalled as the newly built wheel file.

::

    pip install --force-reinstall zinolib-example.whl

After ``pip install`` run a local webserver in development-mode::

    $ python3 -m howitz --devmode

You should now have a server running on http://127.0.0.1:9000/ (Port chosen not
to clash with other things.)

For other command line arguments see::

    $ python3 -m howitz -h

Run tests
=========

::

    tox
