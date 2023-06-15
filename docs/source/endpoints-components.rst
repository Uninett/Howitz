Endpoints and components needed
===============================

List of events: stored as a module global so all instances get the same data.

/hello:
-------

Shows off bottle with jinja2, removed when we get used to things

/ GET:
------

* redirect to login, eventually, probably
* list of open events

Links to: /<id>/

/<id>/ GET:
-----------

* single event
* triggers load of history/log from backend

Multiple possibilities:
* load everything and show in one window/dialog?
* Hide history/log behind another click?
* Accordion to widen and show a bit more, the buttons and links?
* Accordion inside the accordion for change, log, history, all attributes?

Linked to by: /
Links to?:
* /<id>/history/
* /<id>/log/
* /<id>/attributes/
* /<id>/state/

/<id>/attributes/ GET:
---------------------

Fetch and show the template with all attributes

Linked to by: /<id>/ somehow

/<id>/log/ GET:
---------------

Linked to by: /<id>/

/<id>/history/ GET:
-------------------

Links to: /<id>/state/

/<id>/state/ GET/POST:
----------------------

* change admin-state (form!)

Form with changing of admin state and history line

We need to check if we can change history-line and state in two operations or
only one. If only one we must show an actual form, if two we can have one
endpoint for state and one for comment.

Is every change a new history line or can history be altered?

Linked to by:

* /<id>/
* /<id>/history/
