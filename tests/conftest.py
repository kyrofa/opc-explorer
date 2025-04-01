import pytest
import asyncio

from pytestqt.qtbot import QtBot

from asyncua import Server
from asyncua.sync import Server as SyncServer

from uaclient.mainwindow import Window


@pytest.fixture(scope="module")
def url():
    yield "opc.tcp://localhost:48400/freeopcua/server/"


@pytest.fixture
async def async_server(url):
    server = Server()
    await server.init()
    server.set_endpoint(url)
    await server.start()
    yield server
    await server.stop()


@pytest.fixture(scope="module")
def server(url):
    server = SyncServer()
    server.set_endpoint(url)
    server.start()
    yield server
    server.stop()


@pytest.fixture
def client(qtbot, url):
    client = Window()
    qtbot.addWidget = client
    client.ui.addrComboBox.setCurrentText(url)
    client.connect()
    yield client
    client.disconnect()


@pytest.fixture
def wait_signal():
    async def _signal_waiter(signal, timeout=1000):
        done = asyncio.Event()

        def _quit_loop(*args):
            done.set()

        signal.connect(_quit_loop)

        await asyncio.wait_for(done.wait(), timeout)

    return _signal_waiter
