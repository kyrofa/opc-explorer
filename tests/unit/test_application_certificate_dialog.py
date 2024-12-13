import pytest
from uaclient.application_certificate_dialog import ApplicationCertificateDialog
from unittest.mock import patch, Mock
from PyQt5.QtWidgets import QFileDialog


@pytest.fixture
def uaclient():
    uaclient = Mock()
    uaclient.application_certificate_path = "parent/certificate/path"
    uaclient.application_private_key_path = "parent/private/key/path"
    yield uaclient


@pytest.fixture
def parent(uaclient):
    parent = Mock()
    parent.uaclient = uaclient
    yield parent


def test_certificate_path(qtbot, uaclient, parent):
    acd = ApplicationCertificateDialog(parent)
    assert acd.ui.certificateLabel.text() == "parent/certificate/path"
    assert acd.certificate_path == "parent/certificate/path"
    acd.certificate_path = "None"
    assert not acd.certificate_path
    qtbot.addWidget = acd
    acd.certificate_path = "test/path"
    assert acd.ui.certificateLabel.text() == "test/path"


def test_private_key_path(qtbot, uaclient, parent):
    acd = ApplicationCertificateDialog(parent)
    assert acd.ui.privateKeyLabel.text() == "parent/private/key/path"
    assert acd.private_key_path == "parent/private/key/path"
    acd.private_key_path = "None"
    assert not acd.private_key_path
    qtbot.addWidget = acd
    acd.private_key_path = "test/path"
    assert acd.ui.privateKeyLabel.text() == "test/path"


def test_get_certificate(parent, uaclient):
    acd = ApplicationCertificateDialog(parent)
    with patch.object(
        QFileDialog, "getOpenFileName", return_value=("/test/path", True)
    ) as dialog:
        acd.get_certificate()
        dialog.assert_called_once_with(
            acd,
            "Select application certificate",
            uaclient.application_certificate_path,
            "Certificate (*.der)",
        )
        assert acd.ui.certificateLabel.text() == "/test/path"


def test_get_private_key(parent, uaclient):
    acd = ApplicationCertificateDialog(parent)
    with patch.object(
        QFileDialog, "getOpenFileName", return_value=("/test/path", True)
    ) as dialog:
        acd.get_private_key()
        dialog.assert_called_once_with(
            acd,
            "Select application private key",
            uaclient.application_private_key_path,
            "Private key (*.pem)",
        )
        assert acd.ui.privateKeyLabel.text() == "/test/path"
