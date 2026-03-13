from flask import Flask, render_template, request, redirect, url_for
from tinydb import TinyDB, Query
import os

app = Flask(__name__)

# TinyDB database
db = TinyDB("db.json")
voters_table = db.table("voters")
candidates_table = db.table("candidates")

# Voting status
voting_open = False

# Admin credentials (hardcoded for now)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


@app.route("/")
def home():
    return render_template(
        "home.html",
        voters=voters_table.all(),
        voting_open=voting_open,
        candidates=candidates_table.all()
    )


@app.route("/register", methods=["POST"])
def register():
    name = request.form["name"]
    email = request.form["email"]

    # Prevent duplicate registration
    Voter = Query()
    if not voters_table.search(Voter.email == email):
        voters_table.insert({"name": name, "email": email})

    return redirect(url_for("home"))


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            return redirect(url_for("dashboard"))
    return render_template("admin_login.html")


@app.route("/dashboard")
def dashboard():
    return render_template(
        "dashboard.html",
        voters=voters_table.all(),
        candidates=candidates_table.all(),
        voting_open=voting_open
    )


@app.route("/open_voting")
def open_voting():
    global voting_open
    voting_open = True
    return redirect(url_for("dashboard"))


@app.route("/add_candidate", methods=["POST"])
def add_candidate():
    name = request.form["name"]
    if name:
        candidates_table.insert({"name": name, "votes": 0})
    return redirect(url_for("dashboard"))


@app.route("/vote", methods=["POST"])
def vote():
    candidate_id = int(request.form["candidate_id"])
    candidate = candidates_table.get(doc_id=candidate_id)
    if candidate:
        candidates_table.update({"votes": candidate["votes"] + 1}, doc_ids=[candidate_id])
    return redirect(url_for("home"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render sets this automatically
    app.run(host="0.0.0.0", port=port)