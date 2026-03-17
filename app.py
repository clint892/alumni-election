import os
from flask import Flask, request, redirect, url_for, render_template_string, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"
DB_FILE = "election.db"

# Initialize database and tables
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
    # Positions table
    c.execute('''CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )''')
    # Votes table
    c.execute('''CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id INTEGER,
        candidate_id INTEGER,
        position TEXT
    )''')
    # Election control
    c.execute('''CREATE TABLE IF NOT EXISTS election_control (
        id INTEGER PRIMARY KEY,
        registration_open INTEGER DEFAULT 1,
        voting_open INTEGER DEFAULT 0
    )''')
    c.execute("INSERT OR IGNORE INTO election_control (id, registration_open, voting_open) VALUES (1,1,0)")
    # Default admins
    c.execute("INSERT OR IGNORE INTO users (username, password, role, email, approved) VALUES ('approver','approver123','approver','approver@example.com',1)")
    c.execute("INSERT OR IGNORE INTO users (username, password, role, email, approved) VALUES ('viewer','viewer123','viewer','viewer@example.com',1)")
    # Default positions
    c.execute("INSERT OR IGNORE INTO positions (id, name) VALUES (1,'President')")
    c.execute("INSERT OR IGNORE INTO positions (id, name) VALUES (2,'Secretary')")
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
    if is_admin():
        return redirect(url_for('dashboard'))
    return redirect(url_for('home'))

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
            return redirect(url_for('index'))
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
    <p>Or <a href="/register">Register as voter</a></p>
    </div>
    </body></html>
    ''')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username,password,role,email) VALUES (?,?,?,?)", (username,password,'voter',email))
            conn.commit()
            flash("Registration successful! Wait for admin approval.","success")
        except sqlite3.IntegrityError:
            flash("Username already exists","danger")
        conn.close()
        return redirect(url_for('login'))
    return render_template_string('''
    <html><head><title>Register</title></head><body>
    <h3>Voter Registration</h3>
    <form method="post">
    Username: <input type="text" name="username" required><br>
    Email: <input type="email" name="email" required><br>
    Password: <input type="password" name="password" required><br>
    <input type="submit" value="Register">
    </form>
    <p><a href="/login">Back to login</a></p>
    </body></html>
    ''')

# Home page for voters
@app.route('/home')
def home():
    if not is_logged_in() or is_admin(): return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    # Positions
    c.execute("SELECT * FROM positions")
    positions = c.fetchall()
    # Candidates per position
    candidates_dict = {}
    for p in positions:
        c.execute("SELECT * FROM candidates WHERE approved=1 AND position=?", (p['name'],))
        candidates_dict[p['name']] = c.fetchall()
    # Election control
    c.execute("SELECT * FROM election_control WHERE id=1")
    control = c.fetchone()
    conn.close()
    return render_template_string('''
    <html><head><title>Voter Home</title>
    <style>
    body {background: linear-gradient(to right,#fbc2eb,#a6c1ee); font-family:Arial;}
    .container {width:80%; margin:auto;}
    h2 {color:#333;}
    .candidate {padding:10px; margin:5px; background:white; border-radius:5px;}
    </style>
    </head><body>
    <div class="container">
    <h2>Welcome {{ session['username'] }}</h2>
    {% if control['voting_open'] %}
      <h3>Vote for candidates</h3>
      <form method="post" action="/vote">
      {% for pos in positions %}
        <h4>{{ pos['name'] }}</h4>
        {% for cand in candidates_dict[pos['name']] %}
          <input type="radio" name="{{ pos['name'] }}" value="{{ cand['id'] }}" required> {{ cand['name'] }}<br>
        {% endfor %}
      {% endfor %}
      <br><input type="submit" value="Submit Votes">
      </form>
    {% else %}
      <p>Voting is currently closed.</p>
    {% endif %}
    <p><a href="/apply_candidate">Apply as Candidate</a> | <a href="/logout">Logout</a></p>
    </div>
    </body></html>
    ''', positions=positions, candidates_dict=candidates_dict, control=control)

@app.route('/apply_candidate', methods=['GET','POST'])
def apply_candidate():
    if not is_logged_in() or is_admin(): return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM positions")
    positions = c.fetchall()
    conn.close()
    if request.method=='POST':
        name = request.form['name']
        position = request.form['position']
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO candidates (name, position) VALUES (?,?)", (name,position))
        conn.commit()
        conn.close()
        flash("Candidate application submitted! Wait for admin approval.","success")
        return redirect(url_for('home'))
    return render_template_string('''
    <html><head><title>Apply Candidate</title></head><body>
    <h3>Candidate Application</h3>
    <form method="post">
    Name: <input type="text" name="name" required><br>
    Position: <select name="position">
      {% for p in positions %}
        <option value="{{p['name']}}">{{p['name']}}</option>
      {% endfor %}
    </select><br>
    <input type="submit" value="Apply">
    </form>
    <p><a href="/home">Back</a></p>
    </body></html>
    ''', positions=positions)

@app.route('/vote', methods=['POST'])
def vote():
    if not is_logged_in() or is_admin(): return redirect(url_for('login'))
    voter_id = session['user_id']
    conn = get_db()
    c = conn.cursor()
    # Ensure voter has not voted for each position
    c.execute("SELECT * FROM election_control WHERE id=1")
    control = c.fetchone()
    if not control['voting_open']:
        flash("Voting is closed","danger")
        conn.close()
        return redirect(url_for('home'))
    for pos, cand_id in request.form.items():
        c.execute("SELECT * FROM votes WHERE voter_id=? AND position=?", (voter_id,pos))
        if c.fetchone():
            flash(f"You have already voted for {pos}","danger")
            continue
        c.execute("INSERT INTO votes (voter_id,candidate_id,position) VALUES (?,?,?)", (voter_id,cand_id,pos))
    conn.commit()
    conn.close()
    flash("Votes submitted successfully!","success")
    return redirect(url_for('home'))

# Admin dashboard
@app.route('/dashboard')
def dashboard():
    if not is_logged_in() or not is_admin(): return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM election_control WHERE id=1")
    control = c.fetchone()
    c.execute("SELECT * FROM users WHERE approved=0")
    pending_voters = c.fetchall()
    c.execute("SELECT * FROM candidates WHERE approved=0")
    pending_candidates = c.fetchall()
    c.execute("SELECT * FROM candidates WHERE approved=1")
    candidates = c.fetchall()
    # Results with percentages
    c.execute("SELECT position, COUNT(*) as total FROM votes GROUP BY position")
    votes_summary = c.fetchall()
    conn.close()
    return render_template_string('''
    <html><head><title>Admin Dashboard</title>
    <style>
    body {background: linear-gradient(to right, #ffecd2, #fcb69f); font-family:Arial;}
    table {border-collapse:collapse; width:80%;}
    table, th, td {border:1px solid #999; padding:8px;}
    .btn{padding:5px 10px;border:none;border-radius:5px; cursor:pointer;}
    .btn-approve{background:green;color:white;}
    .btn-cancel{background:red;color:white;}
    .btn-toggle{background:#007BFF;color:white;}
    </style></head><body>
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
      <td><a href="/approve_voter/{{voter['id']}}" class="btn btn-approve">Approve</a></td>
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
      <tr><td>{{v['position']}}</td><td>{{v['total']}}</td></tr>
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
    c.execute("UPDATE election_control SET registration_open=? WHERE id=1", (0 if status else 1,))
    conn.commit(); conn.close()
    return redirect(url_for('dashboard'))

@app.route('/toggle_voting', methods=['POST'])
def toggle_voting():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT voting_open FROM election_control WHERE id=1")
    status = c.fetchone()['voting_open']
    c.execute("UPDATE election_control SET voting_open=? WHERE id=1", (0 if status else 1,))
    conn.commit(); conn.close()
    return redirect(url_for('dashboard'))

@app.route('/approve_voter/<int:id>')
def approve_voter(id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET approved=1 WHERE id=?", (id,))
    conn.commit(); conn.close()
    return redirect(url_for('dashboard'))

@app.route('/approve_candidate/<int:id>')
def approve_candidate(id):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE candidates SET approved=1 WHERE id=?", (id,))
    conn.commit(); conn.close()
    return redirect(url_for('dashboard'))

@app.route('/cancel_candidate/<int:id>')
def cancel_candidate(id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM candidates WHERE id=?", (id,))
    conn.commit(); conn.close()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)