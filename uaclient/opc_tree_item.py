import itertools
import asyncio
import collections
from typing import Optional, Any, List, Callable

from qasync import asyncSlot
from PyQt5.QtCore import (
    QObject,
    pyqtSignal,
    QPersistentModelIndex,
    QModelIndex,
    QAbstractItemModel,
)

from asyncua import Node
from asyncua import ua

_BATCH_SIZE = 5


# This exists in itertools in Python 3.12, but we're not there yet
def _batched(iterable, batch_size):
    iterator = iter(iterable)
    while batch := tuple(itertools.islice(iterator, batch_size)):
        yield batch


class OpcTreeItem(QObject):
    data_changed = pyqtSignal(QModelIndex, QModelIndex)
    item_added = pyqtSignal(QObject)
    item_removed = pyqtSignal(QObject)

    def __init__(
        self,
        model: QAbstractItemModel,
        node: Node,
        parent_index: QPersistentModelIndex,
        columns: List[ua.AttributeIds],
        *,
        parent: Optional["OpcTreeItem"] = None,
    ):
        super().__init__(parent)
        self.node = node
        self._model = model
        self._parent_index = parent_index
        self._children: List["OpcTreeItem"] = []

        self._display_name = ""
        self._value = None
        self._children_fetched = False

        self._columns = columns
        self._model_column_to_ua_column = dict(
            [(index, column) for index, column in enumerate(columns)]
        )

        self._ua_column_to_model_column = dict(
            [(column, index) for index, column in enumerate(columns)]
        )

        # Create an dict that maintains column order
        self._data = collections.OrderedDict([(column, None) for column in columns])

    async def initialize(self) -> None:
        values = await self.node.read_attributes(self._columns)
        for index, column in enumerate(self._columns):
            self.set_data(column, values[index].Value.Value, emit=False)

        # Emit signal letting subscribers know what data has changed here
        start_index = QModelIndex(self.persistent_index(0))
        end_index = QModelIndex(self.persistent_index(self.column_count() - 1))
        self.data_changed.emit(start_index, end_index)

        # Emit signal letting subscribers know that a new item has been added/initialized
        self.item_added.emit(self)

    async def initialize_children(self) -> None:
        await asyncio.gather(*[child.initialize() for child in self._children])

    async def fetch_children(
        self,
        *,
        before_add_children: Optional[Callable[[QModelIndex, int, int], None]] = None,
        after_add_children: Optional[Callable[[], None]] = None,
    ) -> None:
        children = await self.node.get_children()
        index = self.persistent_index(0)
        non_persistent_index = QModelIndex(index)
        batch_index = self.child_count()
        for child_batch in _batched(children, _BATCH_SIZE):
            batch_size = len(child_batch)

            if before_add_children is not None:
                before_add_children(non_persistent_index, batch_index, batch_size - 1)

            for child in child_batch:
                item = OpcTreeItem(self._model, child, index, self._columns)
                self.add_child(item)

            if after_add_children is not None:
                after_add_children()

            batch_index += batch_size

        self._children_fetched = True

    def set_parent_index(self, index: QPersistentModelIndex) -> None:
        self._parent_index = index

    def children_fetched(self) -> bool:
        return self._children_fetched

    def add_child(self, child: "OpcTreeItem") -> None:
        child.setParent(self)
        child.set_parent_index(self.persistent_index(0))
        child.data_changed.connect(self.data_changed)
        child.item_added.connect(self.item_added)
        child.item_removed.connect(self.item_removed)
        self._children.append(child)

    def child(self, row: int) -> Optional["OpcTreeItem"]:
        return self._children[row]

    def persistent_index(self, column) -> QPersistentModelIndex:
        if not self._parent_index.isValid():
            # This must be the root item
            return QPersistentModelIndex(self._model.index(0, 0))

        return QPersistentModelIndex(
            self._model.index(self.row(), column, QModelIndex(self._parent_index))
        )

    def reset_children(
        self,
        *,
        before_remove_children: Optional[
            Callable[[QModelIndex, int, int], None]
        ] = None,
        after_remove_children: Optional[Callable[[], None]] = None,
    ) -> None:
        self._children_fetched = False
        children_count = self.child_count()
        if children_count == 0:
            return

        if before_remove_children is not None:
            index = QModelIndex(self.persistent_index(0))
            before_remove_children(index, 0, children_count - 1)

        for child in self._children:
            self.item_removed.emit(child)

        self._children.clear()

        if after_remove_children is not None:
            after_remove_children()

    def row(self) -> int:
        if self.parent() is None:
            return 0

        return self.parent()._children.index(self)

    def child_count(self) -> int:
        return len(self._children)

    def column_count(self) -> int:
        return len(self._data)

    def data(self, column: int) -> Any:
        return self._data[self._model_column_to_ua_column[column]]

    def set_data(
        self, attribute: ua.AttributeIds, value: Any, *, emit: bool = True
    ) -> None:
        if isinstance(value, ua.LocalizedText):
            value = value.Text

        self._data[attribute] = value

        if emit:
            # Emit signal letting subscribers know what data has changed here
            index = QModelIndex(
                self.persistent_index(self._ua_column_to_model_column[attribute])
            )
            self.data_changed.emit(index, index)

    def __eq__(self, other) -> bool:
        if isinstance(other, OpcTreeItem):
            return self.node == other.node
        return False
