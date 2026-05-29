import streamlit as st
from gmail_cleanup import authenticate, get_unread_old_emails, mark_as_read, log_action
from datetime import datetime

st.set_page_config(page_title="AA Email Cleaner Suite", layout="centered")

st.title("🧹 AA’s Email Cleaner Suite")
st.caption("Professional Inbox Cleanup Tool")

# ----------------------------
# CLIENT INFO (optional)
# ----------------------------
client_name = st.text_input("Client Name / Label")

st.markdown("---")

# ----------------------------
# MODE LOCK (SAFETY CONTROL)
# ----------------------------
mode = st.radio("Cleaning Mode", ["Safe (Recommended)", "Aggressive (Unlocked)"])

if mode == "Aggressive (Unlocked)":
    st.warning("⚠️ Aggressive mode removes ALL unread emails.")

st.markdown("---")

# ----------------------------
# CONNECT GMAIL
# ----------------------------
if st.button("🔌 Connect Gmail Account"):

    if not client_name:
        st.error("Please enter client name first.")
    else:
        service = authenticate(client_name)
        st.session_state.service = service
        st.session_state.client = client_name
        st.success(f"Connected: {client_name}")

# ----------------------------
# SCAN EMAILS
# ----------------------------
if "service" in st.session_state:

    if st.button("🔍 Scan Emails"):

        ids = get_unread_old_emails(
            st.session_state.service,
            mode
        )

        st.session_state.ids = ids

        st.info(f"Found {len(ids)} emails")

        log_action(client_name, f"SCAN: {len(ids)} emails found at {datetime.now()}")

# ----------------------------
# CLEAN EMAILS
# ----------------------------
if "ids" in st.session_state:

    if st.button("🧹 Mark as Read"):

        mark_as_read(st.session_state.service, st.session_state.ids)

        log_action(client_name, f"CLEANED: {len(st.session_state.ids)} emails at {datetime.now()}")

        st.success("Cleanup completed successfully!")