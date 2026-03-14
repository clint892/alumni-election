from flask import Flask, render_template, request, redirect, url_for, session
from tinydb import TinyDB, Query
import uuid

app = Flask(__name__)
app.secret_key = "supersecretkey"

# TinyDB setup
db = TinyDB("db.json")
voters = db.table("voters")
candidates = db.table("candidates")
admins = db.table("admins")

# Initialize admin if not exists
if not admins.all():
    admins.insert({"username": "admin", "password": "admin123"})

# Election states
election = {"registration_open": True, "voting_open": False}

# ---------------- VOTER ROUTES ----------------

@app.route("/")
def home():
    return render_template("home.html", registration_open=election["registration_open"])

@app.route("/register", methods=["POST"])
def register():
    name = request.form["name"]
    email = request.form["email"]
    # Check if already exists
    if voters.search(Query().email == email):
        return "Email already registered! Please use another email."
    # Add as pending
    voters.insert({"id": str(uuid.uuid4()), "name": name, "email": email, "approved": False, "voted": False})
    return "Registration submitted! Wait for admin approval and email confirmation."

# ---------------- ADMIN ROUTES ----------------

@app.route("/admin", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = admins.search((Query().username==username) & (Query().password==password))
        if user:
            session["admin"] = username
            return redirect(url_for("dashboard"))
        return "Invalid login"
    return render_template("admin_login.html")

@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    pending_voters = voters.search(Query().approved == False)
    approved_voters = voters.search(Query().approved == True)
    pending_candidates = candidates.search(Query().approved == False)
    all_candidates = candidates.all()
    total_votes = sum(c.get("votes",0) for c in all_candidates)
    return render_template("dashboard.html", 
                           pending_voters=pending_voters,
                           approved_voters=approved_voters,
                           pending_candidates=pending_candidates,
                           candidates=all_candidates,
                           registration_open=election["registration_open"],
                           voting_open=election["voting_open"],
                           total_votes=total_votes)

# Admin actions
@app.route("/approve_voter/<voter_id>")
def approve_voter(voter_id):
    if "admin" not in session: return redirect(url_for("admin_login"))
    voters.update({"approved": True}, Query().id == voter_id)
    return redirect(url_for("dashboard"))

@app.route("/reject_voter/<voter_id>")
def reject_voter(voter_id):
    if "admin" not in session: return redirect(url_for("admin_login"))
    voters.remove(Query().id == voter_id)
    return redirect(url_for("dashboard"))

@app.route("/toggle_registration")
def toggle_registration():
    if "admin" not in session: return redirect(url_for("admin_login"))
    election["registration_open"] = not election["registration_open"]
    return redirect(url_for("dashboard"))

@app.route("/toggle_voting")
def toggle_voting():
    if "admin" not in session: return redirect(url_for("admin_login"))
    election["voting_open"] = not election["voting_open"]
    return redirect(url_for("dashboard"))

@app.route("/approve_candidate/<candidate_id>")
def approve_candidate(candidate_id):
    if "admin" not in session: return redirect(url_for("admin_login"))
    candidates.update({"approved": True}, Query().id == candidate_id)
    return redirect(url_for("dashboard"))

@app.route("/reject_candidate/<candidate_id>")
def reject_candidate(candidate_id):
    if "admin" not in session: return redirect(url_for("admin_login"))
    candidates.remove(Query().id == candidate_id)
    return redirect(url_for("dashboard"))

# ---------------- CANDIDATE ROUTES ----------------

@app.route("/apply_candidate", methods=["POST"])
def apply_candidate():
    name = request.form["name"]
    position = request.form.get("position","")
    candidates.insert({"id": str(uuid.uuid4()), "name": name, "position": position, "approved": False, "votes":0})
    return "Candidate application submitted! Wait for admin approval."

# ---------------- VOTING ROUTES ----------------

@app.route("/vote/<candidate_id>/<voter_id>")
def vote(candidate_id,voter_id):
    if not election["voting_open"]:
        return "Voting is closed"
    voter = voters.get(doc_id=int(voter_id))
    if voter["voted"]:
        return "You have already voted"
    candidates.update({"votes": Query().votes + 1}, Query().id==candidate_id)
    voters.update({"voted": True}, Query().id==voter_id)
    return "Vote recorded!"

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)