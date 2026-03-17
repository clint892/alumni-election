import os
import sqlite3
from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = "secret123"

DATABASE = "election.db"


# ---------------- DB ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- HOME ----------------

@app.route("/")
def home():

    db = get_db()

    settings = db.execute("SELECT * FROM settings").fetchone()

    candidates = db.execute(
        "SELECT * FROM candidates WHERE approved=1"
    ).fetchall()

    positions = {}

    for c in candidates:
        if c["position"] not in positions:
            positions[c["position"]] = []
        positions[c["position"]].append(c)

    return render_template(
        "home.html",
        positions=positions,
        voting=settings["voting"],
        registration=settings["registration"]
    )


# ---------------- REGISTER ----------------

@app.route("/register", methods=["POST"])
def register():

    name = request.form["name"]
    email = request.form["email"]

    db = get_db()

    try:
        db.execute(
            "INSERT INTO voters(name,email) VALUES(?,?)",
            (name, email)
        )
        db.commit()
    except:
        return "Already registered"

    return "Waiting for admin approval"


# ---------------- APPLY ----------------

@app.route("/apply")
def apply():
    return render_template("apply_candidate.html")


@app.route("/apply_candidate", methods=["POST"])
def apply_candidate():

    name = request.form["name"]
    position = request.form["position"]

    db = get_db()

    db.execute(
        "INSERT INTO candidates(name,position) VALUES(?,?)",
        (name, position)
    )

    db.commit()

    return "Application sent for approval"


# ---------------- VOTE ----------------

@app.route("/vote", methods=["POST"])
def vote():

    email = request.form["email"]
    db = get_db()

    # check voter
    voter = db.execute(
        "SELECT * FROM voters WHERE email=? AND approved=1",
        (email,)
    ).fetchone()

    if not voter:
        return "Not approved"

    # check voting ON
    settings = db.execute("SELECT * FROM settings").fetchone()
    if settings["voting"] == 0:
        return "Voting is closed"

    # vote per position
    for key in request.form:

        if key.startswith("position_"):

            position = key.replace("position_", "")
            candidate_id = request.form[key]

            # prevent duplicate vote per position
            existing = db.execute(
                "SELECT * FROM votes WHERE voter_email=? AND position=?",
                (email, position)
            ).fetchone()

            if existing:
                continue

            db.execute(
                "INSERT INTO votes(voter_email,position,candidate_id) VALUES(?,?,?)",
                (email, position, candidate_id)
            )

    db.commit()

    return "Vote submitted successfully"


# ---------------- ADMIN LOGIN ----------------

@app.route("/admin", methods=["GET","POST"])
def admin():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        db = get_db()

        admin = db.execute(
            "SELECT * FROM admin WHERE username=? AND password=?",
            (username,password)
        ).fetchone()

        if admin:
            session["admin"] = True
            return redirect("/dashboard")

        return "Wrong login"

    return render_template("admin_login.html")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if not session.get("admin"):
        return redirect("/admin")

    db = get_db()

    voters = db.execute(
        "SELECT * FROM voters WHERE approved=0"
    ).fetchall()

    candidates = db.execute(
        "SELECT * FROM candidates WHERE approved=0"
    ).fetchall()

    approved = db.execute(
        "SELECT * FROM candidates WHERE approved=1"
    ).fetchall()

    settings = db.execute("SELECT * FROM settings").fetchone()

    # RESULTS
    results = {}

    for c in approved:

        votes = db.execute(
            "SELECT COUNT(*) as total FROM votes WHERE candidate_id=?",
            (c["id"],)
        ).fetchone()["total"]

        if c["position"] not in results:
            results[c["position"]] = []

        results[c["position"]].append({
            "name": c["name"],
            "votes": votes
        })

    # percentages
    for pos in results:

        total = sum(x["votes"] for x in results[pos])

        for r in results[pos]:
            r["percent"] = 0 if total == 0 else round((r["votes"]/total)*100,2)

    return render_template(
        "dashboard.html",
        voters=voters,
        candidates=candidates,
        results=results,
        voting=settings["voting"],
        registration=settings["registration"]
    )


# ---------------- APPROVALS ----------------

@app.route("/approve_voter/<id>")
def approve_voter(id):

    db = get_db()
    db.execute("UPDATE voters SET approved=1 WHERE id=?", (id,))
    db.commit()

    return redirect("/dashboard")


@app.route("/approve_candidate/<id>")
def approve_candidate(id):

    db = get_db()
    db.execute("UPDATE candidates SET approved=1 WHERE id=?", (id,))
    db.commit()

    return redirect("/dashboard")


# ---------------- TOGGLES ----------------

@app.route("/toggle_voting")
def toggle_voting():

    db = get_db()

    current = db.execute(
        "SELECT voting FROM settings"
    ).fetchone()["voting"]

    db.execute(
        "UPDATE settings SET voting=?",
        (0 if current else 1,)
    )

    db.commit()

    return redirect("/dashboard")


@app.route("/toggle_registration")
def toggle_registration():

    db = get_db()

    current = db.execute(
        "SELECT registration FROM settings"
    ).fetchone()["registration"]

    db.execute(
        "UPDATE settings SET registration=?",
        (0 if current else 1,)
    )

    db.commit()

    return redirect("/dashboard")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/admin")


# ---------------- RUN ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)