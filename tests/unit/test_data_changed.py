import pytest
from uaclient.mainwindow import DataChangeUI
from PyQt5.QtGui import QStandardItemModel
from unittest.mock import patch, Mock


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


def test_subscribe_data_changed(window, server_node, uaclient, server):
    datachange_ui = DataChangeUI(window, uaclient)
    datachange_ui._subscribe()

    # only one subscription per node is allowed, so this should not be added to _subscribed_nodes
    datachange_ui._subscribe()

    assert len(datachange_ui._subscribed_nodes) == 1
    assert datachange_ui._subscribed_nodes[0] == server_node


def test_unsubscribe_data_changed(window, server_node, uaclient, server):
    datachange_ui = DataChangeUI(window, uaclient)
    datachange_ui._subscribe(server_node)
    assert len(datachange_ui._subscribed_nodes) == 1

    datachange_ui._unsubscribe(server_node)
    datachange_ui._unsubscribe(server_node)
    assert len(datachange_ui._subscribed_nodes) == 0


def test_clear(window, server_node, uaclient):
    datachange_ui = DataChangeUI(window, uaclient)
    datachange_ui._subscribe(server_node)

    with patch.object(QStandardItemModel, "clear") as q_clear:
        datachange_ui.clear()
    assert len(datachange_ui._subscribed_nodes) == 0
    q_clear.assert_called_once()
