from flask import Flask, render_template, request, redirect, url_for
from tinydb import TinyDB, Query
import uuid

app = Flask(__name__)

# Databases
voters_table = TinyDB('voters.json')
candidates_table = TinyDB('candidates.json')
admins_table = TinyDB('admins.json')
settings_table = TinyDB('settings.json')

# Initialize settings
if not settings_table.all():
    settings_table.insert({"registration_open": True, "voting_open": False})

# Simple admin credentials (can be extended)
if not admins_table.all():
    admins_table.insert({"username": "admin", "password": "admin"})

# ---- Routes ----

@app.route('/')
def home():
    settings = settings_table.all()[0]
    voters = voters_table.all()
    return render_template(
        "home.html",
        voters=voters,
        registration_open=settings["registration_open"],
        voting_open=settings["voting_open"]
    )

@app.route('/register', methods=['POST'])
def register():
    settings = settings_table.all()[0]
    if not settings["registration_open"]:
        return "Registration is closed", 403

    name = request.form['name']
    email = request.form['email']

    # Check if email already registered
    Voter = Query()
    existing = voters_table.get(Voter.email == email)
    if existing:
        return "Email already registered", 400

    voters_table.insert({
        "name": name,
        "email": email,
        "approved": False,
        "confirmed": False,
        "token": ""
    })

    return redirect(url_for('home'))

# ---- Admin Login ----
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        Admin = Query()
        admin = admins_table.get((Admin.username == username) & (Admin.password == password))
        if admin:
            return redirect(url_for('dashboard'))
        return "Invalid credentials", 403
    return render_template('admin_login.html')

# ---- Admin Dashboard ----
@app.route('/dashboard')
def dashboard():
    settings = settings_table.all()[0]
    voters = voters_table.all()
    pending_voters = [v for v in voters if not v["approved"]]
    candidates = candidates_table.all()
    return render_template(
        'dashboard.html',
        voters=voters,
        pending_voters=pending_voters,
        candidates=candidates,
        registration_open=settings["registration_open"],
        voting_open=settings["voting_open"]
    )

# ---- Toggle Registration ----
@app.route('/toggle_registration')
def toggle_registration():
    settings = settings_table.all()[0]
    settings_table.update({"registration_open": not settings["registration_open"]}, doc_ids=[1])
    return redirect(url_for('dashboard'))

# ---- Toggle Voting ----
@app.route('/toggle_voting')
def toggle_voting():
    settings = settings_table.all()[0]
    # Only allow opening voting if all voters are approved & confirmed
    pending = [v for v in voters_table.all() if not (v.get("approved") and v.get("confirmed"))]
    if pending and not settings["voting_open"]:
        return "Cannot start voting: Some voters not approved/confirmed.", 400
    settings_table.update({"voting_open": not settings["voting_open"]}, doc_ids=[1])
    return redirect(url_for('dashboard'))

# ---- Approve voter ----
@app.route('/approve_voter/<int:voter_id>')
def approve_voter(voter_id):
    voter = voters_table.get(doc_id=voter_id)
    if voter:
        token = str(uuid.uuid4())
        voters_table.update({"approved": True, "token": token}, doc_ids=[voter_id])
        # In real system: send email with confirmation link
        print(f"Email sent to {voter['email']} with token {token}")
    return redirect(url_for('dashboard'))

# ---- Confirm registration (voter clicks email link) ----
@app.route('/confirm_registration/<token>')
def confirm_registration(token):
    Voter = Query()
    voter = voters_table.get(Voter.token == token)
    if voter:
        voters_table.update({"confirmed": True}, doc_ids=[voter.doc_id])
        return "Your registration is confirmed! You can now vote."
    return "Invalid token", 404

# ---- Add candidate ----
@app.route('/add_candidate', methods=['POST'])
def add_candidate():
    name = request.form['name']
    candidates_table.insert({"name": name, "votes": 0})
    return redirect(url_for('dashboard'))

# ---- Add admin ----
@app.route('/add_admin', methods=['POST'])
def add_admin():
    username = request.form['username']
    password = request.form['password']
    admins_table.insert({"username": username, "password": password})
    return redirect(url_for('dashboard'))

# ---- Voting route ----
@app.route('/vote', methods=['POST'])
def vote():
    settings = settings_table.all()[0]
    if not settings["voting_open"]:
        return "Voting is closed", 403

    email = request.form["email"]
    candidate_id = int(request.form["candidate_id"])
    Voter = Query()
    voter = voters_table.get((Voter.email == email) & (Voter.confirmed == True))
    if not voter:
        return "You are not eligible to vote", 403

    candidate = candidates_table.get(doc_id=candidate_id)
    if candidate:
        candidates_table.update({"votes": candidate["votes"] + 1}, doc_ids=[candidate.doc_id])
    return redirect(url_for("home"))

if __name__ == '__main__':
    app.run(debug=True)