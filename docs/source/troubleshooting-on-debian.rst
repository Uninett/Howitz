=========================
Troubleshooting on Debian
=========================

Visit the URL of the site. If there is a "50x"-error, and the logs are not
exported to an external log tool you need to log in to the console of the site.

Check systemctl status
======================

Run ``sudo systemctl status howitz-gunicorn.service``. If it says "disabled" or
there is red text, Howitz didn't start properly or has crashed. Go to
`Check journalctl`_

Check journalctl
================

Run `journalctl -since="-1h" howitz-gunicorn.service`. This will show the
gunicorn log for the last hour.

If there is an exception mentioning "pydantic", you might have forgotten to
configure everything. Remember that if ``devmode`` is ``false``, then
``listen`` must be set to an IP address and ``port`` must be set to a port
number.
