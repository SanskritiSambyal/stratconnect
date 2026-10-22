"""StratConnect Hub — Streamlit app.
 
Networking & outreach tracker + corporate-outreach prompt studio for the
Strategy & Consulting Club, IIM Mumbai. Access is limited to verified,
approved institute emails. Data lives in a shared Google Sheet.
"""
import datetime
 
import streamlit as st
 
import auth
import views
from constants import APP_NAME, can_edit, can_admin
 
st.set_page_config(page_title=APP_NAME, page_icon="◈", layout="wide",
                   initial_sidebar_state="expanded")
views.inject_css()
 
# ---- persistent 8-hour session via a signed cookie ----
# Uses extra-streamlit-components if available; degrades to per-tab session if not.
cookie_mgr = None
try:
    import extra_streamlit_components as stx
    cookie_mgr = stx.CookieManager(key="scx_cookie_mgr")
except Exception:
    cookie_mgr = None
 
if cookie_mgr is not None:
    # write or clear the cookie if the auth layer asked us to
    _tok = st.session_state.pop("_pending_cookie", None)
    if _tok:
        try:
            cookie_mgr.set(auth.COOKIE_NAME, _tok, key="scx_set",
                           expires_at=datetime.datetime.now() + datetime.timedelta(hours=auth.SESSION_HOURS))
        except Exception:
            pass
    if st.session_state.pop("_clear_cookie", None):
        try:
            cookie_mgr.delete(auth.COOKIE_NAME, key="scx_del")
        except Exception:
            pass
    # let the cookie component mount once so get() can read on first load
    if not st.session_state.get("_cookie_ready"):
        st.session_state["_cookie_ready"] = True
        st.rerun()
 
# ---- auth gate ----
user = auth.current_user()
if not user and cookie_mgr is not None:
    try:
        _token = cookie_mgr.get(auth.COOKIE_NAME)
    except Exception:
        _token = None
    if _token and auth.restore_from_token(_token):
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
 
# show any acknowledgement queued before the last rerun
views.show_flash()
 
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
 
    # Navigation: keep the current page in a plain session var (NOT the radio's
    # widget key) so code can redirect after saving without Streamlit complaining.
    current = st.session_state.get("page", "Tracker")
    if current not in pages:
        current = "Tracker"
    page = st.radio("Go to", pages, index=pages.index(current), label_visibility="collapsed")
    st.session_state["page"] = page
 
    st.divider()
    if st.button("Log out", use_container_width=True):
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
 
