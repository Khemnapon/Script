import requests
from datetime import datetime, timezone
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sys
import os

# ------------------ CONFIGURATION ------------------
GITLAB_URL = "https://gitlab-ce.arv.co.th"  # Replace with your GitLab URL
PRIVATE_TOKEN = os.getenv("GITLAB_PRIVATE_TOKEN")  # Replace with your GitLab private token
REPORT_FILE = "gitlab_token_expiration_report.html"  # Report file name

SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587
SMTP_USER = "arv.gitlab-noreply@arv.co.th"  # Your email address
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")  # Set your SMTP password or app password (for 2FA)

RECEIVER_EMAIL = "arv-solar@arv.co.th"
EXPIRY_THRESHOLD_DAYS = 30  # Number of days before expiry to flag a token
# ---------------------------------------------------

def fetch_tokens():
    """Fetch all personal access tokens from GitLab."""
    headers = {"PRIVATE-TOKEN": PRIVATE_TOKEN}
    url = f"{GITLAB_URL}/api/v4/personal_access_tokens"
    
    response = requests.get(url, headers=headers)

    if response.status_code == 404:
        print("❌ Error: 404 Not Found – Check API URL or token permissions.")
        sys.exit(1)
    elif response.status_code != 200:
        print(f"❌ Error: {response.status_code} – {response.text}")
        sys.exit(1)

    return response.json()

def log(message):
    """Append message to the report file."""
    with open(REPORT_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def check_token_expiration(tokens):
    """Check each token's expiration and print the status."""
    # Get the current time in UTC as a timezone-aware object
    now = datetime.now(timezone.utc)    

    log(f"<h2>GitLab Token Expiry Check (Current time: {now})</h2>")
    log("<hr>")

    # print(f"GitLab Token Expiry Check (Current time: {now})")
    # print("=" * 50)

    for token in tokens:
        token_id = token['id']
        token_name = token['name']
        token_created_at = token['created_at']
        token_expires_at = token['expires_at']

        if token_expires_at:
            # Try to parse the expiration date with two different formats
            try:
                # Attempt to parse with the full datetime format (with time and microseconds)
                expiration_date = datetime.strptime(token_expires_at, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                # If it fails, parse with the simplified date format (only the date)
                expiration_date = datetime.strptime(token_expires_at, "%Y-%m-%d")
            
            expiration_date = expiration_date.replace(tzinfo=timezone.utc)  # Make it timezone-aware

            days_remaining = (expiration_date - now).days

            if days_remaining < 0:
                status = f"Expired ({-days_remaining} days ago)"
            elif days_remaining <= EXPIRY_THRESHOLD_DAYS:
                status = f"⚠️ Will expire in {days_remaining} days"
            else:
                status = f"Active ({days_remaining} days left)"
        else:
            status = "Active (No expiration date)"

            # Log HTML formatted message to file
        log(
            f"<b>Token ID:</b> {token_id}<br>"
            f"<b>Token Name:</b> {token_name}<br>"
            f"<b>Created At:</b> {token_created_at}<br>"
            f"<b>Expires At:</b> {token_expires_at or 'N/A'}<br>"
            f"<b>Status:</b> {status}<br><br>"
            f"<b>--------------------------------------------------------<br>"
        )

        print(f"Token ID: {token_id}, Name: {token_name}, Status: {status}")
        print("-" * 50)

def send_email():
    """Send email with the HTML body containing the token status report."""
    # Read the HTML report content
    with open(REPORT_FILE, 'r', encoding='utf-8') as f:
        html_content = f.read()

    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = "GitLab Token Expiry Report"

    msg.attach(MIMEText(html_content, 'html'))

    try:
        # Set up the SMTP connection and send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, RECEIVER_EMAIL, msg.as_string())
            print(f"✅ Email sent to {RECEIVER_EMAIL}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def main():
    print("🔍 Fetching GitLab personal access tokens...")
    tokens = fetch_tokens()

    # Clear previous report
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        pass

    check_token_expiration(tokens)
    print(f"\n✅ Token expiration check complete. Report saved to {REPORT_FILE}")

    # check_token_expiration(tokens)
    # print("\n✅ Token expiration check complete.")

    send_email()  # Send the email with the report

if __name__ == "__main__":
    main()
