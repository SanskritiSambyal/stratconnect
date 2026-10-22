"""StratConnect Hub — Streamlit app.

Networking & outreach tracker + corporate-outreach prompt studio for the
Strategy & Consulting Club, IIM Mumbai. Access is limited to verified,
approved institute emails. Data lives in a shared Google Sheet.
"""
import streamlit as st

import auth
import views
from constants import APP_NAME, can_edit, can_admin

st.set_page_config(page_title=APP_NAME, page_icon="◈", layout="wide",
                   initial_sidebar_state="expanded")
views.inject_css()

# ---- auth gate ----
user = auth.current_user()
if not user:
    views.login_view()
    st.stop()

# re-resolve role each run so access changes take effect without re-login
fresh_role = auth.resolve_role(user["email"])
if not fresh_role:
    auth.logout()
    st.warning("Your access has been removed. Please contact a club admin.")
    st.stop()
user["role"] = fresh_role
st.session_state["auth"] = user

# ---- sidebar / nav ----
with st.sidebar:
    st.markdown('<div class="scx-brand">StratConnect<span class="d">.</span></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub">{user["email"]}<br><b>{user["role"].title()}</b></div>',
                unsafe_allow_html=True)
    st.divider()

    pages = ["Tracker"]
    if can_edit(user["role"]):
        pages.append("Add entry")
    pages.append("Outreach studio")
    if can_admin(user["role"]):
        pages.append("Access")

    if st.session_state.get("page") not in pages:
        st.session_state["page"] = "Tracker"
    page = st.radio("Go to", pages, key="page", label_visibility="collapsed")

    st.divider()
    st.caption("Tip: use the ⋮ menu (top-right) → Settings to switch between light and dark.")
    if st.button("Log out"):
        auth.logout()
        st.rerun()

# ---- header + route ----
views.header(user)
st.write("")

try:
    if page == "Tracker":
        views.tracker_view(user)
    elif page == "Add entry":
        views.add_edit_view(user)
    elif page == "Outreach studio":
        views.outreach_view(user)
    elif page == "Access":
        views.access_view(user)
except Exception as e:
    st.error(f"Something went wrong loading this page: {e}")
    st.caption("If this mentions the spreadsheet or credentials, check the app secrets "
               "(gcp_service_account and gsheets.spreadsheet).")
