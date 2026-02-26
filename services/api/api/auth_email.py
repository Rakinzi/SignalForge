"""SMTP email delivery and branded auth templates for SignalForge."""

import os
import smtplib
from email.message import EmailMessage
from html import escape

SITE_BG = "#f4f4f0"
CARD_BG = "#fdfcf7"
BORDER = "#d7d2c4"
TEXT = "#1f2937"
TEXT_MUTED = "#4b5563"
ACCENT = "#0f766e"


class EmailService:
    def __init__(self) -> None:
        self.host = os.getenv("SMTP_HOST", "").strip()
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.secure = os.getenv("SMTP_SECURE", "false").lower() == "true"
        self.user = os.getenv("SMTP_USER", "").strip()
        self.password = os.getenv("SMTP_PASS", "")
        self.from_email = os.getenv("SMTP_FROM_EMAIL", self.user or "no-reply@signalforge.local")

    @property
    def configured(self) -> bool:
        return bool(self.host and self.user and self.password)

    def send_email(self, to_email: str, subject: str, html_body: str, text_body: str) -> tuple[bool, str]:
        if not self.configured:
            return False, "smtp_not_configured"

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to_email
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")

        try:
            if self.secure:
                with smtplib.SMTP_SSL(self.host, self.port, timeout=20) as smtp:
                    smtp.login(self.user, self.password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=20) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.ehlo()
                    smtp.login(self.user, self.password)
                    smtp.send_message(msg)
            return True, "sent"
        except Exception as exc:  # pragma: no cover - network dependent
            return False, str(exc)


def _wrap_email(title: str, intro: str, action_text: str, action_url: str, outro: str) -> str:
    safe_title = escape(title)
    safe_intro = escape(intro)
    safe_action_text = escape(action_text)
    safe_action_url = escape(action_url, quote=True)
    safe_outro = escape(outro)

    return f"""
<!doctype html>
<html>
  <body style=\"margin:0;padding:0;background:{SITE_BG};font-family:Arial,Helvetica,sans-serif;color:{TEXT};\">
    <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"padding:24px 0;\">
      <tr>
        <td align=\"center\">
          <table role=\"presentation\" width=\"620\" cellspacing=\"0\" cellpadding=\"0\" style=\"max-width:620px;background:{CARD_BG};border:1px solid {BORDER};border-radius:12px;overflow:hidden;\">
            <tr>
              <td style=\"padding:24px 28px;background:{ACCENT};color:#ffffff;\">
                <div style=\"font-size:22px;font-weight:700;\">SignalForge</div>
                <div style=\"font-size:13px;opacity:0.9;\">Network Detection Platform</div>
              </td>
            </tr>
            <tr>
              <td style=\"padding:28px;\">
                <h1 style=\"margin:0 0 14px 0;font-size:22px;line-height:1.3;color:{TEXT};\">{safe_title}</h1>
                <p style=\"margin:0 0 20px 0;font-size:15px;line-height:1.6;color:{TEXT_MUTED};\">{safe_intro}</p>
                <table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" style=\"margin:0 0 20px 0;\"><tr><td>
                  <a href=\"{safe_action_url}\" style=\"display:inline-block;padding:12px 18px;border-radius:8px;background:{ACCENT};color:#ffffff;text-decoration:none;font-weight:600;font-size:14px;\">{safe_action_text}</a>
                </td></tr></table>
                <p style=\"margin:0;font-size:13px;line-height:1.6;color:{TEXT_MUTED};\">{safe_outro}</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
""".strip()


def build_verification_email(username: str, verify_url: str) -> tuple[str, str]:
    subject = "Verify your SignalForge account"
    html = _wrap_email(
        title=f"Welcome, {username}",
        intro="Please confirm your email address to activate account verification and secure auth workflows.",
        action_text="Verify Email",
        action_url=verify_url,
        outro="If you did not sign up for SignalForge, you can safely ignore this email.",
    )
    text = (
        f"Welcome, {username}\n\n"
        f"Verify your SignalForge email by opening this link:\n{verify_url}\n\n"
        "If you did not sign up, ignore this message."
    )
    return subject, html, text


def build_reset_email(username: str, reset_url: str) -> tuple[str, str]:
    subject = "Reset your SignalForge password"
    html = _wrap_email(
        title="Password reset requested",
        intro=f"Hi {username}, we received a request to reset your password.",
        action_text="Reset Password",
        action_url=reset_url,
        outro="This link expires in 30 minutes. If you did not request this, ignore this email.",
    )
    text = (
        f"Hi {username},\n\n"
        f"Reset your SignalForge password using this link:\n{reset_url}\n\n"
        "This link expires in 30 minutes. If you did not request this, ignore this message."
    )
    return subject, html, text
