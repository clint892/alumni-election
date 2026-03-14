from flask import Flask, render_template, request, redirect, session
from tinydb import TinyDB, Query

app = Flask(__name__)
app.secret_key = "secret123"

db = TinyDB("database.json")

voters = db.table("voters")
pending_voters = db.table("pending_voters")
candidates = db.table("candidates")
pending_candidates = db.table("pending_candidates")
admins = db.table("admins")
settings = db.table("settings")

# default admin
if not admins.all():
    admins.insert({"username":"admin","password":"admin123"})

# default settings
if not settings.all():
    settings.insert({"registration":True,"voting":False})

def get_settings():
    return settings.all()[0]

def update_settings(key,value):
    s=settings.all()[0]
    s[key]=value
    settings.update(s,doc_ids=[1])

# ================= HOME =================

@app.route("/")
def home():

    s=get_settings()

    return render_template(
        "home.html",
        registration=s["registration"],
        voting=s["voting"],
        candidates=candidates.all()
    )

# ================= REGISTER =================

@app.route("/register",methods=["POST"])
def register():

    s=get_settings()

    if not s["registration"]:
        return "Registration closed"

    name=request.form["name"]
    email=request.form["email"]

    pending_voters.insert({
        "name":name,
        "email":email
    })

    return "Registration sent for approval"

# ================= APPLY CANDIDATE =================

@app.route("/apply_candidate_page")
def apply_candidate_page():
    return render_template("apply_candidate.html")

@app.route("/apply_candidate",methods=["POST"])
def apply_candidate():

    name=request.form["name"]
    email=request.form["email"]
    position=request.form["position"]

    pending_candidates.insert({
        "name":name,
        "email":email,
        "position":position,
        "votes":0
    })

    return "Application submitted"

# ================= VOTE =================

@app.route("/vote",methods=["POST"])
def vote():

    s=get_settings()

    if not s["voting"]:
        return "Voting not started"

    email=request.form["email"]
    candidate_id=int(request.form["candidate_id"])

    voter=voters.search(Query().email==email)

    if not voter:
        return "You are not approved to vote"

    voter=voter[0]

    if voter.get("voted"):
        return "You already voted"

    c=candidates.get(doc_id=candidate_id)

    candidates.update(
        {"votes":c["votes"]+1},
        doc_ids=[candidate_id]
    )

    voters.update({"voted":True},Query().email==email)

    return "Vote successful"

# ================= ADMIN LOGIN =================

@app.route("/admin",methods=["GET","POST"])
def admin():

    if request.method=="POST":

        username=request.form["username"]
        password=request.form["password"]

        admin=admins.search(
            (Query().username==username) &
            (Query().password==password)
        )

        if admin:
            session["admin"]=True
            return redirect("/dashboard")

        return "Invalid login"

    return render_template("admin_login.html")

# ================= DASHBOARD =================

@app.route("/dashboard")
def dashboard():

    if not session.get("admin"):
        return redirect("/admin")

    s=get_settings()

    total_votes=sum(c["votes"] for c in candidates.all())

    return render_template(
        "dashboard.html",
        registration=s["registration"],
        voting=s["voting"],
        pending_voters=pending_voters.all(),
        voters=voters.all(),
        pending_candidates=pending_candidates.all(),
        candidates=candidates.all(),
        total_votes=total_votes
    )

# ================= TOGGLES =================

@app.route("/toggle_registration")
def toggle_registration():

    s=get_settings()

    update_settings("registration",not s["registration"])

    return redirect("/dashboard")

@app.route("/toggle_voting")
def toggle_voting():

    s=get_settings()

    update_settings("voting",not s["voting"])

    return redirect("/dashboard")

# ================= APPROVE VOTER =================

@app.route("/approve_voter/<int:id>")
def approve_voter(id):

    voter=pending_voters.get(doc_id=id)

    voters.insert({
        "name":voter["name"],
        "email":voter["email"],
        "voted":False
    })

    pending_voters.remove(doc_ids=[id])

    return redirect("/dashboard")

# ================= APPROVE CANDIDATE =================

@app.route("/approve_candidate/<int:id>")
def approve_candidate(id):

    c=pending_candidates.get(doc_id=id)

    candidates.insert({
        "name":c["name"],
        "position":c["position"],
        "votes":0
    })

    pending_candidates.remove(doc_ids=[id])

    return redirect("/dashboard")

# ================= RUN =================

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)