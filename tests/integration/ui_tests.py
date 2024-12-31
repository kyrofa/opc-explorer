import pytest
from asyncua.sync import Server

@pytest.fixture
def connection_dialog(qtbot,client, url):
    dialog = ConnectionDialog(client,url)
    qtbot.addWidget = dialog
    yield dialog

def test_restart_timer(client):
    client.ui.spinBoxNumberOfPoints.setValue(90)
    client.ui.buttonApply.click()
    assert client.graph_ui.N == 90

def test_close_dialog(connection_dialog):
    connection_dialog.ui.closeButton.click()
    assert connection_dialog.isVisible() == False