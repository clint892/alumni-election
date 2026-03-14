from flask import Flask, render_template, request, redirect, url_for, flash
from tinydb import TinyDB, Query
import uuid

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Databases
voters = TinyDB("voters.json")
pending_voters = TinyDB("pending_voters.json")
candidates = TinyDB("candidates.json")
pending_candidates = TinyDB("pending_candidates.json")
admins = TinyDB("admins.json")
settings = TinyDB("settings.json")

# Default admin
if not admins.all():
    admins.insert({"username":"admin","password":"admin123"})

# Default settings
if not settings.all():
    settings.insert({"registration_open": True, "voting_open": False})

def get_setting(key):
    return settings.all()[0].get(key, False)

def set_setting(key, value):
    s = settings.all()[0]
    s[key] = value
    settings.update(s, doc_ids=[1])

# ------------------ ROUTES ------------------

@app.route("/")
def home():
    return render_template(
        "home.html",
        registration_open=get_setting("registration_open"),
        voting_open=get_setting("voting_open"),
        candidates=candidates.all()
    )

# ---------- Voter Registration ----------
@app.route("/register", methods=["POST"])
def register():
    if not get_setting("registration_open"):
        flash("Registration is closed!")
        return redirect(url_for("home"))

    name = request.form["name"].strip()
    email = request.form["email"].strip()

    # Check if already registered
    if any(v["email"] == email for v in voters.all()) or any(v["email"] == email for v in pending_voters.all()):
        flash("You are already registered or pending approval.")
        return redirect(url_for("home"))

    # Generate verification token (for email confirmation later)
    token = str(uuid.uuid4())

    pending_voters.insert({
        "name": name,
        "email": email,
        "token": token
    })

    flash("Registration submitted. Waiting for admin approval.")
    return redirect(url_for("home"))

# ---------- Voting ----------
@app.route("/vote", methods=["POST"])
def vote():
    if not get_setting("voting_open"):
        flash("Voting is not open yet!")
        return redirect(url_for("home"))

    email = request.form["email"].strip()
    candidate_id = int(request.form["candidate_id"])

    # Check if voter exists and approved
    voter = next((v for v in voters.all() if v["email"] == email), None)
    if not voter:
        flash("You are not an approved voter.")
        return redirect(url_for("home"))

    # Check if already voted
    if voter.get("voted"):
        flash("You have already voted!")
        return redirect(url_for("home"))

    # Register vote
    c = candidates.get(doc_id=candidate_id)
    candidates.update({"votes": c.get("votes", 0) + 1}, doc_ids=[candidate_id])
    voters.update({"voted": True}, doc_ids=[voter.doc_id])

    flash("Vote recorded successfully!")
    return redirect(url_for("home"))

# ---------- Candidate Application ----------
@app.route("/apply_candidate_page")
def apply_candidate_page():
    return render_template("apply_candidate.html")

@app.route("/apply_candidate", methods=["POST"])
def apply_candidate():
    name = request.form["name"].strip()
    email = request.form["email"].strip()
    position = request.form["position"].strip()

    # Check if already applied
    if any(c["email"] == email for c in candidates.all()) or any(c["email"] == email for c in pending_candidates.all()):
        flash("You have already applied or approved.")
        return redirect(url_for("home"))

    pending_candidates.insert({
        "name": name,
        "email": email,
        "position": position,
        "votes": 0
    })

    flash("Application submitted. Waiting for admin approval.")
    return redirect(url_for("home"))

# ---------- Admin Login ----------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        admin = next((a for a in admins.all() if a["username"] == username and a["password"] == password), None)
        if admin:
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid admin credentials.")
            return redirect(url_for("admin_login"))
    return render_template("admin_login.html")

# ---------- Admin Dashboard ----------
@app.route("/dashboard")
def dashboard():
    return render_template(
        "dashboard.html",
        registration_open=get_setting("registration_open"),
        voting_open=get_setting("voting_open"),
        pending_voters=pending_voters.all(),
        candidates=candidates.all(),
        pending_candidates=pending_candidates.all()
    )

# ---------- Toggle Registration ----------
@app.route("/toggle_registration")
def toggle_registration():
    set_setting("registration_open", not get_setting("registration_open"))
    return redirect(url_for("dashboard"))

# ---------- Toggle Voting ----------
@app.route("/toggle_voting")
def toggle_voting():
    set_setting("voting_open", not get_setting("voting_open"))
    return redirect(url_for("dashboard"))

# ---------- Approve Voter ----------
@app.route("/approve_voter/<int:doc_id>")
def approve_voter(doc_id):
    voter = pending_voters.get(doc_id=doc_id)
    if voter:
        voters.insert({"name": voter["name"], "email": voter["email"], "voted": False})
        pending_voters.remove(doc_ids=[doc_id])
        flash(f"{voter['name']} approved.")
    return redirect(url_for("dashboard"))

# ---------- Add Candidate ----------
@app.route("/add_candidate", methods=["POST"])
def add_candidate():
    name = request.form["name"].strip()
    position = request.form["position"].strip()
    candidates.insert({"name": name, "position": position, "votes": 0})
    flash(f"Candidate {name} added.")
    return redirect(url_for("dashboard"))

# ---------- Approve Candidate ----------
@app.route("/approve_candidate/<int:doc_id>")
def approve_candidate(doc_id):
    c = pending_candidates.get(doc_id=doc_id)
    if c:
        candidates.insert({"name": c["name"], "position": c["position"], "votes": 0})
        pending_candidates.remove(doc_ids=[doc_id])
        flash(f"Candidate {c['name']} approved.")
    return redirect(url_for("dashboard"))

# ---------- Delete Candidate ----------
@app.route("/delete_candidate/<int:doc_id>")
def delete_candidate(doc_id):
    candidates.remove(doc_ids=[doc_id])
    pending_candidates.remove(doc_ids=[doc_id])
    flash("Candidate removed.")
    return redirect(url_for("dashboard"))

# ---------- Results Page ----------
@app.route("/results")
def results():
    total_votes = sum(c.get("votes",0) for c in candidates.all())
    results_list = []

    for c in candidates.all():
        percent = (c.get("votes",0)/total_votes*100) if total_votes>0 else 0
        results_list.append({
            "name": c["name"],
            "position": c["position"],
            "votes": c.get("votes",0),
            "percent": round(percent,2)
        })
    return render_template("results.html", results=results_list)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)