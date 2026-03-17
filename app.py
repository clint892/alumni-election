import sqlite3
from flask import Flask, request, render_template_string, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "supersecretkey"

# --- Database Setup ---
conn = sqlite3.connect('election.db', check_same_thread=False)
cursor = conn.cursor()

# Users table (admin)
cursor.execute('''
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT
)
''')

# Candidates table
cursor.execute('''
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    position TEXT,
    approved INTEGER DEFAULT 0
)
''')

# Voters table
cursor.execute('''
CREATE TABLE IF NOT EXISTS voters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    approved INTEGER DEFAULT 0
)
''')

# Votes table
cursor.execute('''
CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voter_email TEXT,
    candidate_id INTEGER,
    position TEXT
)
''')

conn.commit()

# --- Create default admins if not exist ---
def create_admins():
    cursor.execute("SELECT * FROM admins")
    if cursor.fetchone() is None:
        admins = [
            ('approver', generate_password_hash('approver123'), 'approver'),
            ('viewer', generate_password_hash('viewer123'), 'viewer')
        ]
        cursor.executemany("INSERT INTO admins (username, password, role) VALUES (?, ?, ?)", admins)
        conn.commit()

create_admins()

# --- Templates ---
login_template = '''
<html>
<head><title>Admin Login</title>
<style>
body { background: linear-gradient(to right, #74ebd5, #ACB6E5); font-family: Arial; }
.container { width: 300px; margin: auto; margin-top: 100px; background: white; padding: 20px; border-radius: 10px; }
input { width: 100%; padding: 10px; margin: 5px 0; border-radius: 5px; border: 1px solid #ccc; }
button { width: 100%; padding: 10px; border-radius: 5px; border: none; background-color: #4CAF50; color: white; }
</style>
</head>
<body>
<div class="container">
<h2>Admin Login</h2>
<form method="POST">
<input type="text" name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<button type="submit">Login</button>
</form>
<p>{{ message }}</p>
</div>
</body>
</html>
'''

dashboard_template = '''
<html>
<head>
<title>Admin Dashboard</title>
<style>
body { background: linear-gradient(to right, #ffecd2, #fcb69f); font-family: Arial; }
.container { width: 80%; margin: auto; margin-top: 20px; }
h2 { text-align: center; }
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

<h3>Results (Percentage)</h3>
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

# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
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
        return redirect('/')
    role = session.get('role')
    # pending voters
    cursor.execute("SELECT * FROM voters WHERE approved=0")
    voters = cursor.fetchall()
    # pending candidates
    cursor.execute("SELECT * FROM candidates WHERE approved=0")
    candidates = cursor.fetchall()
    # results (only for approved candidates)
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
    if 'admin' not in session: return redirect('/')
    cursor.execute("UPDATE voters SET approved=1 WHERE id=?", (voter_id,))
    conn.commit()
    return redirect('/dashboard')

@app.route('/approve_candidate/<int:cand_id>', methods=['POST'])
def approve_candidate(cand_id):
    if 'admin' not in session: return redirect('/')
    position = request.form['position']
    cursor.execute("UPDATE candidates SET approved=1, position=? WHERE id=?", (position, cand_id))
    conn.commit()
    return redirect('/dashboard')

@app.route('/cancel_candidate/<int:cand_id>', methods=['POST'])
def cancel_candidate(cand_id):
    if 'admin' not in session: return redirect('/')
    cursor.execute("DELETE FROM candidates WHERE id=?", (cand_id,))
    conn.commit()
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    session.pop('role', None)
    return redirect('/')

# --- Run App ---
if __name__ == '__main__':
    app.run(debug=True)