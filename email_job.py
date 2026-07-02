"""
email_job.py
Background job that runs every 1 minute.
Finds unsent enquiries (sent_at IS NULL) and dispatches email notifications
to the business owner via Gmail SMTP.

This file runs as a separate process alongside the API:
  python email_job.py
"""

import smtplib
import schedule
import time
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from database import get_connection

load_dotenv()

# ─── Config ──────────────────────────────────────────────────────────────────
GMAIL_ADDRESS    = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
NOTIFY_EMAIL     = os.getenv("NOTIFY_EMAIL")

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [EMAIL JOB] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def send_email(enquiry: dict) -> bool:
    """
    Composes and sends an email notification for a single enquiry.
    Returns True on success, False on failure.
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"New Enquiry from {enquiry['name']} — Bahafix Website"
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = NOTIFY_EMAIL

        # Plain text version
        plain_text = f"""
New customer enquiry received via the Bahafix website.

─────────────────────────────────────────
  Name:      {enquiry['name']}
  Phone:     {enquiry['phone']}
  Email:     {enquiry['email']}
  Submitted: {enquiry['submitted_at']}
─────────────────────────────────────────

Message:
{enquiry['message']}

─────────────────────────────────────────
This is an automated notification from the Bahafix website.
        """.strip()

        # HTML version (renders nicely in Gmail)
        html_text = f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
    <div style="background: #1B3A6B; padding: 20px; border-radius: 6px 6px 0 0;">
      <h2 style="color: white; margin: 0;">New Customer Enquiry</h2>
      <p style="color: #D6E4F0; margin: 4px 0 0 0;">Received via the Bahafix website</p>
    </div>
    <div style="border: 1px solid #ddd; border-top: none; padding: 24px; border-radius: 0 0 6px 6px;">
      <table style="width: 100%; border-collapse: collapse;">
        <tr>
          <td style="padding: 8px 12px; background: #f5f5f5; font-weight: bold; width: 120px;">Name</td>
          <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{enquiry['name']}</td>
        </tr>
        <tr>
          <td style="padding: 8px 12px; background: #f5f5f5; font-weight: bold;">Phone</td>
          <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{enquiry['phone']}</td>
        </tr>
        <tr>
          <td style="padding: 8px 12px; background: #f5f5f5; font-weight: bold;">Email</td>
          <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">
            <a href="mailto:{enquiry['email']}">{enquiry['email']}</a>
          </td>
        </tr>
        <tr>
          <td style="padding: 8px 12px; background: #f5f5f5; font-weight: bold;">Submitted</td>
          <td style="padding: 8px 12px; border-bottom: 1px solid #eee;">{enquiry['submitted_at']}</td>
        </tr>
      </table>
      <div style="margin-top: 20px;">
        <p style="font-weight: bold; margin-bottom: 8px;">Message:</p>
        <div style="background: #f9f9f9; padding: 16px; border-left: 4px solid #1B3A6B; border-radius: 4px;">
          {enquiry['message']}
        </div>
      </div>
    </div>
    <p style="color: #aaa; font-size: 12px; margin-top: 16px;">
      Automated notification — Bahafix Website
    </p>
  </body>
</html>
        """.strip()

        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_text, "html"))

        # Send via Gmail SMTP with TLS
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, NOTIFY_EMAIL, msg.as_string())

        return True

    except Exception as e:
        log.error(f"Failed to send email for enquiry ID {enquiry['id']}: {e}")
        return False


def process_pending_enquiries():
    """
    Main job function — called every 1 minute by the scheduler.

    1. Fetches all enquiries where sent_at IS NULL
    2. Attempts to send an email for each one
    3. On success: updates sent_at with current Melbourne timestamp
    4. On failure: leaves sent_at as NULL so it retries next minute
    """
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, name, phone, email, message, submitted_at
            FROM Enquiries
            WHERE sent_at IS NULL
            ORDER BY submitted_at ASC
            """
        )
        pending = cursor.fetchall()

        if not pending:
            return  # Nothing to process

        log.info(f"Found {len(pending)} pending enquiry/enquiries to dispatch")

        for enquiry in pending:
            # Convert datetime to readable string for the email
            if enquiry["submitted_at"]:
                enquiry["submitted_at"] = enquiry["submitted_at"].strftime("%d %b %Y %H:%M %Z")

            success = send_email(enquiry)

            if success:
                cursor.execute(
                    """
                    UPDATE Enquiries
                    SET sent_at = CONVERT_TZ(NOW(), 'UTC', 'Australia/Melbourne')
                    WHERE id = %s
                    """,
                    (enquiry["id"],),
                )
                conn.commit()
                log.info(f"Enquiry ID {enquiry['id']} — email sent and record updated")
            else:
                log.warning(f"Enquiry ID {enquiry['id']} — email failed, will retry next run")

    except Exception as e:
        log.error(f"Unexpected error in job: {e}")
    finally:
        cursor.close()
        conn.close()


# ─── Scheduler ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("Email dispatch job started — running every 1 minute")

    # Run once immediately on startup so we don't wait a full minute
    process_pending_enquiries()

    # Then schedule to run every minute
    schedule.every(1).minutes.do(process_pending_enquiries)

    while True:
        schedule.run_pending()
        time.sleep(10)  # Check every 10 seconds if a scheduled job is due
