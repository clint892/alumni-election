from flask import Flask, render_template, request, redirect, session
from tinydb import TinyDB, Query

app = Flask(__name__)
app.secret_key = "secret123"

db = TinyDB("database.json")

# Tables
voters = db.table("voters")
pending_voters = db.table("pending_voters")
candidates = db.table("candidates")
pending_candidates = db.table("pending_candidates")
admins = db.table("admins")
settings_table = db.table("settings")

# ----------------- INITIALIZATION -----------------
if not admins.all():
    admins.insert({"username": "admin", "password": "admin123"})

if not settings_table.all():
    settings_table.insert({"registration": True, "voting": False})

def get_settings():
    s = settings_table.all()
    return s[0]

def update_settings(key, value):
    settings_table.update({key: value}, doc_ids=[get_settings()["doc_id"]])

# ----------------- HOME -----------------
@app.route("/")
def home():
    s = get_settings()
    return render_template(
        "home.html",
        registration=s["registration"],
        voting=s["voting"],
        candidates=candidates.all()
    )

# ----------------- REGISTER -----------------
@app.route("/register", methods=["POST"])
def register():
    s = get_settings()
    if not s["registration"]:
        return "Registration is closed"
    name = request.form["name"]
    email = request.form["email"]

    if pending_voters.search(Query().email == email) or voters.search(Query().email == email):
        return "Already registered"

    pending_voters.insert({"name": name, "email": email})
    return "Registration sent for admin approval"

# ----------------- APPLY CANDIDATE -----------------
@app.route("/apply_candidate_page")
def apply_candidate_page():
    return render_template("apply_candidate.html")

@app.route("/apply_candidate", methods=["POST"])
def apply_candidate():
    name = request.form["name"]
    email = request.form["email"]
    position = request.form["position"]

    if pending_candidates.search(Query().email == email) or candidates.search(Query().email == email):
        return "Already applied"

    pending_candidates.insert({
        "name": name,
        "email": email,
        "position": position,
        "votes": 0
    })
    return "Candidate application sent for admin approval"

# ----------------- VOTE -----------------
@app.route("/vote", methods=["POST"])
def vote():
    s = get_settings()
    if not s["voting"]:
        return "Voting not started"

    email = request.form["email"]
    candidate_id = int(request.form["candidate_id"])

    voter_list = voters.search(Query().email == email)
    if not voter_list:
        return "You are not approved to vote"

    voter = voter_list[0]
    if voter.get("voted"):
        return "You already voted"

    c = candidates.get(doc_id=candidate_id)
    candidates.update({"votes": c["votes"] + 1}, doc_ids=[candidate_id])
    voters.update({"voted": True}, Query().email == email)

    return "Vote successful"

# ----------------- ADMIN LOGIN -----------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        admin_user = admins.search((Query().username == username) & (Query().password == password))
        if admin_user:
            session["admin"] = True
            return redirect("/dashboard")
        return "Invalid login"
    return render_template("admin_login.html")

# ----------------- DASHBOARD -----------------
@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/admin")

    s = get_settings()
    total_votes = sum(c["votes"] for c in candidates.all())
    candidate_list = candidates.all()
    for c in candidate_list:
        c["percentage"] = round((c["votes"]/total_votes*100) if total_votes else 0, 2)

    return render_template(
        "dashboard.html",
        registration=s["registration"],
        voting=s["voting"],
        pending_voters=pending_voters.all(),
        voters=voters.all(),
        pending_candidates=pending_candidates.all(),
        candidates=candidate_list,
        total_votes=total_votes
    )

# ----------------- TOGGLES -----------------
@app.route("/toggle_registration")
def toggle_registration():
    s = get_settings()
    update_settings("registration", not s["registration"])
    return redirect("/dashboard")

@app.route("/toggle_voting")
def toggle_voting():
    s = get_settings()
    update_settings("voting", not s["voting"])
    return redirect("/dashboard")

# ----------------- APPROVE VOTER -----------------
@app.route("/approve_voter/<int:id>")
def approve_voter(id):
    v = pending_voters.get(doc_id=id)
    if v:
        voters.insert({"name": v["name"], "email": v["email"], "voted": False})
        pending_voters.remove(doc_ids=[id])
    return redirect("/dashboard")

# ----------------- APPROVE CANDIDATE -----------------
@app.route("/approve_candidate/<int:id>")
def approve_candidate(id):
    c = pending_candidates.get(doc_id=id)
    if c:
        candidates.insert({"name": c["name"], "position": c["position"], "votes": 0})
        pending_candidates.remove(doc_ids=[id])
    return redirect("/dashboard")

# ----------------- DELETE CANDIDATE -----------------
@app.route("/delete_candidate/<int:id>")
def delete_candidate(id):
    candidates.remove(doc_ids=[id])
    return redirect("/dashboard")

# ----------------- RUN -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)