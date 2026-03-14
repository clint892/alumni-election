from flask import Flask, render_template, request, redirect, url_for
from tinydb import TinyDB, Query
import os, uuid, smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# -----------------------------
# TinyDB setup
# -----------------------------
db = TinyDB("db.json")
voters_table = db.table("voters")
candidates_table = db.table("candidates")
admins_table = db.table("admins")
settings_table = db.table("settings")

# --- Initialize settings ---
if len(settings_table) == 0:
    settings_table.insert({"registration_open": True, "voting_open": False})

# --- Initialize default admin ---
if len(admins_table) == 0:
    admins_table.insert({"username": "admin", "password": "admin123"})

# -----------------------------
# Email setup (Gmail example)
# -----------------------------
EMAIL_ADDRESS = "your-email@gmail.com"
EMAIL_PASSWORD = "your-app-password"  # Gmail App Password

def send_approval_email(to_email, token):
    link = f"https://<your-app>.onrender.com/confirm_registration/{token}"
    msg = MIMEText(f"Click this link to confirm your registration:\n{link}")
    msg["Subject"] = "Alumni Election Registration Confirmation"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    settings = settings_table.all()[0]
    registration_open = settings["registration_open"]
    voting_open = settings["voting_open"]

    return render_template(
        "home.html",
        voters=voters_table.all(),
        candidates=candidates_table.all(),
        registration_open=registration_open,
        voting_open=voting_open
    )

# Voter registration
@app.route("/register", methods=["POST"])
def register():
    settings = settings_table.all()[0]
    if not settings["registration_open"]:
        return "Registration is closed", 403

    name = request.form["name"]
    email = request.form["email"]
    Voter = Query()
    if not voters_table.search(Voter.email == email):
        voters_table.insert({
            "name": name,
            "email": email,
            "approved": False,
            "confirmed": False
        })
    return redirect(url_for("home"))

# Confirm registration via email link
@app.route("/confirm_registration/<token>")
def confirm_registration(token):
    Voter = Query()
    voter = voters_table.get(Voter.token == token)
    if voter:
        voters_table.update({"confirmed": True}, doc_ids=[voter.doc_id])
        return "Your registration is confirmed! You can now vote."
    return "Invalid or expired link"

# Voting
@app.route("/vote", methods=["POST"])
def vote():
    settings = settings_table.all()[0]
    if not settings["voting_open"]:
        return "Voting is closed", 403

    email = request.form["email"]
    candidate_id = int(request.form["candidate_id"])
    Voter = Query()
    voter = voters_table.get((Voter.email == email) & (Voter.confirmed == True))
    if not voter:
        return "You are not eligible to vote", 403

    candidate = candidates_table.get(doc_id=candidate_id)
    if candidate:
        candidates_table.update({"votes": candidate["votes"] + 1}, doc_ids=[candidate_id])
    return redirect(url_for("home"))

# Admin login
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        Admin = Query()
        admin = admins_table.get((Admin.username == username) & (Admin.password == password))
        if admin:
            return redirect(url_for("dashboard"))
    return render_template("admin_login.html")

# Admin dashboard
@app.route("/dashboard")
def dashboard():
    settings = settings_table.all()[0]
    pending_voters = [v for v in voters_table.all() if not v.get("approved", False)]
    return render_template(
        "dashboard.html",
        voters=voters_table.all(),
        pending_voters=pending_voters,
        candidates=candidates_table.all(),
        registration_open=settings["registration_open"],
        voting_open=settings["voting_open"]
    )

# Approve voter
@app.route("/approve_voter/<int:voter_id>")
def approve_voter(voter_id):
    voter = voters_table.get(doc_id=voter_id)
    if voter:
        token = str(uuid.uuid4())
        voters_table.update({"approved": True, "token": token}, doc_ids=[voter_id])
        send_approval_email(voter["email"], token)
    return redirect(url_for("dashboard"))

# Toggle registration
@app.route("/toggle_registration")
def toggle_registration():
    settings = settings_table.all()[0]
    settings_table.update({"registration_open": not settings["registration_open"]}, doc_ids=[1])
    return redirect(url_for("dashboard"))

# Toggle voting
@app.route("/toggle_voting")
def toggle_voting():
    settings = settings_table.all()[0]
    settings_table.update({"voting_open": not settings["voting_open"]}, doc_ids=[1])
    return redirect(url_for("dashboard"))

# Add candidate
@app.route("/add_candidate", methods=["POST"])
def add_candidate():
    name = request.form["name"]
    if name:
        candidates_table.insert({"name": name, "votes": 0})
    return redirect(url_for("dashboard"))

# Add admin
@app.route("/add_admin", methods=["POST"])
def add_admin():
    username = request.form["username"]
    password = request.form["password"]
    if username and password:
        Admin = Query()
        if not admins_table.search(Admin.username == username):
            admins_table.insert({"username": username, "password": password})
    return redirect(url_for("dashboard"))

# -----------------------------
# Run the app
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)