import pytest
import asyncio

from unittest import mock

from PyQt5.QtCore import Qt, QAbstractItemModel, QPersistentModelIndex, QModelIndex
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QTreeView

from asyncua import ua

from uaclient.tree_ui import OpcTreeModel


@pytest.fixture
def tree_view(qtbot):
    view = QTreeView()
    qtbot.addWidget(view)
    yield view


# def test_init(tree_view):
#     with mock.patch.object(tree_view, "setModel") as mock_set_model:
#         model = OpcTreeModel(tree_view, [])

#     mock_set_model.assert_called_with(model)
#     assert model.columnCount() == 0
#     assert model.rowCount() == 0


# def test_init_columns(tree_view):
#     model = OpcTreeModel(
#         tree_view, [ua.AttributeIds.DisplayName, ua.AttributeIds.BrowseName]
#     )
#     assert model.columnCount() == 2
#     assert model.rowCount() == 0


# def test_header_data(tree_view):
#     model = OpcTreeModel(
#         tree_view, [ua.AttributeIds.DisplayName, ua.AttributeIds.BrowseName]
#     )

#     assert model.headerData(0, Qt.Orientation.Horizontal) == "Display Name"
#     assert model.headerData(1, Qt.Orientation.Horizontal) == "Browse Name"


# def test_header_data_all_possible_columns(tree_view):
#     model = OpcTreeModel(tree_view, [id for id in ua.AttributeIds])

#     assert model.columnCount() > 0

#     # Make sure no possible column throws KeyErrors when we're fetching its name
#     for column in range(model.columnCount()):
#         model.headerData(column, Qt.Orientation.Horizontal)


async def test_expand_root_node(qtbot, tree_view, async_server):
    model = OpcTreeModel(tree_view, [ua.AttributeIds.DisplayName])

    index = await async_server.register_namespace("test")
    node = await async_server.nodes.objects.add_variable(index, "TestVariable", 42)

    await model.set_root_node(async_server.nodes.objects)

    with qtbot.waitSignal(model.item_added, timeout=10000) as blocker:
        tree_view.expanded.emit(model.index(0, 0))
        await asyncio.sleep(1)

    assert blocker.args[0].node == node
