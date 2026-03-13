from flask import Flask, render_template, request, redirect, url_for, session
from tinydb import TinyDB, Query

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for sessions

# TinyDB setup
db = TinyDB('db.json')
voters_table = db.table('voters')
candidates_table = db.table('candidates')
votes_table = db.table('votes')

# Voting state
voting_open = False

# Admin credentials (for simplicity)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Helper functions
def get_voters():
    return voters_table.all()

def add_voter(name, email):
    Voter = Query()
    if not voters_table.search(Voter.email == email):
        voters_table.insert({'name': name, 'email': email})

def get_candidates():
    return candidates_table.all()

def add_candidate(name, position):
    Candidate = Query()
    if not candidates_table.search((Candidate.name == name) & (Candidate.position == position)):
        candidates_table.insert({'name': name, 'position': position})

# ------------------ Routes ------------------

@app.route('/')
def home():
    return render_template("home.html")  # Only voter registration page

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    email = request.form['email']
    add_voter(name, email)
    return redirect(url_for('home'))

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials!"
    return render_template("admin_login.html")

@app.route('/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    voters = get_voters()
    candidates = get_candidates()
    return render_template("dashboard.html", voters=voters, candidates=candidates, voting_open=voting_open)

@app.route('/add_candidate', methods=['POST'])
def add_candidate_route():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    name = request.form['name']
    position = request.form['position']
    add_candidate(name, position)
    return redirect(url_for('dashboard'))

@app.route('/open_voting')
def open_voting():
    global voting_open
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    voting_open = True
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)