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
Page: yes

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
* /<id>/flapping/
* /<id>/refresh/

Page: yes

/<id>/flapping/ GET/POST:
-------------------------

Button, "Clear", visible if flapState is flapping
Server must refetch (poll for update?) event afterwards.

/<id>/refresh/ GET:
-------------------

Refetch from zino server.

/<id>/update/ GET/POST:
-----------------------

* fetch forms for change (history/state)
* update. (client: which first, history or state? historically history first)

Linked to by: /<id>/
Links to?:
* /<id>/history/update/
* /<id>/state/

/<id>/attributes/ GET:
----------------------

Fetch and show the template with all attributes

Linked to by: /<id>/ somehow

/<id>/log/ GET:
---------------

Linked to by: /<id>/

/<id>/history/ GET/POST:
------------------------

Fetch history on GET, create a history message on POST

/<id>/history/update/ GET/POST:
-------------------------------

* add history! (form!)

Every change is a new history line.

On successful post, (server) refetch history.

/<id>/state/ GET/POST:
----------------------

* change admin-state (form!)

Form with changing of admin state and history line

We need to check if we can change history-line and state in two operations or
only one. If only one we must show an actual form, if two we can have one
endpoint for state and one for comment.

Every change is a new history line.

On successful post, (server) refetch whole event and history.

Linked to by:

* /<id>/
