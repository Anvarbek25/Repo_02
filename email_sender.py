"""
email_sender.py
Sends customer enquiry notification emails via Gmail SMTP.

Called synchronously from POST /api/enquiries.
If this fails, the endpoint returns HTTP 500 and no log record is stored.

Gmail setup:
  1. Enable 2-Step Verification on the sending Gmail account.
  2. Go to myaccount.google.com → Security → App Passwords.
  3. Create an App Password for "Mail".
  4. Set GMAIL_APP_PASSWORD in your .env or Render environment variables.
     (This is NOT your Gmail login password — it's the 16-char app password.)
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

GMAIL_ADDRESS     = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
NOTIFY_EMAIL      = os.getenv("NOTIFY_EMAIL")


def send_enquiry_email(name: str, phone: str, email: str, message: str) -> bool:
    """
    Composes and sends an enquiry notification email to the business owner.

    Args:
        name:    Customer's full name
        phone:   Customer's phone number
        email:   Customer's email address
        message: Customer's enquiry message

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"New Enquiry from {name} — Bahafix Website"
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = NOTIFY_EMAIL

        # ── Plain text version ────────────────────────────────────────────
        plain = f"""
New customer enquiry received via the Bahafix website.

─────────────────────────────────────
  Name:   {name}
  Phone:  {phone}
  Email:  {email}
─────────────────────────────────────

Message:
{message}

─────────────────────────────────────
Automated notification — Bahafix Website
        """.strip()

        # ── HTML version (renders nicely in Gmail) ────────────────────────
        html = f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">

    <div style="background: #1B3A6B; padding: 24px 28px; border-radius: 6px 6px 0 0;">
      <h2 style="color: #ffffff; margin: 0; font-size: 20px;">New Customer Enquiry</h2>
      <p style="color: #D6E4F0; margin: 6px 0 0 0; font-size: 14px;">
        Received via the Bahafix website
      </p>
    </div>

    <div style="border: 1px solid #ddd; border-top: none; padding: 24px 28px; border-radius: 0 0 6px 6px;">

      <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
        <tr>
          <td style="padding: 10px 14px; background: #f5f5f5; font-weight: bold;
                     width: 90px; border-bottom: 1px solid #e0e0e0;">Name</td>
          <td style="padding: 10px 14px; border-bottom: 1px solid #e0e0e0;">{name}</td>
        </tr>
        <tr>
          <td style="padding: 10px 14px; background: #f5f5f5; font-weight: bold;
                     border-bottom: 1px solid #e0e0e0;">Phone</td>
          <td style="padding: 10px 14px; border-bottom: 1px solid #e0e0e0;">
            <a href="tel:{phone}" style="color: #1B3A6B;">{phone}</a>
          </td>
        </tr>
        <tr>
          <td style="padding: 10px 14px; background: #f5f5f5; font-weight: bold;
                     border-bottom: 1px solid #e0e0e0;">Email</td>
          <td style="padding: 10px 14px; border-bottom: 1px solid #e0e0e0;">
            <a href="mailto:{email}" style="color: #1B3A6B;">{email}</a>
          </td>
        </tr>
      </table>

      <p style="font-weight: bold; margin: 0 0 8px 0;">Message:</p>
      <div style="background: #f9f9f9; padding: 16px; border-left: 4px solid #1B3A6B;
                  border-radius: 0 4px 4px 0; line-height: 1.6;">
        {message}
      </div>

    </div>

    <p style="color: #aaa; font-size: 12px; margin-top: 16px; text-align: center;">
      Automated notification — Bahafix Website
    </p>

  </body>
</html>
        """.strip()

        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        # ── Send via Gmail SMTP with STARTTLS ─────────────────────────────
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, NOTIFY_EMAIL, msg.as_string())

        log.info(f"Enquiry email sent successfully to {NOTIFY_EMAIL}")
        return True

    except Exception as e:
        log.error(f"Failed to send enquiry email: {e}")
        return False
