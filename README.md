# StratConnect Hub

Networking & outreach tracker + corporate-outreach prompt studio for the
**Strategy & Consulting Club, IIM Mumbai** — a Streamlit app.

- **Tracker** — shared contact pipeline with KPIs, status breakdown, search, filter, CSV export.
- **Add entry** — log/edit contacts (editors & admins only).
- **Outreach studio** — generates the company-specific research prompt; copy or download it.
- **Access** — admins grant/revoke institute emails or whole domains, and set roles.

Data lives in a **Google Sheet**. Access is limited to **approved institute emails**,
each verified by a **one-time code** sent to that address.

**Roles:** `viewer` (browse + export) · `editor` (+ add/edit/delete) · `admin` (+ manage access).

---

## What you need (one-time)

1. A **Google account** (to create the Sheet and a service account).
2. A **GitHub account** (to host the code) and a **Streamlit Community Cloud** account (free) — https://share.streamlit.io.
3. An **email sender** for the one-time codes — a Gmail with an App Password is easiest.

---

## Step 1 — Create the Google Sheet

1. Create a new blank Google Sheet. Name it e.g. *StratConnect Data*.
2. Copy its URL (or the long id in the URL) — you'll paste it into secrets.
   The app creates the `contacts` and `access` tabs automatically on first run.

## Step 2 — Create a service account (so the app can read/write the Sheet)

1. Go to https://console.cloud.google.com → create (or pick) a project.
2. **APIs & Services → Library** → enable **Google Sheets API** and **Google Drive API**.
3. **APIs & Services → Credentials → Create credentials → Service account**. Name it, create.
4. Open the service account → **Keys → Add key → Create new key → JSON**. A `.json` file downloads.
5. Open that JSON — you'll copy its fields into secrets (Step 5). Note the `client_email`.
6. **Share the Google Sheet** (Share button) with that `client_email`, as **Editor**.

## Step 3 — Set up the code-email sender (SMTP)

Easiest is a Gmail App Password:
1. On the sending Google account, turn on **2-Step Verification**.
2. Google account → **Security → App passwords** → create one for "Mail". Copy the 16 characters
3. Use `smtp.gmail.com`, port `587`, your Gmail as user, the app password as password.

(Or use your institute's SMTP server details instead.)

## Step 4 — Put the code on GitHub

Create a new GitHub repo and upload this folder's contents (or push with git):

```bash
git init
git add .
git commit -m "StratConnect Hub"
git branch -M main
git remote add origin https://github.com/<you>/stratconnect.git
git push -u origin main
```

`.gitignore` already keeps your real `secrets.toml` out of the repo. **Never commit secrets.**

## Step 5 — Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io → **Create app** → pick your repo, branch `main`, main file `app.py`.
2. **Advanced settings → Secrets**: paste the contents of `.streamlit/secrets.toml.example`
   with your real values (service-account JSON fields, sheet URL, SMTP, admins, domains).
   - `private_key` must keep its `\n` line breaks exactly as in the JSON.
   - Put at least your own email in `admins = [...]` so you can get in and manage access.
3. **Deploy.** First load takes a minute while it installs dependencies.

Your team opens the app URL, enters their institute email, gets a code, and they're in —
if their email is approved. As an admin, use the **Access** page to grant others.

---

## Run it locally (optional, for testing)

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then edit it
streamlit run app.py
```

To test without setting up SMTP, add `allow_insecure_dev_login = true` to secrets —
the one-time code is then shown on screen instead of emailed. **Remove it for real use.**

---

## How access works

- An email gets in only if it is: listed in `admins`, granted on the **Access** page
  (as an email or an `@domain`), or on a domain in `allowed_domains`.
- Everyone proves they own their email via the one-time code before entering — so a
  granted domain means "anyone with a real @that-domain address", not outsiders.
- Change someone's role or remove them any time on the **Access** page; it takes effect
  on their next action, no re-deploy needed.

## Notes & limits

- Writes update the Google Sheet directly; fine for a club-sized tracker (hundreds of rows,
  a few simultaneous editors). It is not built for heavy concurrent editing.
- One-time codes expire after 10 minutes; resend is rate-limited to once per 30 seconds.
- The Sheet is the source of truth — you can also open it directly (link on the Tracker page)
  to bulk-edit or back up.
