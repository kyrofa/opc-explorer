import pytest
from asyncua.sync import Server


def test_restart_timer(client):
    client.ui.spinBoxNumberOfPoints.setValue(90)
    client.ui.buttonApply.click()
    assert client.graph_ui.N == 90
