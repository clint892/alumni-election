import os
from flask import Flask, request, redirect, url_for, render_template_string, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_FILE = "election.db"

# Ensure DB exists and tables created
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        email TEXT,
        approved INTEGER DEFAULT 0
    )''')
    # Candidates table
    c.execute('''CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        position TEXT,
        approved INTEGER DEFAULT 0
    )''')
    # Votes table
    c.execute('''CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id INTEGER,
        candidate_id INTEGER,
        position TEXT
    )''')
    # Positions table
    c.execute('''CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )''')
    # Election control
    c.execute('''CREATE TABLE IF NOT EXISTS election_control (
        id INTEGER PRIMARY KEY,
        registration_open INTEGER DEFAULT 1,
        voting_open INTEGER DEFAULT 0
    )''')
    # Default election control row
    c.execute("INSERT OR IGNORE INTO election_control (id, registration_open, voting_open) VALUES (1,1,0)")
    # Add default admins if not exist
    c.execute("INSERT OR IGNORE INTO users (username, password, role, email, approved) VALUES ('approver','approver123','approver','approver@example.com',1)")
    c.execute("INSERT OR IGNORE INTO users (username, password, role, email, approved) VALUES ('viewer','viewer123','viewer','viewer@example.com',1)")
    conn.commit()
    conn.close()

init_db()

# Helpers
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def is_logged_in():
    return 'user_id' in session

def is_admin():
    return session.get('role') in ['approver','viewer']

# Routes
@app.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username,password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash("Logged in successfully","success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid login","danger")
    return render_template_string('''
    <html><head><title>Login</title>
    <style>
    body {background: linear-gradient(to right, #74ebd5, #ACB6E5); font-family: Arial;}
    .login {width:300px;margin:100px auto;padding:20px;background:white;border-radius:10px;}
    </style>
    </head>
    <body>
    <div class="login">
    <h3>Login</h3>
    <form method="post">
    Username:<br><input type="text" name="username" required><br>
    Password:<br><input type="password" name="password" required><br><br>
    <input type="submit" value="Login">
    </form>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for category, message in messages %}
        <div style="color:red;">{{ message }}</div>
      {% endfor %}
    {% endwith %}
    </div>
    </body></html>
    ''')

@app.route('/dashboard')
def dashboard():
    if not is_logged_in(): return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    # Get election control
    c.execute("SELECT * FROM election_control WHERE id=1")
    control = c.fetchone()
    # Get pending voters
    c.execute("SELECT * FROM users WHERE approved=0")
    pending_voters = c.fetchall()
    # Get pending candidates
    c.execute("SELECT * FROM candidates WHERE approved=0")
    pending_candidates = c.fetchall()
    # All candidates approved
    c.execute("SELECT * FROM candidates WHERE approved=1")
    candidates = c.fetchall()
    # Votes count per position
    c.execute("SELECT position, COUNT(*) as total FROM votes GROUP BY position")
    votes_summary = c.fetchall()
    conn.close()
    return render_template_string('''
    <html><head><title>Admin Dashboard</title>
    <style>
    body {font-family:Arial; background: linear-gradient(to right, #ffecd2, #fcb69f);}
    h2 {color:#333;}
    table {border-collapse: collapse; width:80%; margin-bottom:20px;}
    table, th, td {border:1px solid #999;}
    th, td {padding:8px;text-align:left;}
    .btn {padding:5px 10px; border:none; border-radius:5px; cursor:pointer;}
    .btn-approve {background:green; color:white;}
    .btn-cancel {background:red; color:white;}
    .btn-toggle {background:#007BFF; color:white;}
    </style>
    </head>
    <body>
    <h2>Welcome, {{ session['username'] }} ({{ session['role'] }})</h2>
    <h3>Election Controls</h3>
    <form method="post" action="/toggle_registration">
      <button class="btn btn-toggle">{{ 'Close' if control['registration_open'] else 'Open' }} Registration</button>
    </form>
    <form method="post" action="/toggle_voting">
      <button class="btn btn-toggle">{{ 'Close' if control['voting_open'] else 'Open' }} Voting</button>
    </form>

    <h3>Pending Voters</h3>
    <table>
    <tr><th>Username</th><th>Email</th><th>Action</th></tr>
    {% for voter in pending_voters %}
    <tr>
      <td>{{ voter['username'] }}</td>
      <td>{{ voter['email'] }}</td>
      <td>
        <a href="/approve_voter/{{ voter['id'] }}" class="btn btn-approve">Approve</a>
      </td>
    </tr>
    {% endfor %}
    </table>

    <h3>Pending Candidates</h3>
    <table>
    <tr><th>Name</th><th>Position</th><th>Action</th></tr>
    {% for cand in pending_candidates %}
    <tr>
      <td>{{ cand['name'] }}</td>
      <td>{{ cand['position'] }}</td>
      <td>
        <a href="/approve_candidate/{{ cand['id'] }}" class="btn btn-approve">Approve</a>
        <a href="/cancel_candidate/{{ cand['id'] }}" class="btn btn-cancel">Cancel</a>
      </td>
    </tr>
    {% endfor %}
    </table>

    <h3>Voting Results (Percentages)</h3>
    <table>
    <tr><th>Position</th><th>Total Votes</th></tr>
    {% for v in votes_summary %}
      <tr><td>{{ v['position'] }}</td><td>{{ v['total'] }}</td></tr>
    {% endfor %}
    </table>

    <br><a href="/logout">Logout</a>
    </body></html>
    ''', control=control, pending_voters=pending_voters, pending_candidates=pending_candidates, votes_summary=votes_summary)

# Admin actions
@app.route('/toggle_registration', methods=['POST'])
def toggle_registration():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT registration_open FROM election_control WHERE id=1")
    status = c.fetchone()['registration_open']
    new_status = 0 if status else 1
    c.execute("UPDATE election_control SET registration_open=? WHERE id=1", (new_status,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/toggle_voting', methods=['POST'])
def toggle_voting():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT voting_open FROM election_control WHERE id=1")
    status = c.fetchone()['voting_open']
    new_status = 0 if status else 1
    c.execute("UPDATE election_control SET voting_open=? WHERE id=1", (new_status,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/approve_voter/<int:id>')
def approve_voter(id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET approved=1 WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/approve_candidate/<int:id>')
def approve_candidate(id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE candidates SET approved=1 WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/cancel_candidate/<int:id>')
def cancel_candidate(id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM candidates WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)