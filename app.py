import os
import sqlite3
from flask import Flask, request, render_template_string, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- Database Setup ---
DB_FILE = 'election.db'

def init_db():
    create_new = not os.path.exists(DB_FILE)
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            position TEXT,
            approved INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            approved INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_email TEXT,
            candidate_id INTEGER,
            position TEXT
        )
    ''')
    conn.commit()

    if create_new:
        admins = [
            ('approver', generate_password_hash('approver123'), 'approver'),
            ('viewer', generate_password_hash('viewer123'), 'viewer')
        ]
        cursor.executemany("INSERT INTO admins (username, password, role) VALUES (?, ?, ?)", admins)
        conn.commit()
    return conn, cursor

conn, cursor = init_db()

# --- Templates ---
landing_template = '''
<html>
<head>
<title>Alumni Election System</title>
<style>
body { background: linear-gradient(to right, #c6ffdd, #fbd786, #f7797d); font-family: Arial; }
.container { width: 400px; margin: auto; margin-top: 100px; background: white; padding: 20px; border-radius: 10px; text-align: center; }
button { padding: 10px 20px; margin: 10px; border-radius: 5px; border: none; cursor: pointer; background-color: #4CAF50; color: white; }
</style>
</head>
<body>
<div class="container">
<h2>Welcome to Alumni Election</h2>
<a href="/voter_register"><button>Register as Voter</button></a><br>
<a href="/candidate_apply"><button>Apply as Candidate</button></a><br>
<a href="/admin_login"><button>Admin Login</button></a>
</div>
</body>
</html>
'''

login_template = '''
<html>
<head><title>Admin Login</title>
<style>
body { background: linear-gradient(to right, #74ebd5, #ACB6E5); font-family: Arial; }
.container { width: 300px; margin: auto; margin-top: 100px; background: white; padding: 20px; border-radius: 10px; }
input, button { width: 100%; padding: 10px; margin: 5px 0; border-radius: 5px; border: 1px solid #ccc; }
button { background-color: #4CAF50; color: white; border: none; }
</style></head>
<body>
<div class="container">
<h2>Admin Login</h2>
<form method="POST">
<input type="text" name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<button type="submit">Login</button>
</form>
<p>{{ message }}</p>
<a href="/"><button>Back to Home</button></a>
</div>
</body>
</html>
'''

dashboard_template = '''
<html>
<head><title>Admin Dashboard</title>
<style>
body { background: linear-gradient(to right, #ffecd2, #fcb69f); font-family: Arial; }
.container { width: 90%; margin: auto; margin-top: 20px; }
h2, h3 { text-align: center; }
table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
th, td { border: 1px solid #ccc; padding: 10px; text-align: left; }
th { background-color: #f08080; color: white; }
button { padding: 5px 10px; border-radius: 5px; border: none; background-color: #4CAF50; color: white; cursor: pointer; }
form { display: inline; }
</style>
</head>
<body>
<div class="container">
<h2>Admin Dashboard ({{ role }})</h2>

<h3>Pending Voter Approvals</h3>
<table>
<tr><th>Name</th><th>Email</th><th>Approve</th></tr>
{% for voter in voters %}
<tr>
<td>{{ voter[1] }}</td>
<td>{{ voter[2] }}</td>
<td>
<form method="POST" action="/approve_voter/{{ voter[0] }}">
<button type="submit">Approve</button>
</form>
</td>
</tr>
{% endfor %}
</table>

<h3>Pending Candidate Approvals</h3>
<table>
<tr><th>Name</th><th>Email</th><th>Position</th><th>Approve</th><th>Cancel</th></tr>
{% for cand in candidates %}
<tr>
<td>{{ cand[1] }}</td>
<td>{{ cand[2] }}</td>
<td>
<form method="POST" action="/approve_candidate/{{ cand[0] }}">
<input type="text" name="position" placeholder="Enter Position" required>
<button type="submit">Approve</button>
</form>
</td>
<td></td>
<td>
<form method="POST" action="/cancel_candidate/{{ cand[0] }}">
<button type="submit">Cancel</button>
</form>
</td>
</tr>
{% endfor %}
</table>

<h3>Voting Results (Percentage)</h3>
<table>
<tr><th>Candidate</th><th>Position</th><th>Votes</th><th>Percentage</th></tr>
{% for res in results %}
<tr>
<td>{{ res[0] }}</td>
<td>{{ res[1] }}</td>
<td>{{ res[2] }}</td>
<td>{{ "%.2f"|format(res[3]) }}%</td>
</tr>
{% endfor %}
</table>

<a href="/logout"><button>Logout</button></a>
</div>
</body>
</html>
'''

voter_register_template = '''
<html>
<head>
<title>Voter Registration</title>
<style>
body { background: linear-gradient(to right, #fbc2eb, #a6c1ee); font-family: Arial; }
.container { width: 300px; margin: auto; margin-top: 50px; background: white; padding: 20px; border-radius: 10px; }
input, button { width: 100%; padding: 10px; margin: 5px 0; border-radius: 5px; border: 1px solid #ccc; }
button { background-color: #2196F3; color: white; border: none; }
</style>
</head>
<body>
<div class="container">
<h2>Voter Registration</h2>
<form method="POST">
<input type="text" name="name" placeholder="Full Name" required>
<input type="email" name="email" placeholder="Email" required>
<button type="submit">Register</button>
</form>
<p>{{ message }}</p>
<a href="/"><button>Back to Home</button></a>
</div>
</body>
</html>
'''

candidate_apply_template = '''
<html>
<head>
<title>Candidate Application</title>
<style>
body { background: linear-gradient(to right, #ffecd2, #fcb69f); font-family: Arial; }
.container { width: 300px; margin: auto; margin-top: 50px; background: white; padding: 20px; border-radius: 10px; }
input, button { width: 100%; padding: 10px; margin: 5px 0; border-radius: 5px; border: 1px solid #ccc; }
button { background-color: #FF5722; color: white; border: none; }
</style>
</head>
<body>
<div class="container">
<h2>Candidate Application</h2>
<form method="POST">
<input type="text" name="name" placeholder="Full Name" required>
<input type="email" name="email" placeholder="Email" required>
<button type="submit">Apply</button>
</form>
<p>{{ message }}</p>
<a href="/"><button>Back to Home</button></a>
</div>
</body>
</html>
'''

vote_template = '''
<html>
<head>
<title>Vote</title>
<style>
body { background: linear-gradient(to right, #cfd9df, #e2ebf0); font-family: Arial; }
.container { width: 600px; margin: auto; margin-top: 20px; background: white; padding: 20px; border-radius: 10px; }
h2 { text-align: center; }
table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
th, td { border: 1px solid #ccc; padding: 10px; text-align: left; }
th { background-color: #4CAF50; color: white; }
button { padding: 5px 10px; border-radius: 5px; border: none; background-color: #2196F3; color: white; cursor: pointer; }
</style>
</head>
<body>
<div class="container">
<h2>Voting</h2>
<form method="POST">
{% for pos, candidates in candidates_by_position.items() %}
<h3>{{ pos }}</h3>
{% for c in candidates %}
<input type="radio" name="{{ pos }}" value="{{ c[0] }}" required> {{ c[1] }}<br>
{% endfor %}
{% endfor %}
<button type="submit">Submit Vote</button>
</form>
<p>{{ message }}</p>
<a href="/"><button>Back to Home</button></a>
</div>
</body>
</html>
'''

# --- Routes ---
@app.route('/')
def index():
    return render_template_string(landing_template)

@app.route('/home')
def home():
    return render_template_string(landing_template)

@app.route('/admin_login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor.execute("SELECT password, role FROM admins WHERE username=?", (username,))
        row = cursor.fetchone()
        if row and check_password_hash(row[0], password):
            session['admin'] = username
            session['role'] = row[1]
            return redirect('/dashboard')
        else:
            message = "Invalid credentials"
    return render_template_string(login_template, message=message)

@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect('/admin_login')
    role = session.get('role')
    cursor.execute("SELECT * FROM voters WHERE approved=0")
    voters = cursor.fetchall()
    cursor.execute("SELECT * FROM candidates WHERE approved=0")
    candidates = cursor.fetchall()
    cursor.execute("SELECT id, name, position FROM candidates WHERE approved=1")
    cand_list = cursor.fetchall()
    results = []
    for c in cand_list:
        cursor.execute("SELECT COUNT(*) FROM votes WHERE candidate_id=?", (c[0],))
        votes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM votes WHERE position=?", (c[2],))
        total = cursor.fetchone()[0]
        pct = (votes / total *100) if total>0 else 0
        results.append((c[1], c[2], votes, pct))
    return render_template_string(dashboard_template, role=role, voters=voters, candidates=candidates, results=results)

@app.route('/approve_voter/<int:voter_id>', methods=['POST'])
def approve_voter(voter_id):
    if 'admin' not in session: return redirect('/admin_login')
    cursor.execute("UPDATE voters SET approved=1 WHERE id=?", (voter_id,))
    conn.commit()
    return redirect('/dashboard')

@app.route('/approve_candidate/<int:cand_id>', methods=['POST'])
def approve_candidate(cand_id):
    if 'admin' not in session: return redirect('/admin_login')
    position = request.form['position']
    cursor.execute("UPDATE candidates SET approved=1, position=? WHERE id=?", (position, cand_id))
    conn.commit()
    return redirect('/dashboard')

@app.route('/cancel_candidate/<int:cand_id>', methods=['POST'])
def cancel_candidate(cand_id):
    if 'admin' not in session: return redirect('/admin_login')
    cursor.execute("DELETE FROM candidates WHERE id=?", (cand_id,))
    conn.commit()
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    session.pop('role', None)
    return redirect('/')

# --- Voter Routes ---
@app.route('/voter_register', methods=['GET', 'POST'])
def voter_register():
    message = ''
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        cursor.execute("INSERT INTO voters (name, email, approved) VALUES (?, ?, 0)", (name, email))
        conn.commit()
        message = "Registration submitted. Wait for admin approval."
    return render_template_string(voter_register_template, message=message)

@app.route('/candidate_apply', methods=['GET', 'POST'])
def candidate_apply():
    message = ''
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        cursor.execute("INSERT INTO candidates (name, email, approved) VALUES (?, ?, 0)", (name, email))
        conn.commit()
        message = "Candidate application submitted. Wait for admin approval."
    return render_template_string(candidate_apply_template, message=message)

@app.route('/vote/<voter_email>', methods=['GET', 'POST'])
def vote(voter_email):
    message = ''
    cursor.execute("SELECT approved FROM voters WHERE email=?", (voter_email,))
    voter = cursor.fetchone()
    if not voter or voter[0]==0:
        return "You are not approved to vote yet."
    cursor.execute("SELECT id, name, position FROM candidates WHERE approved=1")
    cands = cursor.fetchall()
    candidates_by_position = {}
    for c in cands:
        candidates_by_position.setdefault(c[2], []).append(c)
    if request.method=='POST':
        for position in candidates_by_position.keys():
            candidate_id = request.form.get(position)
            if candidate_id:
                cursor.execute("SELECT * FROM votes WHERE voter_email=? AND position=?", (voter_email, position))
                if cursor.fetchone() is None:
                    cursor.execute("INSERT INTO votes (voter_email, candidate_id, position) VALUES (?, ?, ?)", (voter_email, candidate_id, position))
        conn.commit()
        message = "Your votes have been submitted!"
    return render_template_string(vote_template, candidates_by_position=candidates_by_position, message=message)

# --- Run on Railway ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)