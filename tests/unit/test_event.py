import pytest
from unittest.mock import patch, Mock
from uaclient.mainwindow import EventUI
from PyQt5.QtGui import QStandardItemModel


@pytest.fixture
def server_node(server):
    yield server.nodes.server


@pytest.fixture
def window(server_node):
    window = Mock()
    window.get_current_node.return_value = server_node
    yield window


@pytest.fixture
def uaclient():
    yield Mock()


def test_event_subscription(window, server_node, uaclient, server):
    event_ui = EventUI(window, uaclient)

    event_ui._subscribe(server_node)

    # only one subscription per node is allowed, so this should not be added to _subscribed_nodes
    event_ui._subscribe(server_node)

    assert len(event_ui._subscribed_nodes) == 1
    assert event_ui._subscribed_nodes[0] == server_node


def test_unsubscribe_event_subscription(window, server_node, uaclient):
    event_ui = EventUI(window, uaclient)
    event_ui._subscribe(server_node)
    event_ui._unsubscribe(server_node)
    event_ui._unsubscribe(server_node)
    assert len(event_ui._subscribed_nodes) == 0
    uaclient.unsubscribe_events.assert_called_once()


def test_clear(window, server_node, uaclient):
    event_ui = EventUI(window, uaclient)
    event_ui._subscribe(server_node)
    # event_ui.model = Mock()

    with patch.object(QStandardItemModel, "clear") as q_clear:
        event_ui.clear()
    assert len(event_ui._subscribed_nodes) == 0
    q_clear.assert_called_once()
