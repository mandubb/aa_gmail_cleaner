import os
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle

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
# ACTIVITY LOG READER
# -------------------------
def read_activity_log(max_lines=20):
    """
    Returns the most recent `max_lines` entries from the activity log.
    Each entry is returned as a dict: { 'timestamp': str, 'client': str, 'message': str }
    """
    log_path = os.path.join(LOG_DIR, "activity.log")

    if not os.path.exists(log_path):
        return []

    entries = []

    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            # Format: "2026-06-12 10:00:00.123456 | [ClientName] MESSAGE"
            parts = line.split(" | ", 1)
            timestamp = parts[0].strip()
            rest = parts[1].strip()

            # Extract client name from [ClientName]
            client_end = rest.index("]")
            client = rest[1:client_end]
            message = rest[client_end + 2:].strip()

            entries.append({
                "timestamp": timestamp,
                "client": client,
                "message": message
            })
        except Exception:
            # If parsing fails, show raw line
            entries.append({
                "timestamp": "",
                "client": "",
                "message": line
            })

        if len(entries) >= max_lines:
            break

    return entries


# -------------------------
# PDF REPORT GENERATION
# -------------------------
def generate_report(client, gmail, mode, cleaned_count):

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"Report_{timestamp}.pdf"
    filepath = os.path.join(REPORT_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=4,
        fontName="Helvetica-Bold"
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#555555"),
        spaceAfter=16,
        fontName="Helvetica"
    )

    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#888888"),
        spaceAfter=2,
        fontName="Helvetica"
    )

    value_style = ParagraphStyle(
        "Value",
        parent=styles["Normal"],
        fontSize=13,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=12,
        fontName="Helvetica-Bold"
    )

    highlight_style = ParagraphStyle(
        "Highlight",
        parent=styles["Normal"],
        fontSize=28,
        textColor=colors.HexColor("#4f46e5"),
        spaceAfter=4,
        fontName="Helvetica-Bold",
        alignment=1  # Center
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#aaaaaa"),
        alignment=1,
        fontName="Helvetica"
    )

    story = []

    # Header
    story.append(Paragraph("AA's Computer &amp; Remote Services", title_style))
    story.append(Paragraph("Professional Email Cleaner Suite — Cleanup Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0e0")))
    story.append(Spacer(1, 0.4 * cm))

    # Info table
    data = [
        [
            Paragraph("CLIENT", label_style),
            Paragraph("GMAIL ADDRESS", label_style),
        ],
        [
            Paragraph(client or "N/A", value_style),
            Paragraph(gmail or "N/A", value_style),
        ],
        [
            Paragraph("CLEANING MODE", label_style),
            Paragraph("DATE &amp; TIME", label_style),
        ],
        [
            Paragraph(mode, value_style),
            Paragraph(datetime.now().strftime("%B %d, %Y — %H:%M:%S"), value_style),
        ],
    ]

    table = Table(data, colWidths=["50%", "50%"])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))

    story.append(table)
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0e0")))
    story.append(Spacer(1, 0.5 * cm))

    # Big number
    story.append(Paragraph(f"{cleaned_count:,}", highlight_style))
    story.append(Paragraph(
        "emails marked as read",
        ParagraphStyle(
            "Sub",
            parent=styles["Normal"],
            fontSize=11,
            textColor=colors.HexColor("#4f46e5"),
            alignment=1,
            spaceAfter=20,
            fontName="Helvetica"
        )
    ))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e0e0e0")))
    story.append(Spacer(1, 0.4 * cm))

    # Status badge row
    status_data = [[
        Paragraph("STATUS", label_style),
    ], [
        Paragraph("✔ COMPLETED SUCCESSFULLY", ParagraphStyle(
            "Status",
            parent=styles["Normal"],
            fontSize=12,
            textColor=colors.HexColor("#16a34a"),
            fontName="Helvetica-Bold",
            spaceAfter=0
        ))
    ]]
    status_table = Table(status_data, colWidths=["100%"])
    status_table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(status_table)
    story.append(Spacer(1, 2 * cm))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0e0e0")))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "AA's Computer &amp; Remote Services • Generated by AA Email Cleaner Suite V3.1",
        footer_style
    ))

    doc.build(story)

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
# MARK AS READ (with progress callback)
# -------------------------
def mark_as_read(service, ids, progress_callback=None):
    """
    Marks all emails in `ids` as read using batchModify in chunks of 1000.
    Optionally calls `progress_callback(current, total)` after each batch.
    """
    total = len(ids)

    for i in range(0, total, 1000):

        chunk = ids[i:i + 1000]

        service.users().messages().batchModify(
            userId="me",
            body={
                "ids": chunk,
                "removeLabelIds": ["UNREAD"]
            }
        ).execute()

        if progress_callback:
            processed = min(i + 1000, total)
            progress_callback(processed, total)