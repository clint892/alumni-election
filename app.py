from flask import Flask, render_template, request, redirect, session
from tinydb import TinyDB, Query

app = Flask(__name__)
app.secret_key = "supersecretkey"

db = TinyDB("database.json")

# Tables
voters_table = db.table("voters")
pending_voters_table = db.table("pending_voters")
candidates_table = db.table("candidates")
pending_candidates_table = db.table("pending_candidates")
admins_table = db.table("admins")
settings_table = db.table("settings")

# ----------------- INITIALIZATION -----------------
if not admins_table.all():
    admins_table.insert({"username": "admin", "password": "admin123"})

if not settings_table.all():
    settings_table.insert({"registration": True, "voting": False})

def get_settings():
    s = settings_table.all()
    return s[0]

def update_settings(key, value):
    settings_table.update({key: value}, doc_ids=[get_settings().doc_id])

# ----------------- HOME -----------------
@app.route("/")
def home():
    s = get_settings()
    return render_template(
        "home.html",
        registration=s["registration"],
        voting=s["voting"],
        candidates=candidates_table.all()
    )

# ----------------- REGISTER -----------------
@app.route("/register", methods=["POST"])
def register():
    s = get_settings()
    if not s["registration"]:
        return "Registration is closed"

    name = request.form["name"]
    email = request.form["email"]

    if pending_voters_table.search(Query().email == email) or voters_table.search(Query().email == email):
        return "Already registered"

    pending_voters_table.insert({"name": name, "email": email})
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

    if pending_candidates_table.search(Query().email == email) or candidates_table.search(Query().email == email):
        return "Already applied"

    pending_candidates_table.insert({
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

    voter_list = voters_table.search(Query().email == email)
    if not voter_list:
        return "You are not approved to vote"

    voter = voter_list[0]
    if voter.get("voted"):
        return "You already voted"

    c = candidates_table.get(doc_id=candidate_id)
    candidates_table.update({"votes": c["votes"] + 1}, doc_ids=[candidate_id])
    voters_table.update({"voted": True}, Query().email == email)

    return "Vote successful"

# ----------------- ADMIN LOGIN -----------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        admin_user = admins_table.search((Query().username == username) & (Query().password == password))
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
    total_votes = sum(c["votes"] for c in candidates_table.all())
    candidate_list = candidates_table.all()
    for c in candidate_list:
        c["percentage"] = round((c["votes"]/total_votes*100) if total_votes else 0, 2)

    return render_template(
        "dashboard.html",
        registration=s["registration"],
        voting=s["voting"],
        pending_voters=pending_voters_table.all(),
        voters=voters_table.all(),
        pending_candidates=pending_candidates_table.all(),
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

# ----------------- APPROVE/DELETE -----------------
@app.route("/approve_voter/<int:id>")
def approve_voter(id):
    v = pending_voters_table.get(doc_id=id)
    if v:
        voters_table.insert({"name": v["name"], "email": v["email"], "voted": False})
        pending_voters_table.remove(doc_ids=[id])
    return redirect("/dashboard")

@app.route("/approve_candidate/<int:id>")
def approve_candidate(id):
    c = pending_candidates_table.get(doc_id=id)
    if c:
        candidates_table.insert({"name": c["name"], "position": c["position"], "votes": 0})
        pending_candidates_table.remove(doc_ids=[id])
    return redirect("/dashboard")

@app.route("/delete_candidate/<int:id>")
def delete_candidate(id):
    candidates_table.remove(doc_ids=[id])
    return redirect("/dashboard")

# ----------------- RUN -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)