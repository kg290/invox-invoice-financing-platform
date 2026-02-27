"""
InvoX Email Service — Gmail API Integration
Sends branded OTP verification emails via Gmail OAuth 2.0.

Adapted for server-side use:
  - Authenticates once at import via token.json (no browser popup)
  - Auto-refreshes expired tokens
  - Graceful fallback to console logging if Gmail is unavailable
"""

import os
import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger("invox.email")

# Gmail send-only scope
_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Resolve paths relative to this file → backend/services/ → backend/
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CREDENTIALS_PATH = os.path.join(_BASE_DIR, "credentials.json")
_TOKEN_PATH = os.path.join(_BASE_DIR, "token.json")


class EmailService:
    """Singleton-style Gmail API wrapper for InvoX."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._service = None
        self._creds = None
        self._ready = False
        self._sender_email = None
        self._authenticate()

    # ── Auth ──────────────────────────────────────────────

    def _authenticate(self):
        """Load token.json, refresh if needed. Never opens a browser."""
        try:
            if not os.path.exists(_TOKEN_PATH):
                logger.warning("token.json not found — email sending disabled")
                return

            self._creds = Credentials.from_authorized_user_file(_TOKEN_PATH, _SCOPES)

            if not self._creds.valid:
                if self._creds.expired and self._creds.refresh_token:
                    self._creds.refresh(Request())
                    # Persist refreshed token
                    with open(_TOKEN_PATH, "w") as f:
                        f.write(self._creds.to_json())
                    logger.info("Gmail token refreshed successfully")
                else:
                    logger.warning("Gmail token invalid and cannot refresh — email disabled")
                    return

            self._service = build("gmail", "v1", credentials=self._creds)
            self._sender_email = "noreply@invox.app"

            # Try to get actual sender address (needs gmail.readonly scope)
            try:
                profile = self._service.users().getProfile(userId="me").execute()
                self._sender_email = profile.get("emailAddress", self._sender_email)
            except Exception:
                pass  # send-only token — use default

            self._ready = True
            logger.info(f"Gmail service ready — sending as {self._sender_email}")

        except Exception as exc:
            logger.error(f"Gmail authentication failed: {exc}")
            self._ready = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    # ── Send helpers ─────────────────────────────────────

    def _send_raw(self, to: str, subject: str, html_body: str, attachment: tuple = None) -> dict | None:
        """Low-level send via Gmail API. Optional attachment=(filename, bytes, mimetype)."""
        if not self._ready:
            logger.warning("Email service not ready — skipping send")
            return None

        msg = MIMEMultipart("mixed")
        msg["to"] = to
        msg["subject"] = subject
        msg["from"] = f"InvoX <{self._sender_email}>"

        # HTML body as alternative part
        html_part = MIMEText(html_body, "html")
        msg.attach(html_part)

        # Optional attachment
        if attachment:
            fname, fbytes, fmimetype = attachment
            att = MIMEApplication(fbytes, _subtype=fmimetype.split("/")[-1] if "/" in fmimetype else "octet-stream")
            att.add_header("Content-Disposition", "attachment", filename=fname)
            msg.attach(att)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        try:
            result = self._service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()
            logger.info(f"Email sent to {to} — Message ID: {result['id']}")
            return result
        except HttpError as err:
            logger.error(f"Gmail API error sending to {to}: {err}")
            return None

    # ── Public API ───────────────────────────────────────

    def send_otp_email(self, to: str, otp: str, user_name: str = "User") -> bool:
        """
        Send a branded OTP verification email.

        Returns True if sent successfully, False otherwise.
        """
        subject = f"🔐 {otp} — Your InvoX Verification Code"

        html = _OTP_TEMPLATE.format(
            user_name=user_name,
            otp=otp,
            year=datetime.now().year,
        )

        result = self._send_raw(to, subject, html)
        return result is not None

    def send_welcome_email(self, to: str, user_name: str = "User") -> bool:
        """Send a welcome email after successful registration."""
        subject = "🎉 Welcome to InvoX — Invoice Financing Made Simple"

        html = _WELCOME_TEMPLATE.format(
            user_name=user_name,
            year=datetime.now().year,
        )

        result = self._send_raw(to, subject, html)
        return result is not None

    def send_invoice_email(
        self,
        to: str,
        invoice_number: str,
        buyer_name: str,
        vendor_name: str,
        grand_total: float,
        due_date: str,
        pdf_bytes: bytes,
    ) -> bool:
        """Send an invoice PDF to the buyer/client via email."""
        subject = f"📄 Invoice {invoice_number} from {vendor_name}"

        html = _INVOICE_EMAIL_TEMPLATE.format(
            buyer_name=buyer_name,
            vendor_name=vendor_name,
            invoice_number=invoice_number,
            grand_total=f"₹{grand_total:,.2f}",
            due_date=due_date,
            year=datetime.now().year,
        )

        attachment = (f"{invoice_number}.pdf", pdf_bytes, "application/pdf")
        result = self._send_raw(to, subject, html, attachment=attachment)
        return result is not None


# ═══════════════════════════════════════════════════
#  HTML Templates
# ═══════════════════════════════════════════════════

_OTP_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:40px 0;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:#fff;font-size:28px;letter-spacing:1px;">InvoX</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:13px;">Invoice Financing Platform</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px 40px;">
            <p style="margin:0 0 8px;font-size:16px;color:#1e293b;">Hello <strong>{user_name}</strong>,</p>
            <p style="margin:0 0 28px;font-size:14px;color:#64748b;line-height:1.6;">
              Use the verification code below to complete your sign-in.
              This code expires in <strong>5 minutes</strong>.
            </p>

            <!-- OTP Box -->
            <div style="text-align:center;margin:0 0 28px;">
              <div style="display:inline-block;background:#f1f5f9;border:2px dashed #6366f1;border-radius:10px;padding:18px 40px;">
                <span style="font-size:36px;font-weight:700;letter-spacing:10px;color:#6366f1;">{otp}</span>
              </div>
            </div>

            <p style="margin:0 0 6px;font-size:13px;color:#94a3b8;">
              If you did not request this code, you can safely ignore this email.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;padding:20px 40px;text-align:center;border-top:1px solid #e2e8f0;">
            <p style="margin:0;font-size:12px;color:#94a3b8;">
              &copy; {year} InvoX &mdash; Built for Hackathon 🚀
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""

_WELCOME_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:40px 0;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:#fff;font-size:28px;letter-spacing:1px;">InvoX</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:13px;">Invoice Financing Platform</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px 40px;">
            <p style="margin:0 0 8px;font-size:20px;color:#1e293b;">Welcome aboard, <strong>{user_name}</strong>! 🎉</p>
            <p style="margin:0 0 20px;font-size:14px;color:#64748b;line-height:1.6;">
              Your InvoX account is verified and ready to go. You can now access
              the full platform — upload invoices, explore the marketplace, and
              manage your financing needs.
            </p>

            <div style="text-align:center;margin:24px 0;">
              <a href="http://localhost:3000/dashboard" style="display:inline-block;background:#6366f1;color:#fff;text-decoration:none;padding:12px 32px;border-radius:8px;font-size:14px;font-weight:600;">
                Go to Dashboard &rarr;
              </a>
            </div>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;padding:20px 40px;text-align:center;border-top:1px solid #e2e8f0;">
            <p style="margin:0;font-size:12px;color:#94a3b8;">
              &copy; {year} InvoX &mdash; Built for Hackathon 🚀
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""

_INVOICE_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:40px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:#fff;font-size:28px;letter-spacing:1px;">InvoX</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:13px;">Invoice Financing Platform</p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px 40px;">
            <p style="margin:0 0 8px;font-size:16px;color:#1e293b;">Hello <strong>{buyer_name}</strong>,</p>
            <p style="margin:0 0 24px;font-size:14px;color:#64748b;line-height:1.6;">
              You have received an invoice from <strong>{vendor_name}</strong>.
              Please find the details below and the PDF attached.
            </p>

            <!-- Invoice Summary Box -->
            <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:20px;margin:0 0 24px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding:6px 0;font-size:13px;color:#64748b;">Invoice Number</td>
                  <td style="padding:6px 0;font-size:13px;color:#1e293b;font-weight:600;text-align:right;">{invoice_number}</td>
                </tr>
                <tr>
                  <td style="padding:6px 0;font-size:13px;color:#64748b;">Amount Due</td>
                  <td style="padding:6px 0;font-size:18px;color:#6366f1;font-weight:700;text-align:right;">{grand_total}</td>
                </tr>
                <tr>
                  <td style="padding:6px 0;font-size:13px;color:#64748b;">Due Date</td>
                  <td style="padding:6px 0;font-size:13px;color:#1e293b;font-weight:600;text-align:right;">{due_date}</td>
                </tr>
              </table>
            </div>

            <p style="margin:0 0 6px;font-size:13px;color:#94a3b8;">
              📎 The detailed invoice is attached as a PDF with this email.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;padding:20px 40px;text-align:center;border-top:1px solid #e2e8f0;">
            <p style="margin:0;font-size:12px;color:#94a3b8;">
              &copy; {year} InvoX &mdash; Invoice Financing Platform 🚀
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
"""


# ── Module-level singleton ───────────────────────
# Import this to use: `from services.email_service import email_service`
email_service = EmailService()
