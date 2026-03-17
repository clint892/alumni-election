# app.py
import sqlite3
from flask import Flask, render_template_string, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "secret123"

DATABASE = "election.db"

# -----------------------
# Database helper
# -----------------------
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    # Voters
    db.execute("""CREATE TABLE IF NOT EXISTS voters(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    email TEXT UNIQUE,
                    approved INTEGER DEFAULT 0
                )""")
    # Candidates
    db.execute("""CREATE TABLE IF NOT EXISTS candidates(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    position TEXT,
                    approved INTEGER DEFAULT 0
                )""")
    # Votes
    db.execute("""CREATE TABLE IF NOT EXISTS votes(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voter_email TEXT,
                    position TEXT,
                    candidate_id INTEGER
                )""")
    # Admins
    db.execute("""CREATE TABLE IF NOT EXISTS admin(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    role TEXT
                )""")
    # Settings
    db.execute("""CREATE TABLE IF NOT EXISTS settings(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voting INTEGER DEFAULT 0,
                    registration INTEGER DEFAULT 1
                )""")
    # Insert default admins if missing
    admin_check = db.execute("SELECT * FROM admin").fetchall()
    if not admin_check:
        db.execute("INSERT INTO admin(username,password,role) VALUES('approver','approver123','approver')")
        db.execute("INSERT INTO admin(username,password,role) VALUES('viewer','viewer123','viewer')")
    # Insert default settings if missing
    settings_check = db.execute("SELECT * FROM settings").fetchone()
    if not settings_check:
        db.execute("INSERT INTO settings(voting,registration) VALUES(0,1)")
    db.commit()

init_db()

# -----------------------
# Templates (embedded)
# -----------------------

dashboard_template = """
<!DOCTYPE html>
<html>
<head>
<title>Admin Dashboard</title>
<style>
body {font-family: Arial; background: linear-gradient(120deg, #f6d365, #fda085);}
.container {max-width: 800px; margin:auto; padding:20px; background: rgba(255,255,255,0.8); border-radius: 10px;}
h2 {text-align:center; color:#333;}
table {width:100%; border-collapse: collapse;}
th,td {padding:8px; border:1px solid #ccc;}
th {background:#f28a30; color:white;}
a.button {padding:5px 10px; background:#ff5a5f; color:white; text-decoration:none; border-radius:5px;}
a.button:hover {background:#ff1e1e;}
</style>
</head>
<body>
<div class="container">
<h2>Admin Dashboard - {{role}}</h2>

{% if role=='approver' %}
<h3>Settings</h3>
<form method="POST" action="/toggle_voting">
Voting: <input type="submit" name="toggle" value="{{'Close' if voting else 'Open'}}">
</form>
<form method="POST" action="/toggle_registration">
Registration: <input type="submit" name="toggle" value="{{'Close' if registration else 'Open'}}">
</form>

<h3>Pending Voters</h3>
<table>
<tr><th>Name</th><th>Email</th><th>Approve</th></tr>
{% for v in voters %}
<tr>
<td>{{v['name']}}</td>
<td>{{v['email']}}</td>
<td><a href="/approve_voter/{{v['id']}}" class="button">Approve</a></td>
</tr>
{% endfor %}
</table>

<h3>Pending Candidates</h3>
<table>
<tr><th>Name</th><th>Position</th><th>Approve</th><th>Cancel</th></tr>
{% for c in candidates %}
<tr>
<td>{{c['name']}}</td>
<td>{{c['position']}}</td>
<td><a href="/approve_candidate/{{c['id']}}" class="button">Approve</a></td>
<td><a href="/cancel_candidate/{{c['id']}}" class="button">Cancel</a></td>
</tr>
{% endfor %}
</table>
{% endif %}

{% if role=='viewer' or role=='approver' %}
<h3>Results (Percentages)</h3>
<table>
<tr><th>Position</th><th>Candidate</th><th>Votes</th><th>Percent</th></tr>
{% for r in results %}
<tr>
<td>{{r['position']}}</td>
<td>{{r['name']}}</td>
<td>{{r['votes']}}</td>
<td>{{r['percent']}}%</td>
</tr>
{% endfor %}
</table>
{% endif %}

</div>
</body>
</html>
"""

login_template = """
<!DOCTYPE html>
<html>
<head>
<title>Admin Login</title>
<style>
body {font-family: Arial; background: linear-gradient(120deg,#cfd9df,#e2ebf0);}
.container {max-width:400px;margin:auto;padding:20px;background:white;border-radius:10px;margin-top:100px;}
input[type=text], input[type=password]{width:100%;padding:10px;margin:5px 0;}
input[type=submit]{padding:10px; background:#4CAF50;color:white;border:none;width:100%;}
</style>
</head>
<body>
<div class="container">
<h2>Admin Login</h2>
<form method="POST">
<input type="text" name="username" placeholder="Username" required>
<input type="password" name="password" placeholder="Password" required>
<input type="submit" value="Login">
</form>
{% with messages = get_flashed_messages() %}
{% if messages %}
<ul>
{% for msg in messages %}
<li>{{msg}}</li>
{% endfor %}
</ul>
{% endif %}
{% endwith %}
</div>
</body>
</html>
"""

# -----------------------
# Helper functions
# -----------------------
def get_settings():
    db = get_db()
    s = db.execute("SELECT * FROM settings").fetchone()
    return s['voting'], s['registration']

def get_results():
    db = get_db()
    candidates = db.execute("SELECT * FROM candidates WHERE approved=1").fetchall()
    results=[]
    for c in candidates:
        votes = db.execute("SELECT COUNT(*) as cnt FROM votes WHERE candidate_id=?", (c['id'],)).fetchone()['cnt']
        total_votes = db.execute("SELECT COUNT(*) as total FROM votes WHERE position=?", (c['position'],)).fetchone()['total']
        percent = round((votes/total_votes*100) if total_votes else 0,2)
        results.append({'position':c['position'], 'name':c['name'],'votes':votes,'percent':percent})
    return results

# -----------------------
# Routes
# -----------------------
@app.route("/", methods=['GET','POST'])
def login():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        db=get_db()
        admin=db.execute("SELECT * FROM admin WHERE username=? AND password=?", (username,password)).fetchone()
        if admin:
            session['admin_id']=admin['id']
            session['role']=admin['role']
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid login")
    return render_template_string(login_template)

@app.route("/dashboard")
def dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    db=get_db()
    role=session['role']
    voters=[]
    candidates=[]
    voting, registration = get_settings()
    if role=='approver':
        voters=db.execute("SELECT * FROM voters WHERE approved=0").fetchall()
        candidates=db.execute("SELECT * FROM candidates WHERE approved=0").fetchall()
    results=get_results()
    return render_template_string(dashboard_template, voters=voters, candidates=candidates, role=role, results=results, voting=voting, registration=registration)

@app.route("/approve_voter/<int:id>")
def approve_voter(id):
    db=get_db()
    db.execute("UPDATE voters SET approved=1 WHERE id=?",(id,))
    db.commit()
    return redirect(url_for('dashboard'))

@app.route("/approve_candidate/<int:id>")
def approve_candidate(id):
    db=get_db()
    db.execute("UPDATE candidates SET approved=1 WHERE id=?",(id,))
    db.commit()
    return redirect(url_for('dashboard'))

@app.route("/cancel_candidate/<int:id>")
def cancel_candidate(id):
    db=get_db()
    db.execute("DELETE FROM candidates WHERE id=?",(id,))
    db.commit()
    return redirect(url_for('dashboard'))

@app.route("/toggle_voting", methods=['POST'])
def toggle_voting():
    db=get_db()
    voting, registration = get_settings()
    new_status=0 if voting else 1
    db.execute("UPDATE settings SET voting=? WHERE id=1",(new_status,))
    db.commit()
    return redirect(url_for('dashboard'))

@app.route("/toggle_registration", methods=['POST'])
def toggle_registration():
    db=get_db()
    voting, registration = get_settings()
    new_status=0 if registration else 1
    db.execute("UPDATE settings SET registration=? WHERE id=1",(new_status,))
    db.commit()
    return redirect(url_for('dashboard'))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

# -----------------------
# Run
# -----------------------
if __name__=="__main__":
    app.run(debug=True)