"""Regression: Hebrew email Subject must be RFC 2047 in raw MIME (Gmail API)."""
import importlib.util
import pathlib
import unittest
from email import policy
from email.parser import BytesParser


def _load_gmail_mime():
    """Load app/gmail_mime.py without importing app package (no Flask)."""
    root = pathlib.Path(__file__).resolve().parents[1]
    path = root / "app" / "gmail_mime.py"
    spec = importlib.util.spec_from_file_location("gmail_mime_standalone", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_multipart_email


class TestGmailMimeSubject(unittest.TestCase):
    def test_hebrew_subject_is_rfc2047_and_round_trips(self):
        build_multipart_email = _load_gmail_mime()
        subject = "שיבוץ שפה ודיבור - נסיון3"
        msg = build_multipart_email(
            subject,
            "student@example.com",
            "שלום",
            "<p>שלום</p>",
            "sender@example.com",
        )
        raw = (
            msg.as_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        )

        subj_lines = [
            line
            for line in raw.split(b"\r\n")
            if line.lower().startswith(b"subject:")
        ]
        self.assertTrue(subj_lines, "expected a Subject header line")
        subj_line = subj_lines[0]
        self.assertIn(
            b"=?utf-8?",
            subj_line,
            "Subject must be RFC 2047 encoded (ASCII-safe), not raw UTF-8 in headers",
        )
        hebrew_leading = b"\xd7\xa9"  # UTF-8 for U+05E9
        after_colon = subj_line.split(b":", 1)[1].strip()
        self.assertNotIn(
            hebrew_leading,
            after_colon,
            "Subject header value must not contain raw UTF-8 Hebrew bytes",
        )

        parsed = BytesParser(policy=policy.default).parsebytes(raw)
        self.assertEqual(parsed["Subject"], subject)

    def test_ascii_subject_unchanged_in_semantics(self):
        build_multipart_email = _load_gmail_mime()
        subject = "Hello - Student"
        msg = build_multipart_email(
            subject, "a@b.com", "x", "<p>x</p>", "f@b.com"
        )
        raw = msg.as_bytes()
        parsed = BytesParser(policy=policy.default).parsebytes(raw)
        self.assertEqual(parsed["Subject"], subject)


if __name__ == "__main__":
    unittest.main()
