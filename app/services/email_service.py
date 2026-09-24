import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

logger = logging.getLogger(__name__)

ACTIVATION_SALT = "email-activation-salt"

def generate_activation_token(user_id: str, email: str) -> str:
    """Generate a time-limited secure token for email activation."""
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps({"user_id": user_id, "email": email.strip().lower()}, salt=ACTIVATION_SALT)

def verify_activation_token(token: str, max_age: int = 86400) -> dict | None:
    """Validate activation token within the allowed lifetime (default 24 hours)."""
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        data = serializer.loads(token, salt=ACTIVATION_SALT, max_age=max_age)
        return data
    except Exception as e:
        logger.warning(f"Activation token validation failed: {e}")
        return None

def send_activation_email(to_email: str, display_name: str, activation_url: str) -> bool:
    """
    Sends an activation link to the user's email address.
    If SMTP credentials are not configured, logs the activation link safely for development/testing.
    """
    subject = "Activate Your LyricSync Studio Account"
    name = (display_name or "").strip() or to_email.split("@")[0]

    text_body = f"""Hello {name},

Thank you for creating an account with LyricSync Studio!

Please confirm your email address and activate your account by clicking the link below:
{activation_url}

This link is valid for 24 hours. If you did not create this account, you can safely ignore this message.

Best regards,
The LyricSync Studio Team
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; margin: 0; padding: 24px; color: #1E293B; }}
    .card {{ max-width: 540px; margin: 0 auto; background: #FFFFFF; border: 1px solid #E2E8F0; padding: 36px; border-radius: 4px; }}
    .header {{ border-bottom: 2px solid #6b1426; padding-bottom: 16px; margin-bottom: 24px; }}
    .title {{ font-size: 22px; font-weight: 700; color: #6b1426; margin: 0; }}
    .btn {{ display: inline-block; background-color: #10B981; color: #FFFFFF !important; font-weight: 600; text-decoration: none; padding: 12px 28px; border-radius: 4px; margin: 24px 0; font-size: 15px; }}
    .url {{ font-family: monospace; font-size: 12px; color: #64748B; word-break: break-all; background: #F1F5F9; padding: 8px; border-radius: 4px; }}
    .footer {{ margin-top: 32px; font-size: 12px; color: #94A3B8; border-top: 1px solid #E2E8F0; padding-top: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h2 class="title">LyricSync Studio</h2>
    </div>
    <p>Hello <strong>{name}</strong>,</p>
    <p>Thank you for signing up for LyricSync Studio. Please activate your account by clicking the button below:</p>
    <p style="text-align: center;">
      <a href="{activation_url}" class="btn" target="_blank">Activate Account</a>
    </p>
    <p>Or paste this link into your browser:</p>
    <div class="url">{activation_url}</div>
    <p class="footer">This activation link expires in 24 hours. If you did not create this account, no further action is required.</p>
  </div>
</body>
</html>"""

    # Check SMTP configuration
    mail_server = current_app.config.get("MAIL_SERVER")
    mail_port = int(current_app.config.get("MAIL_PORT", 587))
    mail_username = current_app.config.get("MAIL_USERNAME")
    mail_password = current_app.config.get("MAIL_PASSWORD")
    sender = current_app.config.get("MAIL_DEFAULT_SENDER", "noreply@tanuisila.dev")
    use_tls = current_app.config.get("MAIL_USE_TLS", True)
    use_ssl = current_app.config.get("MAIL_USE_SSL", False)

    if not mail_username or not mail_server or mail_server in ("localhost", "127.0.0.1"):
        logger.info(f"Activation email for {to_email} generated (SMTP not configured). Link: {activation_url}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        if use_ssl:
            with smtplib.SMTP_SSL(mail_server, mail_port, timeout=10) as server:
                if mail_username and mail_password:
                    server.login(mail_username, mail_password)
                server.sendmail(sender, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(mail_server, mail_port, timeout=10) as server:
                if use_tls:
                    server.starttls()
                if mail_username and mail_password:
                    server.login(mail_username, mail_password)
                server.sendmail(sender, [to_email], msg.as_string())

        logger.info(f"Activation email sent successfully to {to_email}")
        return True
    except Exception as exc:
        logger.error(f"Failed to send activation email to {to_email}: {exc}")
        logger.info(f"Activation URL fallback: {activation_url}")
        return False
