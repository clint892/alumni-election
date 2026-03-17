import os
import sqlite3
from flask import Flask, request, redirect, session

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
conn = sqlite3.connect("election.db", check_same_thread=False)
cursor = conn.cursor()

# Voters
cursor.execute("""
CREATE TABLE IF NOT EXISTS voters (
    id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE,
    approved INTEGER DEFAULT 0
)
""")

# Candidates (NO EMAIL)
cursor.execute("""
CREATE TABLE IF NOT EXISTS candidates (
    name TEXT PRIMARY KEY,
    position TEXT,
    approved INTEGER DEFAULT 0
)
""")

# Votes
cursor.execute("""
CREATE TABLE IF NOT EXISTS votes (
    email TEXT,
    candidate TEXT,
    position TEXT
)
""")

# Settings
cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")
cursor.execute("INSERT OR IGNORE INTO settings VALUES ('voting','off')")
cursor.execute("INSERT OR IGNORE INTO settings VALUES ('registration','on')")
conn.commit()

# ---------------- HOME ----------------
@app.route('/')
def home():
    return '''
    <h1>Election System</h1>
    <a href="/voter_register">Register Voter</a><br><br>
    <a href="/candidate_apply">Apply Candidate</a><br><br>
    <a href="/admin_login">Admin Login</a>
    '''

# ---------------- VOTER ----------------
@app.route('/voter_register', methods=['GET','POST'])
def voter_register():
    msg=""
    if request.method=="POST":
        name=request.form['name']
        email=request.form['email']
        try:
            cursor.execute("INSERT INTO voters (name,email,approved) VALUES (?,?,0)",(name,email))
            conn.commit()
            msg="Registered. Wait approval"
        except:
            msg="Email exists"
    return f'''
    <h2>Voter Register</h2>
    <form method="POST">
    <input name="name" placeholder="Name"><br>
    <input name="email" placeholder="Email"><br>
    <button>Register</button>
    </form>{msg}
    '''

# ---------------- CANDIDATE (NO EMAIL) ----------------
@app.route('/candidate_apply', methods=['GET','POST'])
def candidate_apply():
    msg=""
    if request.method=="POST":
        name=request.form['name']
        position=request.form['position']
        try:
            cursor.execute("INSERT INTO candidates (name,position,approved) VALUES (?,?,0)",(name,position))
            conn.commit()
            msg="Wait approval"
        except:
            msg="Already applied"
    return f'''
    <h2>Candidate Apply</h2>
    <form method="POST">
    <input name="name" placeholder="Name"><br>
    <input name="position" placeholder="Position"><br>
    <button>Apply</button>
    </form>{msg}
    '''

# ---------------- ADMIN LOGIN ----------------
@app.route('/admin_login', methods=['GET','POST'])
def admin_login():
    msg=""
    if request.method=="POST":
        username=request.form['username']
        password=request.form['password']

        # Approver admin
        if username=="approver" and password=="approver123":
            session['admin']=username
            session['role']="approver"
            return redirect('/dashboard')

        # Viewer admin
        if username=="viewer" and password=="viewer123":
            session['admin']=username
            session['role']="viewer"
            return redirect('/dashboard')

        msg="Wrong login"

    return f'''
    <h2>Admin Login</h2>
    <form method="POST">
    <input name="username" placeholder="Username"><br>
    <input name="password" type="password" placeholder="Password"><br>
    <button>Login</button>
    </form>{msg}
    '''

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect('/admin_login')

    cursor.execute("SELECT * FROM voters WHERE approved=0")
    voters=cursor.fetchall()

    cursor.execute("SELECT * FROM candidates WHERE approved=0")
    candidates=cursor.fetchall()

    cursor.execute("SELECT value FROM settings WHERE key='voting'")
    voting=cursor.fetchone()[0]

    return f'''
    <h2>Dashboard ({session['role']})</h2>

    <h3>Voting: {voting}</h3>
    <a href="/toggle_voting">Toggle Voting</a><br><br>

    <h3>Approve Voters</h3>
    {''.join([f"{v[1]} <a href='/approve_voter/{v[0]}'>Approve</a><br>" for v in voters])}

    <h3>Approve Candidates</h3>
    {''.join([f"{c[0]} ({c[1]}) <a href='/approve_candidate/{c[0]}'>Approve</a><br>" for c in candidates])}

    <br><a href="/results">View Results</a><br>
    <a href="/logout">Logout</a>
    '''

# ---------------- APPROVAL ----------------
@app.route('/approve_voter/<int:id>')
def approve_voter(id):
    cursor.execute("UPDATE voters SET approved=1 WHERE id=?",(id,))
    conn.commit()
    return redirect('/dashboard')

@app.route('/approve_candidate/<name>')
def approve_candidate(name):
    cursor.execute("UPDATE candidates SET approved=1 WHERE name=?",(name,))
    conn.commit()
    return redirect('/dashboard')

# ---------------- TOGGLE VOTING ----------------
@app.route('/toggle_voting')
def toggle_voting():
    cursor.execute("SELECT value FROM settings WHERE key='voting'")
    v=cursor.fetchone()[0]
    new="on" if v=="off" else "off"
    cursor.execute("UPDATE settings SET value=? WHERE key='voting'",(new,))
    conn.commit()
    return redirect('/dashboard')

# ---------------- VOTING ----------------
@app.route('/vote/<email>', methods=['GET','POST'])
def vote(email):
    cursor.execute("SELECT approved FROM voters WHERE email=?",(email,))
    v=cursor.fetchone()
    if not v or v[0]==0:
        return "Not approved"

    cursor.execute("SELECT value FROM settings WHERE key='voting'")
    if cursor.fetchone()[0]=="off":
        return "Voting not started"

    cursor.execute("SELECT name,position FROM candidates WHERE approved=1")
    data=cursor.fetchall()

    grouped={}
    for c in data:
        grouped.setdefault(c[1],[]).append(c[0])

    if request.method=="POST":
        for pos in grouped:
            choice=request.form.get(pos)
            cursor.execute("SELECT * FROM votes WHERE email=? AND position=?",(email,pos))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO votes VALUES (?,?,?)",(email,choice,pos))
        conn.commit()
        return "Vote submitted"

    form=""
    for pos in grouped:
        form+=f"<h3>{pos}</h3>"
        for c in grouped[pos]:
            form+=f"<input type='radio' name='{pos}' value='{c}'> {c}<br>"

    return f"<form method='POST'>{form}<button>Vote</button></form>"

# ---------------- RESULTS ----------------
@app.route('/results')
def results():
    if 'admin' not in session:
        return redirect('/admin_login')

    output=""
    cursor.execute("SELECT DISTINCT position FROM candidates WHERE approved=1")
    positions=[p[0] for p in cursor.fetchall()]

    for pos in positions:
        output+=f"<h3>{pos}</h3>"
        cursor.execute("SELECT name FROM candidates WHERE position=? AND approved=1",(pos,))
        for c in cursor.fetchall():
            name=c[0]
            cursor.execute("SELECT COUNT(*) FROM votes WHERE candidate=?",(name,))
            v=cursor.fetchone()[0]
            output+=f"{name}: {v}<br>"

    return output

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)