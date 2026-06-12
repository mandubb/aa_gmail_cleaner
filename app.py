import streamlit as st
from gmail_cleanup import (
    authenticate,
    get_unread_old_emails,
    mark_as_read,
    get_count,
    get_profile_email,
    generate_report,
    log_action
)
from datetime import datetime

# -----------------------------------
# PAGE CONFIG
# -----------------------------------
st.set_page_config(
    page_title="AA Email Cleaner Suite",
    page_icon="📧",
    layout="wide"
)

# -----------------------------------
# HEADER
# -----------------------------------
st.title("📧 AA's Email Cleaner Suite")
st.caption("Professional Inbox Cleanup Tool")

# -----------------------------------
# SIDEBAR
# -----------------------------------
with st.sidebar:

    st.header("⚙️ Settings")

    client_name = st.text_input(
        "Client Name / Label",
        placeholder="e.g. Juan, Personal, Work"
    )

    mode = st.radio(
        "Cleaning Mode",
        [
            "Safe (Recommended)",
            "Aggressive (Unlocked)"
        ]
    )

    if mode == "Aggressive (Unlocked)":
        st.warning(
            "⚠️ This will mark ALL unread emails as read."
        )

    connect_btn = st.button(
        "🔌 Connect Gmail Account",
        use_container_width=True
    )

# -----------------------------------
# CONNECT
# -----------------------------------
if connect_btn:

    if not client_name:
        st.error("Please enter a client name first.")

    else:

        with st.spinner("Connecting to Gmail..."):

            service = authenticate(client_name)

            gmail_address = get_profile_email(service)

            st.session_state.service = service
            st.session_state.client = client_name
            st.session_state.gmail = gmail_address

            log_action(
                client_name,
                f"CONNECTED Gmail: {gmail_address}"
            )

        st.success(f"Connected: {gmail_address}")

# -----------------------------------
# DASHBOARD
# -----------------------------------
if "service" in st.session_state:

    st.success(
        f"Connected Gmail: {st.session_state.gmail}"
    )

    st.divider()

    st.subheader("📊 Inbox Dashboard")

    if st.button(
        "🔍 Scan Inbox",
        use_container_width=True
    ):

        with st.spinner("Scanning inbox..."):

            safe_count = get_count(
                st.session_state.service,
                "Safe (Recommended)"
            )

            aggressive_count = get_count(
                st.session_state.service,
                "Aggressive (Unlocked)"
            )

            st.session_state.safe_count = safe_count
            st.session_state.aggressive_count = aggressive_count

            log_action(
                st.session_state.client,
                f"SCAN | Safe={safe_count} | Aggressive={aggressive_count}"
            )

    # ----------------------------
    # DASHBOARD CARDS
    # ----------------------------
    if "safe_count" in st.session_state:

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "🧹 Safe Mode Emails",
                st.session_state.safe_count
            )

        with col2:
            st.metric(
                "⚡ Aggressive Mode Emails",
                st.session_state.aggressive_count
            )

        st.divider()

        # ----------------------------
        # CLEANUP
        # ----------------------------
        st.subheader("🧹 Cleanup")

        if mode == "Aggressive (Unlocked)":

            confirm_text = st.text_input(
                "Type CONFIRM to enable aggressive cleanup"
            )

            can_clean = confirm_text == "CONFIRM"

            if not can_clean:
                st.warning(
                    "Aggressive cleanup is locked."
                )

        else:
            can_clean = True

        if can_clean:

            if st.button(
                "🚀 Start Cleanup",
                type="primary",
                use_container_width=True
            ):

                with st.spinner("Cleaning inbox..."):

                    ids = get_unread_old_emails(
                        st.session_state.service,
                        mode
                    )

                    count = len(ids)

                    mark_as_read(
                        st.session_state.service,
                        ids
                    )

                    report_path = generate_report(
                        st.session_state.client,
                        st.session_state.gmail,
                        mode,
                        count
                    )

                    st.session_state.report_path = report_path

                    log_action(
                        st.session_state.client,
                        f"CLEANUP COMPLETE | Mode={mode} | Emails={count}"
                    )

                st.success(
                    f"Successfully marked {count:,} emails as read."
                )

    # ----------------------------
    # REPORT DOWNLOAD
    # ----------------------------
    if "report_path" in st.session_state:

        st.divider()

        st.subheader("📄 Cleanup Report")

        with open(
            st.session_state.report_path,
            "rb"
        ) as f:

            st.download_button(
                label="⬇ Download Report",
                data=f,
                file_name=st.session_state.report_path.split("\\")[-1],
                mime="text/plain",
                use_container_width=True
            )

# -----------------------------------
# FOOTER
# -----------------------------------
st.divider()

st.caption(
    "AA's Computer & Remote Services • Professional Email Cleaner Suite"
)