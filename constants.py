"""Shared constants: field schema, dropdown options, status styling, prompt builder."""
 
APP_NAME = "StratConnect Hub"
ORG_NAME = "Strategy & Consulting Committee — IIM Mumbai"
 
# (key, label) — the order used in forms and exports.
DATA_FIELDS = [
    ("name",     "Contact Name"),
    ("desig",    "Designation"),
    ("company",  "Company / Org"),
    ("sector",   "Sector"),
    ("email",    "Email"),
    ("phone",    "Phone / LinkedIn"),
    ("conn",     "Connection Type"),
    ("channel",  "Preferred Channel"),
    ("purpose",  "Purpose"),
    ("owner",    "Committee Owner"),
    ("priority", "Priority"),
    ("status",   "Status"),
    ("lastdate", "Last Interaction Date"),
    ("lastnote", "Last Interaction / Response"),
    ("follow",   "Follow-up Needed"),
    ("next",     "Next Step"),
    ("nextdate", "Next Follow-up Date"),
    ("notes",    "Notes"),
]
FIELD_KEYS = [k for k, _ in DATA_FIELDS]
LABELS = {k: l for k, l in DATA_FIELDS}
 
# Stored columns in the Google Sheet: stable id + fields + timestamp.
CONTACT_COLUMNS = ["_id"] + FIELD_KEYS + ["created_at"]
 
OPTIONS = {
    "conn":     ["Alumni", "Personal Connection", "Faculty / Prof Referral", "Peer Referral",
                 "Cold Outreach", "Event / Conference Contact", "Existing Partner"],
    "channel":  ["Email", "LinkedIn", "Phone Call", "WhatsApp", "Warm Intro", "In-person"],
    "purpose":  ["Guest Session", "Case Competition", "Sponsorship", "Mentorship",
                 "Workshop", "Long-term Partnership"],
    "priority": ["High", "Medium", "Low"],
    "status":   ["Not Started", "Researching", "Contacted", "Awaiting Reply", "In Conversation",
                 "Call Scheduled", "Confirmed", "Declined", "On Hold"],
    "follow":   ["No", "Yes"],
}
 
# status -> (background, text) for pills. Colors chosen to read on both light and dark.
STATUS_STYLE = {
    "Confirmed":       ("#d9ead0", "#2f6b45"),
    "In Conversation": ("#d6e4f0", "#2f5a86"),
    "Call Scheduled":  ("#d6e4f0", "#2f5a86"),
    "Contacted":       ("#f3e6c4", "#866020"),
    "Awaiting Reply":  ("#f3e6c4", "#866020"),
    "Researching":     ("#e4e2d6", "#5f5b4d"),
    "Not Started":     ("#e4e2d6", "#5f5b4d"),
    "Declined":        ("#e4e2d6", "#5f5b4d"),
    "On Hold":         ("#e7ddef", "#6a5577"),
}
PRIORITY_COLOR = {"High": "#9c3a2b", "Medium": "#86601f", "Low": "#2f6b45"}
 
ROLES = ["viewer", "editor", "admin"]
ROLE_RANK = {"viewer": 1, "editor": 2, "admin": 3}
ROLE_HELP = {
    "viewer": "Can browse the tracker and export data.",
    "editor": "Can add, edit and delete contacts.",
    "admin":  "Can also manage who has access.",
}
 
 
def can_edit(role):
    return ROLE_RANK.get(role, 0) >= ROLE_RANK["editor"]
 
 
def can_admin(role):
    return ROLE_RANK.get(role, 0) >= ROLE_RANK["admin"]
 
 
def build_prompt(d):
    """Build the corporate-outreach research prompt from a dict of inputs."""
    company = d.get("company") or "[Company Name]"
    window = d.get("window") or "90"
    sender = d.get("sender") or "[Your Name]"
    email = d.get("email") or "[Official Committee Email]"
    context = d.get("context") or "None"
    return f"""You are an elite corporate partnership strategist and exceptionally strong B2B email writer for the Strategy & Consulting Committee, IIM Mumbai.
 
Your task is to produce THREE DISTINCT, highly personalized, send-ready corporate outreach emails for the target company.
 
Each email must propose a DIFFERENT strategic business idea. Do not simply rewrite the same idea in three different tones.
 
The emails are the primary deliverable. Keep research commentary extremely brief.
 
COMPANY INFORMATION
 
Target company:
{company}
 
Research window:
Previous {window} days ending today
 
Preferred business focus:
{d.get('focus', '')}
 
Preferred collaboration:
{d.get('collab', '')}
 
Optional strategic angle:
{context}
 
Writing voice:
{d.get('tone', '')}
 
Sender:
{sender}
 
Organization:
Strategy & Consulting Committee, IIM Mumbai
 
Email:
{email}
 
RESEARCH REQUIREMENTS
 
Before drafting, perform live web research. Examine recent and credible developments involving the target company, including: expansion plans and market-entry opportunities; business model and strategic initiatives; product launches and customer segments; relevant competitive or industry developments.
 
Prioritize official company announcements, credible news reports and verifiable public sources. For each material company-specific fact, verify its publication date and original URL. Distinguish verified developments from strategic hypotheses.
 
Never manufacture research findings, links, internal problems, financial metrics or company commitments. If credible developments are unavailable within the research window, acknowledge this briefly and use reliable existing company context. Do not present assumptions as company problems.
 
STRATEGIC IDEATION
 
Identify THREE genuinely different collaboration opportunities for the Strategy & Consulting Committee, IIM Mumbai. Each opportunity must have a distinct business question that students could investigate through a case competition or related corporate collaboration.
 
Possible directions: new customer segment or market expansion; growth strategy or customer retention; channel partnerships or go-to-market design; operations and unit economics; student-led research or campus pilots. Use only directions relevant to the company.
 
Rank the options on strategic relevance, credibility, feasibility and likelihood of earning a response. Mark the strongest as RECOMMENDED.
 
OUTPUT FORMAT
 
Output only the following sections. Do not write a long introduction. Do not include tables or detailed analysis.
 
RECOMMENDED — [Distinct strategic theme]
Subject: [Compelling subject line, maximum 11 words]
[Complete outreach email of 115-145 words, excluding the signature.]
Why this works: [One sentence, maximum 25 words.]
 
ALTERNATIVE — [Different strategic theme]
Subject: [Compelling subject line, maximum 11 words]
[Complete outreach email of 105-135 words, excluding the signature.]
Why this works: [One sentence, maximum 20 words.]
 
CREATIVE OPTION — [Third distinct strategic idea]
Subject: [Compelling subject line, maximum 11 words]
[Complete outreach email of 105-135 words, excluding the signature.]
Why this works: [One sentence, maximum 20 words.]
 
RESEARCH BASIS
No more than THREE concise bullets. Each: a verified company development or a clearly labeled strategic hypothesis; publication date where applicable; direct source URL for any factual claim. If nothing recent could be verified, say so explicitly.
 
EMAIL WRITING STANDARDS
 
The emails must sound like a thoughtful professional writing personally to this specific company. Avoid language that sounds mass-generated or artificial.
 
Never use: "I hope this email finds you well"; "Esteemed organization"; "Remarkable journey"; "Unlock synergies"; "What if India's brightest minds"; or similar exaggerated corporate language.
 
Start each email with a meaningful company-specific observation, business insight or relevant strategic question. Introduce the Strategy & Consulting Committee, IIM Mumbai naturally. Explain one specific, realistic collaboration concept. State the potential benefit to the company clearly, without exaggerated promises.
 
Each email should contain approximately four short, well-connected paragraphs. Do not include bullet points inside the emails. Use confident, conversational and professional English. The proposal should feel like a genuine collaboration, not a request for sponsorship money. End each email with a clear invitation to a 15-minute exploratory call next week, and offer to share a short concept note.
 
Address the email to "Dear [Name/Team]," unless an actual recipient is provided. Sign every email using the supplied sender details.
 
Do not invent committee participation figures, institutional endorsements, existing partnerships, contact names, company financial performance or confidential business challenges. Never embed citations inside the emails; put source links only in the Research Basis section.
 
The three emails MUST differ in the actual business opportunity they propose, not merely their vocabulary.
 
FINAL QUALITY REVIEW
 
Would each email still make sense if the company name were swapped for a competitor? If yes, sharpen the company-specific insight. Does the collaboration give a real reason to engage? If not, strengthen it. Would a busy decision-maker grasp the opportunity immediately? If not, cut words.
 
Deliver only the three polished email options, their brief justifications and the short Research Basis. Target roughly 550-650 words overall; the majority must be the emails."""
