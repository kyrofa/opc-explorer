#! /usr/bin/env python3

import logging

from qasync import asyncSlot
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QWidget, QLabel
from typing import List, Optional

from asyncua import ua, Node

from uawidgets.utils import trycatchslot

from ._graph_ui import Ui_Graph

logger = logging.getLogger(__name__)


_use_graph = True
try:
    import pyqtgraph as pg
    import numpy as np
    import numpy.typing as npt
except ImportError:
    print("pyqtgraph or numpy are not installed, use of graph feature disabled")
    _use_graph = False

if _use_graph:
    pg.setConfigOptions(antialias=True)
    pg.setConfigOption("background", "w")
    pg.setConfigOption("foreground", "k")


class _GraphWidgetBase(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        pass


class _GraphWidget(QWidget):

    # use tango color schema (public domain)
    colorCycle = [
        "#4e9a06ff",
        "#ce5c00ff",
        "#3465a4ff",
        "#75507bff",
        "#cc0000ff",
        "#edd400ff",
    ]
    acceptedDatatypes = ["Decimal128", "Double", "Float", "Integer", "UInteger"]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._setup_ui()

        self._node_list: List[Node] = []  # holds the nodes to poll
        self._channels: List[npt.NDArray[np.float64]] = []  # holds the actual data
        self._curves: List[pg.PlotDataItem] = []  # holds the curve objects

        self._restartTimer()

    def _setup_ui(self) -> None:
        self._ui = Ui_Graph()
        self._ui.setupUi(self)

        self.pw = pg.PlotWidget(name="Plot1")
        self.pw.showGrid(x=True, y=True, alpha=0.3)
        self.legend = self.pw.addLegend()
        self._ui.graphLayout.addWidget(self.pw)

        # connect Apply button
        self._ui.buttonApply.clicked.connect(self._restartTimer)

    def _restartTimer(self):
        # stop current timer, if it exists
        if hasattr(self, "_timer") and self._timer.isActive():
            self._timer.stop()

        # define the number of polls displayed in graph
        self.N = self._ui.spinBoxNumberOfPoints.value()
        self.ts = np.arange(self.N)
        # define the poll intervall
        self.intervall = self._ui.spinBoxIntervall.value() * 1000

        # overwrite current channel buffers with zeros of current length and add to curves again
        for i, channel in enumerate(self._channels):
            self._channels[i] = np.zeros(self.N)
            self._curves[i].setData(self._channels[i])

        # starting new timer
        self._timer = QTimer(self)
        self._timer.setInterval(self.intervall)
        self._timer.timeout.connect(self._pushtoGraph)
        self._timer.start()

    @asyncSlot()
    @trycatchslot
    async def add_node(self, node: Node):
        if node not in self._node_list:
            dtype = await node.read_attribute(ua.AttributeIds.DataType)

            dtypeStr = ua.ObjectIdNames[dtype.Value.Value.Identifier]

            value = await node.get_value()

            if dtypeStr in self.acceptedDatatypes and not isinstance(value, list):
                self._node_list.append(node)
                displayName = (await node.read_display_name()).Text
                colorIndex = len(self._node_list) % len(self.colorCycle)
                self._curves.append(
                    self.pw.plot(
                        pen=pg.mkPen(
                            color=self.colorCycle[colorIndex],
                            width=3,
                        ),
                        name=displayName,
                    )
                )
                # set initial data to zero
                self._channels.append(np.zeros(self.N))  # init data sequence with zeros
                # add the new channel data to the new curve
                self._curves[-1].setData(self._channels[-1])
                logger.info("Variable %s added to graph", displayName)

            else:
                logger.info(
                    "Variable cannot be added to graph because it is of type %s or an array",
                    dtypeStr,
                )

    @asyncSlot()
    @trycatchslot
    async def remove_node(self, node: Node):
        if node in self._node_list:
            idx = self._node_list.index(node)
            self._node_list.pop(idx)
            displayName = (await node.read_display_name()).Text
            self.legend.removeItem(displayName)
            self.pw.removeItem(self._curves[idx])
            self._curves.pop(idx)
            self._channels.pop(idx)

    @asyncSlot()
    async def _pushtoGraph(self):
        # ringbuffer: shift and replace last
        for i, node in enumerate(self._node_list):
            self._channels[i] = np.roll(
                self._channels[i], -1
            )  # shift elements to the left by one
            value = await node.get_value()
            self._channels[i][-1] = float(value)
            self._curves[i].setData(self.ts, self._channels[i])


class _GraphWidgetUnsupported(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._ui = Ui_Graph()
        self._ui.setupUi(self)
        self._ui.graphLayout.addWidget(QLabel("pyqtgraph or numpy not installed"))


if _use_graph:
    GraphWidget = _GraphWidget
else:
    GraphWidget = _GraphWidgetUnsupported
