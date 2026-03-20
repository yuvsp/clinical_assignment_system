"""
MIME multipart/alternative for Gmail API raw send (stdlib only).
MIMEMultipart + email.header.Header for Subject: reliable RFC 2047 for long
Hebrew strings (EmailMessage+SMTP mishandles pre-encoded multi-chunk Subject).
"""
import json
import time
from pathlib import Path

from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# #region agent log
def _agent_log(hypothesis_id, location, message, data=None, run_id="pre-fix"):
    try:
        p = Path(__file__).resolve().parents[1] / "debug-c3ccbf.log"
        with open(p, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "c3ccbf",
                        "hypothesisId": hypothesis_id,
                        "location": location,
                        "message": message,
                        "data": data or {},
                        "runId": run_id,
                        "timestamp": int(time.time() * 1000),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except OSError:
        pass


# #endregion


def build_multipart_email(subject, to_email, plain_body, html_body, from_email=None):
    message = MIMEMultipart("alternative")
    if from_email:
        message["From"] = from_email
    message["To"] = to_email
    subj = subject if subject is not None else ""
    message["Subject"] = Header(subj, "utf-8")
    # #region agent log
    _agent_log(
        "H2_H4",
        "gmail_mime.build_multipart_email",
        "subject_mime_header",
        {
            "subj_len": len(subj),
            "first_cp": ord(subj[0]) if subj else None,
            "using": "MIMEMultipart+Header",
        },
    )
    # #endregion
    message.attach(MIMEText(plain_body or "", "plain", "utf-8"))
    message.attach(MIMEText(html_body or "", "html", "utf-8"))
    return message
