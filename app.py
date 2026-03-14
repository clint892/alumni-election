from flask import Flask, render_template, request, redirect, url_for
from tinydb import TinyDB, Query
import uuid
import os

app = Flask(__name__)

# -----------------------------
# DATABASES
# -----------------------------
voters_table = TinyDB("voters.json")
candidates_table = TinyDB("candidates.json")
admins_table = TinyDB("admins.json")
settings_table = TinyDB("settings.json")

# -----------------------------
# INITIAL DATA
# -----------------------------
if not settings_table.all():
    settings_table.insert({
        "registration_open": True,
        "voting_open": False
    })

if not admins_table.all():
    admins_table.insert({
        "username": "admin",
        "password": "admin"
    })

# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def home():
    settings = settings_table.all()[0]
    voters = voters_table.all()
    candidates = candidates_table.all()

    return render_template(
        "home.html",
        voters=voters,
        candidates=candidates,
        registration_open=settings["registration_open"],
        voting_open=settings["voting_open"]
    )

# -----------------------------
# REGISTER VOTER
# -----------------------------
@app.route("/register", methods=["POST"])
def register():

    settings = settings_table.all()[0]
    if not settings["registration_open"]:
        return "Registration closed"

    name = request.form["name"]
    email = request.form["email"]

    Voter = Query()

    if voters_table.get(Voter.email == email):
        return "Email already registered"

    voters_table.insert({
        "name": name,
        "email": email,
        "approved": False,
        "confirmed": False,
        "token": ""
    })

    return redirect(url_for("home"))

# -----------------------------
# ADMIN LOGIN
# -----------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        Admin = Query()
        admin = admins_table.get(
            (Admin.username == username) &
            (Admin.password == password)
        )

        if admin:
            return redirect(url_for("dashboard"))

        return "Invalid login"

    return render_template("admin_login.html")

# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard")
def dashboard():

    settings = settings_table.all()[0]
    voters = voters_table.all()

    pending_voters = [
        v for v in voters if not v["approved"]
    ]

    candidates = candidates_table.all()

    return render_template(
        "dashboard.html",
        voters=voters,
        pending_voters=pending_voters,
        candidates=candidates,
        registration_open=settings["registration_open"],
        voting_open=settings["voting_open"]
    )

# -----------------------------
# TOGGLE REGISTRATION
# -----------------------------
@app.route("/toggle_registration")
def toggle_registration():

    settings = settings_table.all()[0]

    settings_table.update(
        {"registration_open": not settings["registration_open"]},
        doc_ids=[1]
    )

    return redirect(url_for("dashboard"))

# -----------------------------
# TOGGLE VOTING
# -----------------------------
@app.route("/toggle_voting")
def toggle_voting():

    settings = settings_table.all()[0]

    # ensure all voters approved + confirmed
    pending = [
        v for v in voters_table.all()
        if not (v.get("approved") and v.get("confirmed"))
    ]

    if pending and not settings["voting_open"]:
        return "Cannot start voting. Some voters not confirmed."

    settings_table.update(
        {"voting_open": not settings["voting_open"]},
        doc_ids=[1]
    )

    return redirect(url_for("dashboard"))

# -----------------------------
# APPROVE VOTER
# -----------------------------
@app.route("/approve_voter/<int:voter_id>")
def approve_voter(voter_id):

    voter = voters_table.get(doc_id=voter_id)

    if voter:

        token = str(uuid.uuid4())

        voters_table.update({
            "approved": True,
            "token": token
        }, doc_ids=[voter_id])

        # In real system send email
        print("Confirmation link:")
        print(f"/confirm/{token}")

    return redirect(url_for("dashboard"))

# -----------------------------
# CONFIRM EMAIL
# -----------------------------
@app.route("/confirm/<token>")
def confirm(token):

    Voter = Query()

    voter = voters_table.get(Voter.token == token)

    if voter:

        voters_table.update(
            {"confirmed": True},
            doc_ids=[voter.doc_id]
        )

        return "Registration confirmed. You can now vote."

    return "Invalid confirmation link"

# -----------------------------
# ADD CANDIDATE
# -----------------------------
@app.route("/add_candidate", methods=["POST"])
def add_candidate():

    name = request.form["name"]

    candidates_table.insert({
        "name": name,
        "votes": 0
    })

    return redirect(url_for("dashboard"))

# -----------------------------
# VOTE
# -----------------------------
@app.route("/vote", methods=["POST"])
def vote():

    settings = settings_table.all()[0]

    if not settings["voting_open"]:
        return "Voting closed"

    email = request.form["email"]
    candidate_id = int(request.form["candidate_id"])

    Voter = Query()

    voter = voters_table.get(
        (Voter.email == email) &
        (Voter.confirmed == True)
    )

    if not voter:
        return "You are not allowed to vote"

    candidate = candidates_table.get(doc_id=candidate_id)

    if candidate:

        candidates_table.update(
            {"votes": candidate["votes"] + 1},
            doc_ids=[candidate_id]
        )

    return redirect(url_for("home"))

# -----------------------------
# RUN SERVER (RENDER FIX)
# -----------------------------
if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )