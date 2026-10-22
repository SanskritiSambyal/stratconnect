"""Streamlit view functions for each page."""
import io

import pandas as pd
import streamlit as st

import auth
import storage
from constants import (APP_NAME, ORG_NAME, DATA_FIELDS, FIELD_KEYS, LABELS, OPTIONS,
                       STATUS_STYLE, PRIORITY_COLOR, ROLES, ROLE_HELP, can_edit, can_admin,
                       build_prompt)

EXPORT_ORDER = ["priority", "name", "desig", "company", "sector", "email", "phone",
                "conn", "channel", "purpose", "owner", "status", "lastdate", "lastnote",
                "follow", "next", "nextdate", "notes"]


def inject_css():
    st.markdown("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Space+Mono:wght@400;700&display=swap');
      h1,h2,h3{font-family:'Fraunces',Georgia,serif!important;letter-spacing:-.01em}
      .scx-brand{font-family:'Fraunces',Georgia,serif;font-size:26px;font-weight:600;line-height:1}
      .scx-brand .d{color:#b1832b}
      .scx-kick{font-family:'Space Mono',monospace;font-size:10.5px;letter-spacing:.14em;
        text-transform:uppercase;color:#8a867a}
      .scx-eyebrow{font-family:'Space Mono',monospace;font-size:11px;letter-spacing:.16em;
        text-transform:uppercase;color:#8a5f14;font-weight:700;margin-bottom:2px}
      .pill{font-family:'Space Mono',monospace;font-size:11px;font-weight:700;padding:3px 9px;
        border-radius:5px;white-space:nowrap;display:inline-block}
      .sub{color:#7a766a;font-size:12.5px}
      .next-over{color:#9c3a2b;font-weight:700;font-family:'Space Mono',monospace;font-size:12px}
      .next{color:#7a766a;font-family:'Space Mono',monospace;font-size:12px}
      .barwrap{background:rgba(120,110,90,.15);border-radius:5px;height:8px;overflow:hidden}
      .barwrap>span{display:block;height:100%;background:#b1832b;border-radius:5px}
      div[data-testid="stMetricValue"]{font-family:'Space Mono',monospace}
    </style>
    """, unsafe_allow_html=True)


def header(user=None):
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(f'<div class="scx-brand">StratConnect<span class="d">.</span></div>'
                    f'<div class="scx-kick">{ORG_NAME}</div>', unsafe_allow_html=True)
    with c2:
        if user:
            st.markdown(f'<div style="text-align:right" class="sub">{user["email"]}<br>'
                        f'<b>{user["role"].title()}</b></div>', unsafe_allow_html=True)


def pill(status):
    bg, fg = STATUS_STYLE.get(status, ("#e4e2d6", "#5f5b4d"))
    return f'<span class="pill" style="background:{bg};color:{fg}">{status or "—"}</span>'


# ---------------------------------------------------------------------- login
def login_view():
    inject_css()
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        header()
        st.write("")
        st.markdown('<div class="scx-eyebrow">Members only</div>', unsafe_allow_html=True)
        st.subheader("Verify your institute email")
        st.caption("Access is limited to approved institute email addresses. "
                   "We'll email you a one-time code to confirm it's you.")

        stage = "code" if "otp_hash" in st.session_state else "email"

        if stage == "email":
            with st.form("email_form"):
                email = st.text_input("Institute email", placeholder="you@iimmumbai.ac.in")
                submitted = st.form_submit_button("Send me a code", type="primary")
            if submitted:
                email = email.strip().lower()
                if not auth.valid_email(email):
                    st.error("Please enter a valid email address.")
                elif not auth.resolve_role(email):
                    st.error("This email isn't on the approved list yet. "
                             "Ask a club admin to grant access to this address.")
                else:
                    ok, msg, dev = auth.send_code(email)
                    (st.success if ok else st.error)(msg)
                    if dev:
                        st.info(f"Your code (dev mode): **{dev}**")
                    if ok:
                        st.rerun()
        else:
            st.success(f"Code sent to **{st.session_state.get('otp_email')}**.")
            with st.form("code_form"):
                code = st.text_input("6-digit code", max_chars=6, placeholder="123456")
                submitted = st.form_submit_button("Verify & enter", type="primary")
            if submitted:
                ok, msg = auth.verify_code(code)
                if ok and auth.complete_login():
                    st.rerun()
                elif ok:
                    st.error("Verified, but your access was removed. Contact an admin.")
                else:
                    st.error(msg)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Resend code"):
                    ok, msg, dev = auth.send_code(st.session_state.get("otp_email"))
                    (st.success if ok else st.error)(msg)
                    if dev:
                        st.info(f"Your code (dev mode): **{dev}**")
            with c2:
                if st.button("Use a different email"):
                    for k in ("otp_hash", "otp_email", "otp_expires", "otp_sent_at", "otp_attempts"):
                        st.session_state.pop(k, None)
                    st.rerun()


# --------------------------------------------------------------------- tracker
def _overdue(c, today):
    return c.get("follow") == "Yes" and c.get("nextdate") and c["nextdate"] < today


def tracker_view(user):
    import datetime
    today = datetime.date.today().isoformat()
    contacts = storage.list_contacts()

    total = len(contacts)
    due = sum(1 for c in contacts if _overdue(c, today))
    confirmed = sum(1 for c in contacts if c.get("status") == "Confirmed")
    live = sum(1 for c in contacts if c.get("status") in ("In Conversation", "Call Scheduled"))

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total contacts", total)
    k2.metric("Follow-ups overdue", due)
    k3.metric("In conversation", live)
    k4.metric("Confirmed", confirmed)

    st.divider()

    # pipeline breakdown
    st.markdown('<div class="scx-eyebrow">Pipeline</div>', unsafe_allow_html=True)
    counts = {s: 0 for s in OPTIONS["status"]}
    for c in contacts:
        if c.get("status") in counts:
            counts[c["status"]] += 1
    shown = [(s, n) for s, n in counts.items() if n]
    if shown:
        mx = max(n for _, n in shown)
        for s, n in shown:
            a, b, cc = st.columns([2, 5, 1])
            a.markdown(pill(s), unsafe_allow_html=True)
            b.markdown(f'<div class="barwrap" style="margin-top:6px"><span style="width:{int(n/mx*100)}%"></span></div>',
                       unsafe_allow_html=True)
            cc.markdown(f'<div style="text-align:right;font-family:Space Mono,monospace;font-weight:700">{n}</div>',
                        unsafe_allow_html=True)
    else:
        st.caption("No contacts yet — the pipeline fills in as you add them.")

    # export
    ex1, ex2 = st.columns([1, 3])
    with ex1:
        if contacts:
            df = _export_df(contacts)
            st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"),
                               file_name="stratconnect-contacts.csv", mime="text/csv")
    with ex2:
        url = storage.sheet_url()
        if url:
            st.markdown(f'<div style="padding-top:6px"><a href="{url}" target="_blank">Open the live Google Sheet ↗</a></div>',
                        unsafe_allow_html=True)

    st.divider()

    # search + filter
    f1, f2 = st.columns([2, 2])
    q = f1.text_input("Search", placeholder="Name, company, owner, sector…", label_visibility="collapsed")
    status_opts = ["All status"] + [s for s in OPTIONS["status"] if counts.get(s)]
    sf = f2.selectbox("Filter", status_opts, label_visibility="collapsed")

    ql = (q or "").lower()
    rows = []
    for c in contacts:
        if sf != "All status" and c.get("status") != sf:
            continue
        if ql:
            hay = " ".join(str(c.get(k, "")) for k in ("name", "company", "owner", "sector", "desig", "purpose", "email")).lower()
            if ql not in hay:
                continue
        rows.append(c)

    if not contacts:
        st.info("No contacts yet. " + ("Use **Add entry** to log the first one."
                if can_edit(user["role"]) else "An editor will add the first one."))
        return
    if not rows:
        st.caption("No contacts match that search or filter.")
        return

    editable = can_edit(user["role"])
    for c in rows:
        over = _overdue(c, today)
        title_bits = [c.get("name") or "Unnamed"]
        if c.get("company"):
            title_bits.append(c["company"])
        label = "  ·  ".join(title_bits)
        with st.expander(label):
            top = st.columns([1, 1])
            top[0].markdown(pill(c.get("status")), unsafe_allow_html=True)
            if c.get("nextdate"):
                cls = "next-over" if over else "next"
                tag = "Overdue · " if over else "Next · "
                top[1].markdown(f'<div style="text-align:right" class="{cls}">{tag}{_fmt(c["nextdate"])}</div>',
                                unsafe_allow_html=True)
            meta = []
            if c.get("priority"):
                col = PRIORITY_COLOR.get(c["priority"], "#7a766a")
                meta.append(f'<span style="color:{col};font-weight:600">● {c["priority"]}</span>')
            if c.get("conn"):
                meta.append(c["conn"])
            if c.get("owner"):
                meta.append("Owner: " + c["owner"])
            if meta:
                st.markdown('<div class="sub">' + "  ·  ".join(meta) + "</div>", unsafe_allow_html=True)

            pairs = [("Email", c.get("email")), ("Phone / LinkedIn", c.get("phone")),
                     ("Sector", c.get("sector")), ("Purpose", c.get("purpose")),
                     ("Preferred channel", c.get("channel")), ("Follow-up needed", c.get("follow")),
                     ("Last interaction", " — ".join(x for x in (_fmt(c.get("lastdate")), c.get("lastnote")) if x)),
                     ("Next step", " ".join(x for x in (c.get("next"), ("by " + _fmt(c["nextdate"])) if c.get("nextdate") else "") if x)),
                     ("Notes", c.get("notes"))]
            dc = st.columns(2)
            i = 0
            for k, v in pairs:
                if v:
                    dc[i % 2].markdown(f'<div class="sub" style="text-transform:uppercase;font-size:10px">{k}</div>'
                                       f'<div style="margin-bottom:8px">{v}</div>', unsafe_allow_html=True)
                    i += 1
            if editable:
                b1, b2, _ = st.columns([1, 1, 4])
                if b1.button("Edit", key="e_" + c["_id"]):
                    st.session_state["editing_id"] = c["_id"]
                    st.session_state["page"] = "Add entry"
                    st.rerun()
                if b2.button("Delete", key="d_" + c["_id"]):
                    k = "confirm_" + c["_id"]
                    if st.session_state.get(k):
                        storage.delete_contact(c["_id"])
                        st.session_state.pop(k, None)
                        st.rerun()
                    else:
                        st.session_state[k] = True
                        st.warning("Click Delete again to confirm.")


def _fmt(iso):
    import datetime
    if not iso:
        return ""
    try:
        return datetime.date.fromisoformat(iso).strftime("%d %b %Y")
    except Exception:
        return str(iso)


def _export_df(contacts):
    data = []
    for i, c in enumerate(contacts, 1):
        row = {"ID": f"{i:03d}"}
        for k in EXPORT_ORDER:
            row[LABELS[k]] = c.get(k, "")
        data.append(row)
    return pd.DataFrame(data)


# -------------------------------------------------------------------- add/edit
def add_edit_view(user):
    if not can_edit(user["role"]):
        st.info("You have view-only access. Ask an admin to make you an editor to add contacts.")
        return

    editing_id = st.session_state.get("editing_id")
    existing = None
    if editing_id:
        existing = next((c for c in storage.list_contacts() if c["_id"] == editing_id), None)
        if not existing:
            st.session_state.pop("editing_id", None)
            editing_id = None

    st.markdown('<div class="scx-eyebrow">' + ("Editing" if editing_id else "New contact") + "</div>",
                unsafe_allow_html=True)
    st.subheader(("Edit " + existing.get("name", "contact")) if existing else "Log an outreach contact")
    st.caption("Everything added here is shared with everyone who can open this hub.")

    g = (existing or {})

    def _sel(key):
        opts = OPTIONS[key]
        cur = g.get(key)
        return opts.index(cur) if cur in opts else (opts.index("Medium") if key == "priority"
               else opts.index("Not Started") if key == "status" else 0)

    with st.form("contact_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input(LABELS["name"] + " *", g.get("name", ""))
        desig = c2.text_input(LABELS["desig"], g.get("desig", ""))
        company = c3.text_input(LABELS["company"], g.get("company", ""))
        c4, c5, c6 = st.columns(3)
        sector = c4.text_input(LABELS["sector"], g.get("sector", ""))
        email = c5.text_input(LABELS["email"], g.get("email", ""))
        phone = c6.text_input(LABELS["phone"], g.get("phone", ""))
        c7, c8, c9 = st.columns(3)
        conn = c7.selectbox(LABELS["conn"], OPTIONS["conn"], index=_sel("conn"))
        channel = c8.selectbox(LABELS["channel"], OPTIONS["channel"], index=_sel("channel"))
        purpose = c9.selectbox(LABELS["purpose"], OPTIONS["purpose"], index=_sel("purpose"))
        c10, c11, c12 = st.columns(3)
        owner = c10.text_input(LABELS["owner"], g.get("owner", ""))
        priority = c11.selectbox(LABELS["priority"], OPTIONS["priority"], index=_sel("priority"))
        status = c12.selectbox(LABELS["status"], OPTIONS["status"], index=_sel("status"))
        c13, c14 = st.columns(2)
        lastdate = c13.date_input(LABELS["lastdate"], value=_date(g.get("lastdate")), format="YYYY-MM-DD")
        lastnote = c14.text_input(LABELS["lastnote"], g.get("lastnote", ""))
        c15, c16, c17 = st.columns(3)
        follow = c15.selectbox(LABELS["follow"], OPTIONS["follow"], index=_sel("follow"))
        nxt = c16.text_input(LABELS["next"], g.get("next", ""))
        nextdate = c17.date_input(LABELS["nextdate"], value=_date(g.get("nextdate")), format="YYYY-MM-DD")
        notes = st.text_area(LABELS["notes"], g.get("notes", ""))

        submitted = st.form_submit_button("Save changes" if editing_id else "Add contact", type="primary")

    if submitted:
        if not name.strip():
            st.error("Add a contact name first.")
            return
        data = {"name": name.strip(), "desig": desig.strip(), "company": company.strip(),
                "sector": sector.strip(), "email": email.strip(), "phone": phone.strip(),
                "conn": conn, "channel": channel, "purpose": purpose, "owner": owner.strip(),
                "priority": priority, "status": status,
                "lastdate": lastdate.isoformat() if lastdate else "", "lastnote": lastnote.strip(),
                "follow": follow, "next": nxt.strip(),
                "nextdate": nextdate.isoformat() if nextdate else "", "notes": notes.strip()}
        try:
            if editing_id:
                storage.update_contact(editing_id, data, created_at=g.get("created_at"))
                st.session_state.pop("editing_id", None)
                st.success("Changes saved.")
            else:
                storage.add_contact(data)
                st.success("Contact added.")
            st.session_state["page"] = "Tracker"
            st.rerun()
        except Exception as e:
            st.error(f"Could not save ({e}).")

    if editing_id:
        if st.button("Cancel edit"):
            st.session_state.pop("editing_id", None)
            st.session_state["page"] = "Tracker"
            st.rerun()


def _date(iso):
    import datetime
    if not iso:
        return None
    try:
        return datetime.date.fromisoformat(iso)
    except Exception:
        return None


# --------------------------------------------------------------------- outreach
def outreach_view(user):
    st.markdown('<div class="scx-eyebrow">Outreach studio</div>', unsafe_allow_html=True)
    st.subheader("Craft a company-specific pitch")
    left, right = st.columns(2)
    with left:
        company = st.text_input("Target company *", "Tumbledry")
        window = st.selectbox("Research period", ["30", "90", "180", "365"],
                              index=1, format_func=lambda v: f"Last {v} days")
        focus = st.selectbox("Business focus", ["Growth & market expansion", "Customer retention & loyalty",
                "Product & go-to-market", "Operations & unit economics", "Brand & positioning",
                "Digital transformation"])
        collab = st.selectbox("Collaboration", ["Company-led case competition", "Case competition + mentorship",
                "Strategy workshop", "Long-term industry partnership"])
        tone = st.selectbox("Email voice", ["Consulting-grade, credible", "Concise executive",
                "Warm and relationship-led", "Bold, insight-led"])
        context = st.text_area("Custom angle (optional)", placeholder="Add a possible strategic opportunity.")
        sender = st.text_input("Club representative", placeholder="[Your Name]")
        semail = st.text_input("Official club email", placeholder="[Official Email]")
        st.info("Use ChatGPT or Claude with web search on. Verify sources, dates and claims before sending.")

    prompt = build_prompt({"company": company, "window": window, "focus": focus, "collab": collab,
                           "tone": tone, "context": context, "sender": sender, "email": semail})
    with right:
        st.markdown('<div class="scx-eyebrow">Personalized prompt</div>', unsafe_allow_html=True)
        st.subheader("Prompt preview")
        st.code(prompt, language=None)
        fname = "stratconnect-" + "".join(ch if ch.isalnum() else "-" for ch in (company or "company")).lower() + ".txt"
        st.download_button("Download .txt", prompt.encode("utf-8"), file_name=fname, mime="text/plain")
        st.caption("Paste into ChatGPT or Claude with search enabled. You’ll get three strategically "
                   "different, source-informed emails, strongest marked Recommended.")


# ---------------------------------------------------------------------- access
def access_view(user):
    if not can_admin(user["role"]):
        st.info("Only admins can manage access.")
        return
    st.markdown('<div class="scx-eyebrow">Access control</div>', unsafe_allow_html=True)
    st.subheader("Who can use this hub")
    st.caption("Grant a specific institute email, or a whole institute domain (e.g. @iimmumbai.ac.in). "
               "Everyone still verifies ownership of their email by one-time code before they get in.")

    with st.form("grant_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([3, 2, 1])
        entry = c1.text_input("Email or @domain", placeholder="person@iimmumbai.ac.in  or  @iimmumbai.ac.in")
        role = c2.selectbox("Role", ROLES, index=0, format_func=lambda r: f"{r.title()} — {ROLE_HELP[r]}")
        c3.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        add = c3.form_submit_button("Grant", type="primary")
    if add:
        e = entry.strip().lower()
        ok = e.startswith("@") and "." in e[1:] or auth.valid_email(e)
        if not ok:
            st.error("Enter a valid email, or a domain starting with @.")
        else:
            storage.set_access(e, role)
            st.success(f"Granted {role} to {e}.")
            st.rerun()

    st.divider()
    try:
        rows = storage.list_access()
    except Exception as e:
        st.error(f"Could not read the access list ({e}).")
        return
    bootstrap = [a.strip().lower() for a in (auth._secret("admins", []) or [])]
    if bootstrap:
        st.caption("Permanent admins (set in app secrets): " + ", ".join(bootstrap))
    if not rows:
        st.info("No granted emails or domains yet. Add one above.")
        return
    for entry, role in rows:
        c1, c2, c3 = st.columns([3, 2, 1])
        c1.write(entry)
        new_role = c2.selectbox("role", ROLES, index=ROLES.index(role) if role in ROLES else 0,
                                key="role_" + entry, label_visibility="collapsed")
        if new_role != role:
            storage.set_access(entry, new_role)
            st.rerun()
        if c3.button("Remove", key="rm_" + entry):
            storage.remove_access(entry)
            st.rerun()
