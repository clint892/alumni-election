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

User = Query()

# initialize admin
if not admins.all():
    admins.insert({"username":"admin","password":"admin123"})

# initialize settings
if not settings.all():
    settings.insert({"registration":True,"voting":False})


def get_settings():
    return settings.all()[0]


# HOME
@app.route("/")
def home():
    s = get_settings()
    return render_template(
        "home.html",
        registration=s["registration"],
        voting=s["voting"],
        candidates=candidates.all()
    )


# REGISTER
@app.route("/register",methods=["POST"])
def register():

    if not get_settings()["registration"]:
        return "Registration closed"

    name=request.form["name"]
    email=request.form["email"]

    if voters.search(User.email==email) or pending_voters.search(User.email==email):
        return "Already registered"

    pending_voters.insert({
        "name":name,
        "email":email,
        "voted":False
    })

    return "Registration sent for approval"


# APPLY CANDIDATE PAGE
@app.route("/apply")
def apply():
    return render_template("apply_candidate.html")


# APPLY CANDIDATE
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

    return redirect("/")


# VOTE
@app.route("/vote",methods=["POST"])
def vote():

    if not get_settings()["voting"]:
        return "Voting not started"

    email=request.form["email"]
    cid=int(request.form["candidate_id"])

    voter=voters.search(User.email==email)

    if not voter:
        return "Not approved voter"

    if voter[0]["voted"]:
        return "You already voted"

    candidate=candidates.get(doc_id=cid)

    candidates.update(
        {"votes":candidate["votes"]+1},
        doc_ids=[cid]
    )

    voters.update({"voted":True},User.email==email)

    return redirect("/")


# ADMIN LOGIN
@app.route("/admin",methods=["GET","POST"])
def admin():

    if request.method=="POST":

        username=request.form["username"]
        password=request.form["password"]

        admin=admins.search(
            (User.username==username)&
            (User.password==password)
        )

        if admin:
            session["admin"]=True
            return redirect("/dashboard")

        return "Wrong login"

    return render_template("admin_login.html")


# DASHBOARD
@app.route("/dashboard")
def dashboard():

    if not session.get("admin"):
        return redirect("/admin")

    s=get_settings()

    total_votes=sum(c["votes"] for c in candidates.all())

    candidate_list=candidates.all()

    for c in candidate_list:
        if total_votes==0:
            c["percent"]=0
        else:
            c["percent"]=round((c["votes"]/total_votes)*100,2)

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


# APPROVE VOTER
@app.route("/approve_voter/<id>")
def approve_voter(id):

    v=pending_voters.get(doc_id=int(id))

    voters.insert({
        "name":v["name"],
        "email":v["email"],
        "voted":False
    })

    pending_voters.remove(doc_ids=[int(id)])

    return redirect("/dashboard")


# APPROVE CANDIDATE
@app.route("/approve_candidate/<id>")
def approve_candidate(id):

    c=pending_candidates.get(doc_id=int(id))

    candidates.insert({
        "name":c["name"],
        "position":c["position"],
        "votes":0
    })

    pending_candidates.remove(doc_ids=[int(id)])

    return redirect("/dashboard")


# DELETE CANDIDATE
@app.route("/delete_candidate/<id>")
def delete_candidate(id):

    candidates.remove(doc_ids=[int(id)])

    return redirect("/dashboard")


# TOGGLE REGISTRATION
@app.route("/toggle_registration")
def toggle_registration():

    s=get_settings()

    settings.update(
        {"registration":not s["registration"]},
        doc_ids=[1]
    )

    return redirect("/dashboard")


# TOGGLE VOTING
@app.route("/toggle_voting")
def toggle_voting():

    s=get_settings()

    settings.update(
        {"voting":not s["voting"]},
        doc_ids=[1]
    )

    return redirect("/dashboard")


# LOGOUT
@app.route("/logout")
def logout():
    session.pop("admin")
    return redirect("/admin")


if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)