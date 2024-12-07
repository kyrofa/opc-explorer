import pytest
from uaclient.connection_dialog import ConnectionDialog
from unittest.mock import patch, Mock
from PyQt5.QtWidgets import QFileDialog


@pytest.fixture
def uaclient():
    uaclient = Mock()
    yield uaclient


@pytest.fixture
def parent(uaclient):
    parent = Mock()
    parent.uaclient = uaclient
    yield parent


def test_get_certificate(qtbot, parent, uaclient, url):
    cd = ConnectionDialog(parent, url)
    qtbot.addWidget = cd
    with patch.object(
        QFileDialog, "getOpenFileName", return_value=("/test/path", True)
    ) as dialog:
        cd.get_certificate()
        dialog.assert_called_once_with(
            cd, "Select certificate", "None", "Certificate (*.der)"
        )
        assert cd.ui.certificateLabel.text() == "/test/path"


def test_get_private_key(qtbot, parent, uaclient, url):
    cd = ConnectionDialog(parent, url)
    qtbot.addWidget = cd
    with patch.object(
        QFileDialog, "getOpenFileName", return_value=("/test/path", True)
    ) as dialog:
        cd.get_private_key()
        dialog.assert_called_once_with(
            cd, "Select private key", "None", "Private key (*.pem)"
        )
        assert cd.ui.privateKeyLabel.text() == "/test/path"
