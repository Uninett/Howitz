import pytest
from datetime import datetime, timezone
from zinolib.event_types import Event, AdmState
from howitz.endpoints import sort_events, EventSort
from flask import Flask

test_app = Flask("test")


class TestSortEvents:
    def test_default_sorting_should_not_change_dict_order(self, events):
        with test_app.app_context():
            sorted_events = sort_events(events, sort_by=EventSort.DEFAULT)
        assert sorted_events.keys() == events.keys()

    def test_upd_sorting_should_order_by_oldest_updated_value_first(self, events):
        with test_app.app_context():
            sorted_events = sort_events(events, sort_by=EventSort.UPD)
        prev_event = None
        for event_id, event in sorted_events.items():
            if prev_event:
                assert prev_event.updated <= event.updated, "Older event seen after younger event"
            prev_event = event


@pytest.fixture()
def events():
    events_dict = {}
    now = datetime.now(timezone.utc)
    for i in range(3):
        event_id = i+1
        event = Event(
            id=event_id,
            type=Event.Type.PORTSTATE,
            adm_state=AdmState.IGNORED,
            router="router1",
            opened=now,
            updated=now,
        )
        events_dict[event_id] = event
    return events_dict
