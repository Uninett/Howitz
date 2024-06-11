import random
import pytest
from datetime import datetime, timezone
from zinolib.event_types import Event, AdmState, PortState, BFDState, ReachabilityState
from howitz.endpoints import sort_events, EventSort, get_priority
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


class TestGetPriority:
    def test_closed_events_that_indicate_status_down_should_have_priority_0(self, events_of_each_type):
        events = events_of_each_type(adm_state=AdmState.CLOSED, is_down=True)

        for event in events:
            assert event.is_down() is True
            priority = get_priority(event)
            assert priority == 0

    def test_closed_events_that_indicate_status_up_should_have_priority_0(self, events_of_each_type):
        events = events_of_each_type(adm_state=AdmState.CLOSED, is_down=False)

        for event in events:
            assert event.is_down() is False
            priority = get_priority(event)
            assert priority == 0

    def test_ignored_events_that_indicate_status_down_should_have_priority_1(self, events_of_each_type):
        events = events_of_each_type(adm_state=AdmState.IGNORED, is_down=True)

        for event in events:
            assert event.is_down() is True
            priority = get_priority(event)
            assert priority == 1

    def test_ignored_events_that_indicate_status_up_should_have_priority_1(self, events_of_each_type):
        events = events_of_each_type(adm_state=AdmState.IGNORED, is_down=False)

        for event in events:
            assert event.is_down() is False
            priority = get_priority(event)
            assert priority == 1

    def test_open_events_that_indicate_status_up_should_have_priority_2(self, events_of_each_type):
        events = events_of_each_type(adm_state=AdmState.OPEN, is_down=False)

        for event in events:
            assert event.is_down() is False
            priority = get_priority(event)
            assert priority == 2

    def test_confirmwait_events_that_indicate_status_down_should_have_priority_2(self, events_of_each_type):
        events = events_of_each_type(adm_state=AdmState.CONFIRM_WAIT, is_down=True)

        for event in events:
            assert event.is_down() is True
            priority = get_priority(event)
            assert priority == 2

    def test_confirmwait_events_that_indicate_status_up_should_have_priority_2(self, events_of_each_type):
        events = events_of_each_type(adm_state=AdmState.CONFIRM_WAIT, is_down=False)

        for event in events:
            assert event.is_down() is False
            priority = get_priority(event)
            assert priority == 2

    def test_events_with_unspecified_adm_state_should_have_priority_2(self, events_of_each_type):
        events = events_of_each_type(adm_state="", is_down=False)
        events += events_of_each_type(adm_state="", is_down=True)

        for event in events:
            priority = get_priority(event)
            assert priority == 2

    def test_events_with_garbage_adm_state_should_have_priority_2(self, events_of_each_type):
        events = events_of_each_type(adm_state=AdmState.UNKNOWN, is_down=False)
        events += events_of_each_type(adm_state=AdmState.UNKNOWN, is_down=True)

        for event in events:
            priority = get_priority(event)
            assert priority == 2

    def test_working_events_that_indicate_status_down_should_have_priority_3(self, events_of_each_type):
        events = events_of_each_type(adm_state=AdmState.WORKING, is_down=True)

        for event in events:
            assert event.is_down() is True
            priority = get_priority(event)
            assert priority == 3

    def test_working_events_that_indicate_status_up_should_have_priority_3(self, events_of_each_type):
        events = events_of_each_type(adm_state=AdmState.WORKING, is_down=False)

        for event in events:
            assert event.is_down() is False
            priority = get_priority(event)
            assert priority == 3

    def test_waiting_events_that_indicate_status_down_should_have_priority_3(self, events_of_each_type):
        events = events_of_each_type(adm_state=AdmState.WAITING, is_down=True)

        for event in events:
            assert event.is_down() is True
            priority = get_priority(event)
            assert priority == 3

    def test_waiting_events_that_indicate_status_up_should_have_priority_3(self, events_of_each_type):
        events = events_of_each_type(adm_state=AdmState.WAITING, is_down=False)

        for event in events:
            assert event.is_down() is False
            priority = get_priority(event)
            assert priority == 3

    def test_open_events_that_indicate_status_down_should_have_priority_4(self, events_of_each_type):
        events = events_of_each_type(adm_state=AdmState.OPEN, is_down=True)

        for event in events:
            assert event.is_down() is True
            priority = get_priority(event)
            assert priority == 4


@pytest.fixture()
def get_priority_boilerplate_event():
    """
        Values that are required to create event, but are irrelevant for determining priority
    """
    now = datetime.now(timezone.utc)
    event_id = random.randint(0, 1000000)
    res = {
        "id": event_id,
        "router": "router1",
        'opened': now,
        'updated': now,
        'if_index': 1234,
        'lastevent': '',
        'bgp_AS': '',
        'remote_AS': 1234,
        'remote_addr': '127.0.0.1',
        'peer_uptime': 1234,
        'bfd_ix': 1234,
        'alarm_type': '',
    }
    return res


@pytest.fixture
def events_of_each_type(get_priority_boilerplate_event):
    """
    :param get_priority_boilerplate_event: fixture
    :return: list containing one event of each known `Event.Type`
    """

    def _events_of_each_type(adm_state: AdmState, is_down: bool):
        res = []
        make_is_down_true = {
            'port_state': PortState.DOWN,
            'bgp_OS': 'down',
            "bfd_state": BFDState.DOWN,
            'alarm_count': 1,
            "reachability": ReachabilityState.NORESPONSE,
        }
        make_is_down_false = {
            'port_state': PortState.UP,
            'bgp_OS': '',
            "bfd_state": BFDState.UP,
            'alarm_count': 0,
            "reachability": ReachabilityState.REACHABLE,
        }
        for _type in Event.Type:
            if is_down:
                res.append(
                    Event.create(
                        {**get_priority_boilerplate_event, **make_is_down_true, 'type': _type, 'adm_state': adm_state}))
            else:
                res.append(
                    Event.create(
                        {**get_priority_boilerplate_event, **make_is_down_false, 'type': _type,
                         'adm_state': adm_state}))

        return res

    return _events_of_each_type
