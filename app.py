import os
import sqlite3
from flask import Flask, request, redirect, session

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
conn = sqlite3.connect("election.db", check_same_thread=False)
cursor = conn.cursor()

# Create tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS voters (
    id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE,
    approved INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY,
    name TEXT,
    position TEXT,
    approved INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS votes (
    email TEXT,
    candidate TEXT,
    position TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    voting INTEGER DEFAULT 0,
    registration INTEGER DEFAULT 1
)
""")

# Ensure settings row exists
cursor.execute("INSERT OR IGNORE INTO settings (id, voting, registration) VALUES (1,0,1)")
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

# ---------------- VOTER REGISTER ----------------
@app.route('/voter_register', methods=['GET','POST'])
def voter_register():
    msg=""
    if request.method=="POST":
        try:
            cursor.execute("INSERT INTO voters (name,email) VALUES (?,?)",
                           (request.form['name'], request.form['email']))
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

# ---------------- CANDIDATE APPLY (NO EMAIL) ----------------
@app.route('/candidate_apply', methods=['GET','POST'])
def candidate_apply():
    msg=""
    if request.method=="POST":
        try:
            cursor.execute("INSERT INTO candidates (name,position) VALUES (?,?)",
                           (request.form['name'], request.form['position']))
            conn.commit()
            msg="Applied. Wait approval"
        except:
            msg="Error"
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
        u = request.form['username']
        p = request.form['password']

        if u=="approver" and p=="approver123":
            session['admin']=u
            session['role']="approver"
            return redirect('/dashboard')

        elif u=="viewer" and p=="viewer123":
            session['admin']=u
            session['role']="viewer"
            return redirect('/dashboard')

        else:
            msg="Invalid credentials"

    return f'''
    <h2>Admin Login</h2>
    <form method="POST">
    <input name="username" placeholder="Username"><br>
    <input type="password" name="password" placeholder="Password"><br>
    <button>Login</button>
    </form>{msg}
    '''

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect('/admin_login')

    # pending approvals
    voters = cursor.execute("SELECT * FROM voters WHERE approved=0").fetchall()
    candidates = cursor.execute("SELECT * FROM candidates WHERE approved=0").fetchall()

    # settings
    voting = cursor.execute("SELECT voting FROM settings WHERE id=1").fetchone()[0]
    registration = cursor.execute("SELECT registration FROM settings WHERE id=1").fetchone()[0]

    return f'''
    <h2>Dashboard ({session['role']})</h2>

    <h3>Voting: {'ON' if voting else 'OFF'}</h3>
    <a href="/toggle_voting">Toggle Voting</a><br><br>

    <h3>Registration: {'ON' if registration else 'OFF'}</h3>
    <a href="/toggle_registration">Toggle Registration</a><br><br>

    <h3>Approve Voters</h3>
    {''.join([f"{v[1]} <a href='/approve_voter/{v[0]}'>Approve</a><br>" for v in voters])}

    <h3>Approve Candidates</h3>
    {''.join([f"{c[1]} ({c[2]}) <a href='/approve_candidate/{c[0]}'>Approve</a><br>" for c in candidates])}

    <br><a href="/results">View Results</a><br>
    <a href="/logout">Logout</a>
    '''

# ---------------- APPROVAL ----------------
@app.route('/approve_voter/<int:id>')
def approve_voter(id):
    cursor.execute("UPDATE voters SET approved=1 WHERE id=?", (id,))
    conn.commit()
    return redirect('/dashboard')

@app.route('/approve_candidate/<int:id>')
def approve_candidate(id):
    cursor.execute("UPDATE candidates SET approved=1 WHERE id=?", (id,))
    conn.commit()
    return redirect('/dashboard')

# ---------------- TOGGLE ----------------
@app.route('/toggle_voting')
def toggle_voting():
    v = cursor.execute("SELECT voting FROM settings WHERE id=1").fetchone()[0]
    new = 1 if v==0 else 0
    cursor.execute("UPDATE settings SET voting=? WHERE id=1", (new,))
    conn.commit()
    return redirect('/dashboard')

@app.route('/toggle_registration')
def toggle_registration():
    r = cursor.execute("SELECT registration FROM settings WHERE id=1").fetchone()[0]
    new = 1 if r==0 else 0
    cursor.execute("UPDATE settings SET registration=? WHERE id=1", (new,))
    conn.commit()
    return redirect('/dashboard')

# ---------------- VOTING ----------------
@app.route('/vote/<email>', methods=['GET','POST'])
def vote(email):
    v = cursor.execute("SELECT approved FROM voters WHERE email=?", (email,)).fetchone()
    if not v or v[0]==0:
        return "Not approved"

    voting = cursor.execute("SELECT voting FROM settings WHERE id=1").fetchone()[0]
    if voting == 0:
        return "Voting not started"

    data = cursor.execute("SELECT name,position FROM candidates WHERE approved=1").fetchall()

    grouped={}
    for c in data:
        grouped.setdefault(c[1], []).append(c[0])

    if request.method=="POST":
        for pos in grouped:
            choice=request.form.get(pos)
            exists = cursor.execute("SELECT * FROM votes WHERE email=? AND position=?",
                                    (email,pos)).fetchone()
            if not exists:
                cursor.execute("INSERT INTO votes VALUES (?,?,?)",
                               (email,choice,pos))
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
    positions = [p[0] for p in cursor.execute("SELECT DISTINCT position FROM candidates WHERE approved=1").fetchall()]

    for pos in positions:
        output+=f"<h3>{pos}</h3>"
        names = cursor.execute("SELECT name FROM candidates WHERE position=?", (pos,)).fetchall()
        total=0
        data={}

        for n in names:
            count = cursor.execute("SELECT COUNT(*) FROM votes WHERE candidate=?", (n[0],)).fetchone()[0]
            data[n[0]]=count
            total+=count

        for n,v in data.items():
            percent = (v/total*100) if total>0 else 0
            output+=f"{n}: {v} votes ({percent:.1f}%)<br>"

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