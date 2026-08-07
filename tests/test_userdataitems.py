"""Unit tests for :mod:`pynetdicom2.userdataitems`."""
from io import BytesIO
import unittest

from pynetdicom2 import userdataitems


class UserIdentityReprTestCase(unittest.TestCase):
    """``repr`` must never leak credentials into logs or tracebacks."""

    def test_repr_masks_password(self) -> None:
        item = userdataitems.UserIdentityNegotiationSubItem(
            'user', 'hunter2', user_identity_type=2
        )
        text = repr(item)
        self.assertIn('user', text)
        self.assertNotIn('hunter2', text)
        self.assertIn('secondary_field="<hidden>"', text)

    def test_repr_masks_kerberos_ticket(self) -> None:
        item = userdataitems.UserIdentityNegotiationSubItem(
            'secret-ticket', user_identity_type=3
        )
        text = repr(item)
        self.assertNotIn('secret-ticket', text)
        self.assertIn('primary_field="<hidden>"', text)

    def test_repr_masks_saml_assertion(self) -> None:
        item = userdataitems.UserIdentityNegotiationSubItem(
            'saml-assertion', user_identity_type=4
        )
        self.assertNotIn('saml-assertion', repr(item))

    def test_repr_shows_username_only(self) -> None:
        item = userdataitems.UserIdentityNegotiationSubItem(
            'user', user_identity_type=1
        )
        text = repr(item)
        self.assertIn('primary_field="user"', text)
        self.assertIn('secondary_field=""', text)


class UserIdentityBinaryTestCase(unittest.TestCase):
    """Kerberos, SAML and JWT credentials are opaque binary data and must
    survive encoding/decoding without being forced through UTF-8."""

    def test_binary_primary_field_roundtrip(self) -> None:
        ticket = b'\x00\x01\xff\xfe\x80'  # not valid UTF-8
        item = userdataitems.UserIdentityNegotiationSubItem(
            ticket, user_identity_type=3
        )
        decoded = userdataitems.UserIdentityNegotiationSubItem.decode(
            BytesIO(item.encode())
        )
        self.assertEqual(decoded.primary_field, ticket)
        self.assertIsInstance(decoded.primary_field, bytes)

    def test_text_primary_field_stays_str(self) -> None:
        item = userdataitems.UserIdentityNegotiationSubItem(
            'user', user_identity_type=1
        )
        self.assertEqual(item.primary_field, 'user')
        self.assertIsInstance(item.primary_field, str)

    def test_binary_server_response_roundtrip(self) -> None:
        response = b'\x80\x81\xfe\xff'  # not valid UTF-8
        item = userdataitems.UserIdentityNegotiationSubItemAc(response)
        decoded = userdataitems.UserIdentityNegotiationSubItemAc.decode(
            BytesIO(item.encode())
        )
        self.assertEqual(decoded.server_response, response)
        self.assertIsInstance(decoded.server_response, bytes)

    def test_repr_masks_binary_server_response(self) -> None:
        item = userdataitems.UserIdentityNegotiationSubItemAc(b'\xfe\xff\x00')
        self.assertIn('server_response="<hidden>"', repr(item))


if __name__ == '__main__':
    unittest.main()
