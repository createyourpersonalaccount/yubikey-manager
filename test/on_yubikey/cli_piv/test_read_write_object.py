import os
import unittest

from cryptography.hazmat.primitives import serialization
from ..framework import cli_test_suite
from ...util import generate_self_signed_certificate
from yubikit.core import Tlv
from yubikit.piv import OBJECT_ID, SLOT
import contextlib
import io


DEFAULT_MANAGEMENT_KEY = "010203040506070801020304050607080102030405060708"


@cli_test_suite
def additional_tests(ykman_cli):
    class ReadWriteObject(unittest.TestCase):
        def setUp(cls):
            ykman_cli("piv", "reset", "-f")
            pass

        @classmethod
        def tearDownClass(cls):
            ykman_cli("piv", "reset", "-f")
            pass

        def test_write_read_preserves_ansi_escapes(self):
            red = b"\x00\x1b[31m"
            blue = b"\x00\x1b[34m"
            reset = b"\x00\x1b[0m"
            data = (
                b"Hello, "
                + red
                + b"red"
                + reset
                + b" and "
                + blue
                + b"blue"
                + reset
                + b" world!"
            )
            ykman_cli(
                "piv",
                "objects",
                "import",
                "-m",
                DEFAULT_MANAGEMENT_KEY,
                "0x5f0001",
                "-",
                input=data,
            )
            output_data = ykman_cli.with_bytes_output(
                "piv", "objects", "export", "0x5f0001", "-"
            )
            self.assertEqual(data, output_data)

        def test_read_write_read_is_noop(self):
            data = os.urandom(32)

            ykman_cli(
                "piv",
                "objects",
                "import",
                hex(OBJECT_ID.AUTHENTICATION),
                "-",
                "-m",
                DEFAULT_MANAGEMENT_KEY,
                input=data,
            )

            output1 = ykman_cli.with_bytes_output(
                "piv", "objects", "export", hex(OBJECT_ID.AUTHENTICATION), "-"
            )
            self.assertEqual(output1, data)

            ykman_cli(
                "piv",
                "objects",
                "import",
                hex(OBJECT_ID.AUTHENTICATION),
                "-",
                "-m",
                DEFAULT_MANAGEMENT_KEY,
                input=output1,
            )

            output2 = ykman_cli.with_bytes_output(
                "piv", "objects", "export", hex(OBJECT_ID.AUTHENTICATION), "-"
            )
            self.assertEqual(output2, data)

        def test_read_write_aliases(self):
            data = os.urandom(32)

            with io.StringIO() as buf:
                with contextlib.redirect_stderr(buf):
                    ykman_cli(
                        "piv",
                        "write-object",
                        hex(OBJECT_ID.AUTHENTICATION),
                        "-",
                        "-m",
                        DEFAULT_MANAGEMENT_KEY,
                        input=data,
                    )

                    output1 = ykman_cli.with_bytes_output(
                        "piv", "read-object", hex(OBJECT_ID.AUTHENTICATION), "-"
                    )
                err = buf.getvalue()
            self.assertEqual(output1, data)
            self.assertIn("piv objects import", err)
            self.assertIn("piv objects export", err)

        def test_read_write_certificate_as_object(self):
            with self.assertRaises(SystemExit):
                ykman_cli(
                    "piv", "objects", "export", hex(OBJECT_ID.AUTHENTICATION), "-"
                )

            cert = generate_self_signed_certificate()
            cert_bytes_der = cert.public_bytes(encoding=serialization.Encoding.DER)

            input_tlv = Tlv(0x70, cert_bytes_der) + Tlv(0x71, b"\0") + Tlv(0xFE, b"")

            ykman_cli(
                "piv",
                "objects",
                "import",
                hex(OBJECT_ID.AUTHENTICATION),
                "-",
                "-m",
                DEFAULT_MANAGEMENT_KEY,
                input=input_tlv,
            )

            output1 = ykman_cli.with_bytes_output(
                "piv", "objects", "export", hex(OBJECT_ID.AUTHENTICATION), "-"
            )
            output_cert_bytes = Tlv.parse_dict(output1)[0x70]
            self.assertEqual(output_cert_bytes, cert_bytes_der)

            output2 = ykman_cli.with_bytes_output(
                "piv",
                "certificates",
                "export",
                hex(SLOT.AUTHENTICATION),
                "-",
                "--format",
                "DER",
            )
            self.assertEqual(output2, cert_bytes_der)

    return [ReadWriteObject]
