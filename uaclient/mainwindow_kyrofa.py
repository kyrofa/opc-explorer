#! /usr/bin/env python3

import sys
import asyncio
from datetime import datetime
from typing import Any
import contextlib
import collections
import functools

from qasync import QEventLoop, QApplication, asyncClose, asyncSlot
from PyQt5.QtCore import QCoreApplication, QSettings, pyqtSignal, QObject
from PyQt5.QtGui import QStandardItemModel, QIcon
from PyQt5.QtWidgets import QMainWindow, QWidget, QAbstractItemView

from asyncua import Client, Node
from asyncua.common.subscription import DataChangeNotif
from asyncua.ua import AttributeIds
import asyncua.ua.uaerrors

# must be here for resources even if not used
from uawidgets import resources  # noqa: F401

from uaclient.mainwindow_ui import Ui_MainWindow
from uaclient import tree_ui
from uaclient.graph_ui import GraphWidget

_SubscriptionData = collections.namedtuple("_SubscriptionData", ["handle", "signal"])


class _SubscriptionSignal(QObject):
    signal = pyqtSignal(object, str)


class _DataChangeHandler:
    def __init__(self, _callback) -> None:
        self._callback = _callback

    async def datachange_notification(
        self, node: Node, value: Any, data: DataChangeNotif
    ):
        if data.monitored_item.Value.SourceTimestamp:
            timestamp = data.monitored_item.Value.SourceTimestamp.isoformat()
        elif data.monitored_item.Value.ServerTimestamp:
            timestamp = data.monitored_item.Value.ServerTimestamp.isoformat()
        else:
            timestamp = datetime.now().isoformat()

        await self._callback(node, value, timestamp)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self._setup_settings()
        self._setup_ui()

        self._uaclient = None
        self._ua_subscription = None
        self._ua_subscription_data = dict()

    @asyncClose
    async def closeEvent(self, event):
        self._save_state()
        await self._disconnect()
        event.accept()

    def _setup_settings(self):
        # setup QSettings for application and get a settings object
        QCoreApplication.setOrganizationName("FreeOpcUa")
        QCoreApplication.setApplicationName("OpcUaClient")
        self._settings = QSettings()

    def _setup_ui(self):
        self._ui = Ui_MainWindow()
        self._ui.setupUi(self)
        self.setWindowIcon(QIcon(":/network.svg"))

        # we only show statusbar in case of errors
        self._ui.statusBar.hide()

        self._setup_ui_tree()
        self._setup_ui_graph()
        self._setup_ui_dock()
        self._setup_ui_addr_combo_box()
        self._setup_ui_connect_disconnect()

    def _setup_ui_tree(self):
        self._model = tree_ui.OpcTreeModel(
            [AttributeIds.DisplayName, AttributeIds.Value]
        )
        self._model.item_added.connect(self._subscribe_to_node)
        self._model.item_removed.connect(self._unsubscribe_from_node)

        self._ui.treeView.setModel(self._model)
        self._ui.treeView.expanded.connect(self._model.handle_expanded)
        self._ui.treeView.collapsed.connect(self._model.handle_collapsed)
        self._ui.treeView.header().setSectionResizeMode(0)
        self._ui.treeView.header().setStretchLastSection(True)
        self._ui.treeView.setSelectionBehavior(QAbstractItemView.SelectRows)

        # populate contextual menu
        self._ui.treeView.addAction(self._ui.actionAddToGraph)
        self._ui.treeView.addAction(self._ui.actionRemoveFromGraph)

    def _setup_ui_graph(self):
        self._graph_ui = GraphWidget(self)
        self._ui.graphLayout.addWidget(self._graph_ui)

        self._ui.actionAddToGraph.triggered.connect(self._handle_add_to_graph)
        self._ui.actionRemoveFromGraph.triggered.connect(self._handle_remove_from_graph)

    def _setup_ui_dock(self):
        # fix stuff imposible to do in qtdesigner
        # remove dock titlebar for addressbar
        w = QWidget()
        self._ui.addrDockWidget.setTitleBarWidget(w)
        # tabify some docks
        self.tabifyDockWidget(self._ui.evDockWidget, self._ui.refDockWidget)
        self.tabifyDockWidget(self._ui.refDockWidget, self._ui.graphDockWidget)

    def _setup_ui_addr_combo_box(self):
        # Add previously-used addresses to the combo box
        for addr in self._settings.value("address_list"):
            self._ui.addrComboBox.insertItem(100, addr)

    def _setup_ui_connect_disconnect(self):
        self._ui.connectButton.clicked.connect(self._connect)
        self._ui.actionConnect.triggered.connect(self._connect)

        self._ui.disconnectButton.clicked.connect(self._disconnect)
        self._ui.actionDisconnect.triggered.connect(self._disconnect)

    def _save_state(self):
        self._settings.setValue("main_window_width", self.size().width())
        self._settings.setValue("main_window_height", self.size().height())
        self._settings.setValue("main_window_state", self.saveState())

    async def _handle_subscription_data(
        self, node: Node, value: Any, timestamp: str
    ) -> None:
        subscription_data = self._ua_subscription_data[node.nodeid]
        subscription_data.signal.signal.emit(value, timestamp)

    @asyncSlot()
    async def _handle_add_to_graph(self):
        index = self._ui.treeView.currentIndex()
        item = index.internalPointer()
        await self._graph_ui.add_node(item.node)

    @asyncSlot()
    async def _handle_remove_from_graph(self):
        index = self._ui.treeView.currentIndex()
        item = index.internalPointer()
        await self._graph_ui.remove_node(item.node)

    @asyncSlot(tree_ui.OpcTreeItem)
    async def _subscribe_to_node(self, item: tree_ui.OpcTreeItem):
        with contextlib.suppress(
            asyncua.ua.uaerrors.BadAttributeIdInvalid,
            asyncua.ua.uaerrors.BadTooManyMonitoredItems,
        ):
            subscription_data = _SubscriptionData(
                await self._ua_subscription.subscribe_data_change(item.node),
                _SubscriptionSignal(self),
            )
            self._ua_subscription_data[item.node.nodeid] = subscription_data
            subscription_data.signal.signal.connect(
                functools.partial(item.set_data, AttributeIds.Value)
            )

    @asyncSlot(tree_ui.OpcTreeItem)
    async def _unsubscribe_from_node(self, item: tree_ui.OpcTreeItem):
        try:
            subscription_data = self._ua_subscription_data.pop(item.node.nodeid)
        except KeyError:
            return

        await self._ua_subscription.unsubscribe(subscription_data.handle)

    @asyncSlot()
    async def _connect(self):
        uri = self._ui.addrComboBox.currentText()
        uri = uri.strip()
        self._uaclient = Client(url=uri)
        try:
            await self._uaclient.connect()
        except Exception as ex:
            self.show_error(ex)
            raise

        self._save_new_uri(uri)
        await self._model.set_root_node(self._uaclient.nodes.root)
        self._ui.treeView.setFocus()

        self._ua_subscription = await self._uaclient.create_subscription(
            500, _DataChangeHandler(self._handle_subscription_data)
        )

    @asyncSlot()
    async def _disconnect(self):
        try:
            if self._uaclient is not None and self._uaclient.uaclient.protocol:
                await self._uaclient.disconnect()
        except Exception as ex:
            self.show_error(ex)
            raise
        finally:
            self._uaclient = None
            self._ua_subscription = None
            self._ua_subscription_data = dict()
            # self.save_current_node()
            # self.tree_ui.clear()
            # self.refs_ui.clear()
            # self.attrs_ui.clear()
            # self.event_ui.clear()

    def _save_new_uri(self, uri):
        address_list = self._settings.value("address_list")
        address_list.remove(uri)
        address_list.insert(0, uri)
        if len(address_list) > self._settings.value("address_list_max_count", 10):
            address_list.pop(-1)
        self._settings.setValue("address_list", address_list)


def main():
    app = QApplication(sys.argv)

    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)

    app_close_event = asyncio.Event()
    app.aboutToQuit.connect(app_close_event.set)

    client = Window()
    client.show()

    with event_loop:
        event_loop.run_until_complete(app_close_event.wait())

    return 0


if __name__ == "__main__":
    main()
