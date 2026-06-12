import os
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly"
]

TOKEN_DIR = "tokens"
LOG_DIR = "logs"
REPORT_DIR = "reports"

os.makedirs(TOKEN_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)


# -------------------------
# LOGGING
# -------------------------
def log_action(client, message):
    with open(
        os.path.join(LOG_DIR, "activity.log"),
        "a",
        encoding="utf-8"
    ) as f:
        f.write(f"{datetime.now()} | [{client}] {message}\n")


# -------------------------
# REPORT GENERATION
# -------------------------
def generate_report(client, gmail, mode, cleaned_count):

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    filename = f"Report_{timestamp}.txt"

    filepath = os.path.join(REPORT_DIR, filename)

    content = f"""
AA's Email Cleaner Suite

Client:
{client}

Gmail:
{gmail}

Date:
{datetime.now()}

Mode:
{mode}

Emails Marked Read:
{cleaned_count}

Status:
SUCCESS
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


# -------------------------
# TOKEN FILE
# -------------------------
def get_token_file(client):
    return os.path.join(TOKEN_DIR, f"{client}.json")


# -------------------------
# AUTHENTICATION
# -------------------------
def authenticate(client):

    token_file = get_token_file(client)

    creds = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(
            token_file,
            SCOPES
        )

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# -------------------------
# GET CONNECTED EMAIL
# -------------------------
def get_profile_email(service):

    profile = service.users().getProfile(
        userId="me"
    ).execute()

    return profile.get("emailAddress")


# -------------------------
# QUERIES
# -------------------------
def get_query(mode):

    if mode == "Safe (Recommended)":
        return "is:unread older_than:30d -label:important -is:starred"

    elif mode == "Aggressive (Unlocked)":
        return "is:unread"

    return "is:unread"


# -------------------------
# FETCH IDS
# -------------------------
def get_unread_old_emails(service, mode):

    ids = []

    page_token = None

    query = get_query(mode)

    while True:

        result = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=500,
            pageToken=page_token
        ).execute()

        ids.extend([
            m["id"]
            for m in result.get("messages", [])
        ])

        page_token = result.get("nextPageToken")

        if not page_token:
            break

    return ids


# -------------------------
# COUNT ONLY
# -------------------------
def get_count(service, mode):

    return len(
        get_unread_old_emails(service, mode)
    )


# -------------------------
# MARK AS READ
# -------------------------
def mark_as_read(service, ids):

    for i in range(0, len(ids), 1000):

        chunk = ids[i:i + 1000]

        service.users().messages().batchModify(
            userId="me",
            body={
                "ids": chunk,
                "removeLabelIds": ["UNREAD"]
            }
        ).execute()