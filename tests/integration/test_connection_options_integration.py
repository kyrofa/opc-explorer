import pytest
from asyncua.sync import Server
from uaclient.mainwindow import Window

# def test_connect_options_button(qtbot, client):
#     client.ui.connectOptionButton.click()
#     assert True
#     # assert client.ui.connection_dialog

def test_connect(qtbot, server, client):
    for ree in client._address_list:
        print(client._address_list)
    # assert client._address_list[0] == 'ree'
