import sys
from typing import Any, List
import itertools
import functools
from datetime import datetime

from qasync import asyncSlot
from PyQt5.QtCore import (
    Qt,
    QModelIndex,
    QPersistentModelIndex,
    pyqtSignal,
    QAbstractItemModel,
    QVariant,
)

import asyncio
from asyncua import Node
from asyncua.ua import AttributeIds
from .opc_tree_item import OpcTreeItem

_UA_ATTRIBUTE_NAMES = {
    AttributeIds.NodeId: "Node ID",
    AttributeIds.NodeClass: "Node Class",
    AttributeIds.BrowseName: "Browse Name",
    AttributeIds.DisplayName: "Display Name",
    AttributeIds.Description: "Description",
    AttributeIds.WriteMask: "Write Mask",
    AttributeIds.UserWriteMask: "User Write Mask",
    AttributeIds.IsAbstract: "Is Abstract",
    AttributeIds.Symmetric: "Symmetric",
    AttributeIds.InverseName: "Inverse Name",
    AttributeIds.ContainsNoLoops: "Contains No Loops",
    AttributeIds.EventNotifier: "Event Notifier",
    AttributeIds.Value: "Value",
    AttributeIds.DataType: "Data Type",
    AttributeIds.ValueRank: "Value Rank",
    AttributeIds.ArrayDimensions: "Array Dimensions",
    AttributeIds.AccessLevel: "Access Level",
    AttributeIds.UserAccessLevel: "User Access Level",
    AttributeIds.MinimumSamplingInterval: "Minimum Sampling Interval",
    AttributeIds.Historizing: "Historizing",
    AttributeIds.Executable: "Executable",
    AttributeIds.UserExecutable: "User Executable",
    AttributeIds.DataTypeDefinition: "Data Type Definition",
    AttributeIds.RolePermissions: "Role Permissions",
    AttributeIds.UserRolePermissions: "User Role Permissions",
    AttributeIds.AccessRestrictions: "Access Restrictions",
    AttributeIds.AccessLevelEx: "Access Level",
}


class OpcTreeModel(QAbstractItemModel):
    item_added = pyqtSignal(OpcTreeItem)
    item_removed = pyqtSignal(OpcTreeItem)

    def __init__(self, columns: List[AttributeIds]):
        super().__init__()
        self._columns = columns
        self._root_item = OpcTreeItem(self, None, QPersistentModelIndex(), columns)
        self._root_item.data_changed.connect(self._handle_data_changed)
        self._root_item.item_added.connect(self.item_added)
        self._root_item.item_removed.connect(self.item_removed)

    def index(
        self, row: int, column: int, parent: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_item = parent.internalPointer() if parent.isValid() else self._root_item
        child_item = parent_item.child(row)
        if child_item is None:
            return QModelIndex()

        return self.createIndex(row, column, child_item)

    def parent(self, child: QModelIndex) -> QModelIndex:
        if not child.isValid():
            return QModelIndex()

        child_item = child.internalPointer()
        parent_item = child_item.parent()

        if parent_item is None or parent_item == self._root_item:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.column() > 0:
            return 0

        parent_item = parent.internalPointer() if parent.isValid() else self._root_item
        if parent_item is None:
            return 0

        return parent_item.child_count()

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        parent_item = parent.internalPointer() if parent.isValid() else self._root_item
        if parent_item is None:
            return 0

        return parent_item.column_count()

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None

        item = index.internalPointer()
        return item.data(index.column())

    async def set_root_node(self, node: Node):
        index = self.index(0, 0)
        item = OpcTreeItem(self, node, QPersistentModelIndex(), self._columns)
        await item.initialize()

        self.beginInsertRows(index, 0, 0)
        self._root_item.add_child(item)
        self.endInsertRows()

    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        item = parent.internalPointer()

        if not parent.isValid() or item.children_fetched():
            return super().hasChildren(parent)

        return True

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> QVariant:
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return QVariant(_UA_ATTRIBUTE_NAMES[self._columns[section]])
        return QVariant()

    @asyncSlot(QModelIndex, QModelIndex)
    async def _handle_data_changed(
        self, start_index: QModelIndex, end_index: QModelIndex
    ) -> None:
        self.dataChanged.emit(start_index, end_index)

    @asyncSlot(QModelIndex)
    async def handle_expanded(self, index: QModelIndex) -> None:
        if not index.isValid():
            return

        # Refresh and initialize the children for the item that was just expanded
        await self._refresh_children(index)

    @asyncSlot(QModelIndex)
    async def handle_collapsed(self, index: QModelIndex) -> None:
        if not index.isValid():
            return

        await self._reset_children(index)

    async def _reset_children(self, index: QModelIndex) -> None:
        if not index.isValid():
            return

        item = index.internalPointer()
        item.reset_children(
            before_remove_children=self.beginRemoveRows,
            after_remove_children=self.endRemoveRows,
        )

    async def _refresh_children(self, index: QModelIndex) -> None:
        if not index.isValid():
            return

        item = index.internalPointer()

        await self._reset_children(index)  # Remove old children before we add new ones

        await item.fetch_children(
            before_add_children=self.beginInsertRows,
            after_add_children=self.endInsertRows,
        )

        await item.initialize_children()
