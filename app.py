from flask import Flask, render_template, request, redirect, url_for
from tinydb import TinyDB, Query
import os

app = Flask(__name__)

# TinyDB setup
db = TinyDB("db.json")
voters_table = db.table("voters")
candidates_table = db.table("candidates")
admins_table = db.table("admins")

# Initialize default admin
if len(admins_table) == 0:
    admins_table.insert({"username": "admin", "password": "admin123"})

# Election states
registration_open = True
voting_open = False

# -----------------------
# Routes
# -----------------------

@app.route("/")
def home():
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
    if not registration_open:
        return "Registration is closed", 403
    name = request.form["name"]
    email = request.form["email"]
    Voter = Query()
    if not voters_table.search(Voter.email == email):
        voters_table.insert({"name": name, "email": email})
    return redirect(url_for("home"))

# Voting
@app.route("/vote", methods=["POST"])
def vote():
    if not voting_open:
        return "Voting is closed", 403
    candidate_id = int(request.form["candidate_id"])
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
    return render_template(
        "dashboard.html",
        voters=voters_table.all(),
        candidates=candidates_table.all(),
        registration_open=registration_open,
        voting_open=voting_open
    )

# Admin actions
@app.route("/toggle_registration")
def toggle_registration():
    global registration_open
    registration_open = not registration_open
    return redirect(url_for("dashboard"))

@app.route("/toggle_voting")
def toggle_voting():
    global voting_open
    voting_open = not voting_open
    return redirect(url_for("dashboard"))

@app.route("/add_candidate", methods=["POST"])
def add_candidate():
    name = request.form["name"]
    if name:
        candidates_table.insert({"name": name, "votes": 0})
    return redirect(url_for("dashboard"))

@app.route("/add_admin", methods=["POST"])
def add_admin():
    username = request.form["username"]
    password = request.form["password"]
    if username and password:
        Admin = Query()
        if not admins_table.search(Admin.username == username):
            admins_table.insert({"username": username, "password": password})
    return redirect(url_for("dashboard"))

# -----------------------
# Run the app
# -----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render dynamic port
    app.run(host="0.0.0.0", port=port)