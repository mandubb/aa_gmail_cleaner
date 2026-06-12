import os
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, KeepTogether
)
from reportlab.platypus.flowables import Flowable

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

# ── Custom Flowables ──────────────────────────────────────────────────────────

class ColorBand(Flowable):
    """A full-width colored rectangle used as a decorative header band."""
    def __init__(self, width, height, fill_color, radius=6):
        super().__init__()
        self.band_width = width
        self.band_height = height
        self.fill_color = fill_color
        self.radius = radius

    def wrap(self, availWidth, availHeight):
        return self.band_width, self.band_height

    def draw(self):
        self.canv.saveState()
        self.canv.setFillColor(self.fill_color)
        self.canv.roundRect(
            0, 0, self.band_width, self.band_height,
            self.radius, stroke=0, fill=1
        )
        self.canv.restoreState()


class AccentLine(Flowable):
    """A short thick accent bar, used under section headings."""
    def __init__(self, width=40, height=4, color=colors.HexColor("#4f46e5")):
        super().__init__()
        self.bar_width = width
        self.bar_height = height
        self.bar_color = color

    def wrap(self, availWidth, availHeight):
        return self.bar_width, self.bar_height

    def draw(self):
        self.canv.saveState()
        self.canv.setFillColor(self.bar_color)
        self.canv.roundRect(
            0, 0, self.bar_width, self.bar_height,
            2, stroke=0, fill=1
        )
        self.canv.restoreState()


def _on_page(canvas, doc, page_width):
    """Draw a left-side decorative sidebar stripe on every page."""
    canvas.saveState()
    stripe_w = 6
    page_h = A4[1]
    canvas.setFillColor(colors.HexColor("#4f46e5"))
    canvas.rect(0, 0, stripe_w, page_h, stroke=0, fill=1)
    canvas.restoreState()


def generate_report(client, gmail, mode, cleaned_count):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"Report_{timestamp}.pdf"
    filepath = os.path.join(REPORT_DIR, filename)

    PAGE_W, PAGE_H = A4
    L_MARGIN = 2.2 * cm
    R_MARGIN = 2 * cm
    T_MARGIN = 2 * cm
    B_MARGIN = 2 * cm
    CONTENT_W = PAGE_W - L_MARGIN - R_MARGIN

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=R_MARGIN,
        leftMargin=L_MARGIN,
        topMargin=T_MARGIN,
        bottomMargin=B_MARGIN,
    )

    styles = getSampleStyleSheet()

    # ── Palette ────────────────────────────────────────────────────────────────
    INDIGO      = colors.HexColor("#4f46e5")
    INDIGO_DARK = colors.HexColor("#3730a3")
    INDIGO_SOFT = colors.HexColor("#ede9fe")
    SLATE_DARK  = colors.HexColor("#1e1b4b")
    SLATE_MID   = colors.HexColor("#64748b")
    SLATE_LIGHT = colors.HexColor("#f8fafc")
    GREEN_BG    = colors.HexColor("#dcfce7")
    GREEN_TEXT  = colors.HexColor("#15803d")
    BORDER      = colors.HexColor("#e2e8f0")
    WHITE       = colors.white

    # ── Text Styles ────────────────────────────────────────────────────────────
    def S(name, **kw):
        base = kw.pop("parent", styles["Normal"])
        return ParagraphStyle(name, parent=base, **kw)

    hero_title = S("HeroTitle",
        fontName="Helvetica-Bold", fontSize=22,
        textColor=WHITE, spaceAfter=2, leading=26)

    hero_sub = S("HeroSub",
        fontName="Helvetica", fontSize=11,
        textColor=colors.HexColor("#c7d2fe"), spaceAfter=0, leading=16)

    section_heading = S("SectionHeading",
        fontName="Helvetica-Bold", fontSize=10,
        textColor=INDIGO, spaceAfter=6, spaceBefore=4,
        leading=14, tracking=1)

    label_s = S("Label2",
        fontName="Helvetica", fontSize=8,
        textColor=SLATE_MID, spaceAfter=1, leading=11)

    value_s = S("Value2",
        fontName="Helvetica-Bold", fontSize=12,
        textColor=SLATE_DARK, spaceAfter=0, leading=16)

    big_num = S("BigNum",
        fontName="Helvetica-Bold", fontSize=48,
        textColor=INDIGO, alignment=1, spaceAfter=0, leading=52)

    big_sub = S("BigSub",
        fontName="Helvetica", fontSize=13,
        textColor=SLATE_MID, alignment=1, spaceAfter=0, leading=18)

    status_ok = S("StatusOk",
        fontName="Helvetica-Bold", fontSize=12,
        textColor=GREEN_TEXT, spaceAfter=0, leading=16)

    footer_s = S("Footer2",
        fontName="Helvetica", fontSize=8,
        textColor=SLATE_MID, alignment=1, leading=11)

    story = []

    # ── 1. Hero Banner ─────────────────────────────────────────────────────────
    # Build banner content as an inner table so text sits on top of band
    hero_content = Table(
        [[
            Paragraph("AA's Computer &amp; Remote Services", hero_title),
            ""
        ],[
            Paragraph("Professional Email Cleaner Suite  ·  Cleanup Report", hero_sub),
            ""
        ]],
        colWidths=[CONTENT_W * 0.80, CONTENT_W * 0.20],
    )
    hero_content.setStyle(TableStyle([
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))

    banner_table = Table(
        [[hero_content]],
        colWidths=[CONTENT_W],
    )
    banner_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), INDIGO_DARK),
        ("LEFTPADDING",  (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("TOPPADDING",   (0, 0), (-1, -1), 20),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 20),
        ("ROUNDEDCORNERS", [8]),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── 2. Client Info Cards ───────────────────────────────────────────────────
    story.append(AccentLine(36, 4, INDIGO))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("REPORT DETAILS", section_heading))

    col_w = (CONTENT_W - 12) / 2   # 12 pt gutter between two cards

    def info_cell(lbl, val):
        """Returns a list of Paragraphs for one label/value pair."""
        return [Paragraph(lbl, label_s), Paragraph(val or "N/A", value_s)]

    # Row 1 — Client | Gmail
    card_data_1 = [
        info_cell("CLIENT NAME", client),
        info_cell("GMAIL ADDRESS", gmail),
    ]
    # Row 2 — Mode | Date
    card_data_2 = [
        info_cell("CLEANING MODE", mode),
        info_cell("DATE &amp; TIME", datetime.now().strftime("%B %d, %Y  ·  %H:%M:%S")),
    ]

    def make_card_row(cells):
        tbl = Table(
            [[
                Table([[c] for c in cells[0]], colWidths=[col_w]),
                Table([[c] for c in cells[1]], colWidths=[col_w]),
            ]],
            colWidths=[col_w, col_w],
            spaceBefore=0,
        )
        tbl.setStyle(TableStyle([
            # Left card
            ("BACKGROUND",   (0, 0), (0, 0), SLATE_LIGHT),
            ("ROUNDEDCORNERS", [6]),
            ("BOX",          (0, 0), (0, 0), 0.5, BORDER),
            ("LEFTPADDING",  (0, 0), (0, 0), 12),
            ("RIGHTPADDING", (0, 0), (0, 0), 12),
            ("TOPPADDING",   (0, 0), (0, 0), 10),
            ("BOTTOMPADDING",(0, 0), (0, 0), 10),
            # Right card
            ("BACKGROUND",   (1, 0), (1, 0), SLATE_LIGHT),
            ("BOX",          (1, 0), (1, 0), 0.5, BORDER),
            ("LEFTPADDING",  (1, 0), (1, 0), 12),
            ("RIGHTPADDING", (1, 0), (1, 0), 12),
            ("TOPPADDING",   (1, 0), (1, 0), 10),
            ("BOTTOMPADDING",(1, 0), (1, 0), 10),
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("INNERGRID",    (0, 0), (-1, -1), 0, WHITE),
            ("COLPADDING",   (0, 0), (-1, -1), 6),
        ]))
        return tbl

    story.append(make_card_row(card_data_1))
    story.append(Spacer(1, 0.25 * cm))
    story.append(make_card_row(card_data_2))
    story.append(Spacer(1, 0.55 * cm))

    # ── 3. Stats Panel ─────────────────────────────────────────────────────────
    story.append(AccentLine(36, 4, INDIGO))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("CLEANUP SUMMARY", section_heading))

    stat_inner = Table(
        [
            [Paragraph(f"{cleaned_count:,}", big_num)],
            [Paragraph("emails successfully marked as read", big_sub)],
        ],
        colWidths=[CONTENT_W],
    )
    stat_inner.setStyle(TableStyle([
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))

    stat_card = Table([[stat_inner]], colWidths=[CONTENT_W])
    stat_card.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), INDIGO_SOFT),
        ("BOX",          (0, 0), (-1, -1), 1.5, INDIGO),
        ("LEFTPADDING",  (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("TOPPADDING",   (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 18),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(stat_card)
    story.append(Spacer(1, 0.55 * cm))

    # ── 4. Status ─────────────────────────────────────────────────────────────
    story.append(AccentLine(36, 4, colors.HexColor("#16a34a")))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("STATUS", section_heading))

    status_inner = Table(
        [[
            Paragraph("✔", S("StatusIcon",
                fontName="Helvetica-Bold", fontSize=18,
                textColor=GREEN_TEXT, leading=22, spaceAfter=0)),
            Paragraph("COMPLETED SUCCESSFULLY", status_ok),
        ]],
        colWidths=[28, CONTENT_W - 28],
    )
    status_inner.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))

    status_card = Table([[status_inner]], colWidths=[CONTENT_W])
    status_card.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), GREEN_BG),
        ("BOX",          (0, 0), (-1, -1), 1, colors.HexColor("#86efac")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING",   (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 14),
    ]))
    story.append(status_card)
    story.append(Spacer(1, 1.5 * cm))

    # ── 5. Footer ─────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "AA's Computer &amp; Remote Services  ·  Generated by AA Email Cleaner Suite V3.1",
        footer_s
    ))

    # ── Build with sidebar stripe ──────────────────────────────────────────────
    doc.build(
        story,
        onFirstPage=lambda c, d: _on_page(c, d, PAGE_W),
        onLaterPages=lambda c, d: _on_page(c, d, PAGE_W),
    )

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