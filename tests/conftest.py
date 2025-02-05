import pytest
from asyncua import Server
from uaclient.mainwindow import Window


@pytest.fixture(scope="module")
def url():
    yield "opc.tcp://localhost:48400/freeopcua/server/"


@pytest.fixture(scope="module")
async def server(url):
    server = Server()
    server.set_endpoint(url)
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
def client(qtbot, url, server):
    client = Window()
    qtbot.addWidget = client
    client.ui.addrComboBox.setCurrentText(url)
    client.connect()
    yield client
    client.disconnect()
