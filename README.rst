======================================
Howitz - Mock Zino with HTMx and Flask
======================================

Play around
===========

Make and activate a virtualenv, install dependencies in that virtualenv::

        $ python3.11 -m venv howitz
        $ source howitz/bin/activate
        $ pip install -e .


On this branch you need a version of zinolib that is still a work-in-progress (hmpf's decoupling branch).
Build it with f.e. `pyproject-build`. Make sure that zinolib dependency is reinstalled as the newly built wheel file.

```
pip install --force-reinstall zinolib-example.whl
```

CD into the source and run a a local webserver::

        $ cd src
        $ python3.11 -m howitz

You should now have a server running on http://127.0.0.1:9000/ (Port chosen not
to clash with other things.)
