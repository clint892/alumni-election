import os
import sqlite3
from flask import Flask, request, render_template_string, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

DB = "election.db"

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB, check_same_thread=False)
    cursor = conn.cursor()

    # Admins
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT
    )
    """)

    # Candidates (NO EMAIL)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        name TEXT PRIMARY KEY,
        position TEXT
    )
    """)

    # Voters (WITH EMAIL)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        approved INTEGER DEFAULT 0
    )
    """)

    # Votes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        voter_email TEXT,
        candidate_name TEXT,
        position TEXT
    )
    """)

    conn.commit()

    # Default admins
    cursor.execute("SELECT * FROM admins")
    if not cursor.fetchall():
        cursor.execute("INSERT INTO admins VALUES (?, ?, ?)",
                       ("approver", generate_password_hash("approver123"), "approver"))
        cursor.execute("INSERT INTO admins VALUES (?, ?, ?)",
                       ("viewer", generate_password_hash("viewer123"), "viewer"))
        conn.commit()

    return conn, cursor

conn, cursor = init_db()

# ================= HOME =================
@app.route('/')
def home():
    return '''
    <body style="background:linear-gradient(to right,#43cea2,#185a9d);color:white;text-align:center;font-family:Arial">
    <h1>Alumni Election System</h1>
    <a href="/voter_register"><button>Register Voter</button></a><br><br>
    <a href="/candidate_apply"><button>Apply Candidate</button></a><br><br>
    <a href="/admin_login"><button>Admin Login</button></a>
    </body>
    '''

# ================= VOTER =================
@app.route('/voter_register', methods=['GET','POST'])
def voter_register():
    msg=""
    if request.method=="POST":
        name=request.form['name']
        email=request.form['email']
        try:
            cursor.execute("INSERT INTO voters (name,email,approved) VALUES (?,?,0)",(name,email))
            conn.commit()
            msg="Registered. Wait for approval."
        except:
            msg="Email already used."
    return f'''
    <h2>Voter Register</h2>
    <form method="POST">
    <input name="name" placeholder="Name" required><br>
    <input name="email" placeholder="Email" required><br>
    <button>Register</button>
    </form>
    {msg}
    '''

# ================= CANDIDATE (NO EMAIL) =================
@app.route('/candidate_apply', methods=['GET','POST'])
def candidate_apply():
    msg=""
    if request.method=="POST":
        name=request.form['name']
        position=request.form['position']
        try:
            cursor.execute("INSERT INTO candidates (name, position) VALUES (?,?)",(name,position))
            conn.commit()
            msg="Application sent. Wait for approval."
        except:
            msg="Already applied."
    return f'''
    <h2>Candidate Application</h2>
    <form method="POST">
    <input name="name" placeholder="Name" required><br>
    <input name="position" placeholder="Position" required><br>
    <button>Apply</button>
    </form>
    {msg}
    '''

# ================= ADMIN LOGIN =================
@app.route('/admin_login', methods=['GET','POST'])
def admin_login():
    msg=""
    if request.method=="POST":
        u=request.form['username']
        p=request.form['password']
        cursor.execute("SELECT password,role FROM admins WHERE username=?",(u,))
        data=cursor.fetchone()
        if data and check_password_hash(data[0],p):
            session['admin']=u
            session['role']=data[1]
            return redirect('/dashboard')
        else:
            msg="Wrong login"
    return f'''
    <h2>Admin Login</h2>
    <form method="POST">
    <input name="username" placeholder="Username"><br>
    <input name="password" type="password" placeholder="Password"><br>
    <button>Login</button>
    </form>
    {msg}
    '''

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect('/admin_login')

    cursor.execute("SELECT * FROM voters WHERE approved=0")
    voters=cursor.fetchall()

    cursor.execute("SELECT * FROM candidates")
    candidates=cursor.fetchall()

    # RESULTS %
    cursor.execute("SELECT DISTINCT position FROM candidates")
    positions=[p[0] for p in cursor.fetchall()]

    results=""
    for pos in positions:
        cursor.execute("SELECT name FROM candidates WHERE position=?",(pos,))
        names=[n[0] for n in cursor.fetchall()]

        for n in names:
            cursor.execute("SELECT COUNT(*) FROM votes WHERE candidate_name=? AND position=?",(n,pos))
            v=cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM votes WHERE position=?",(pos,))
            total=cursor.fetchone()[0]

            pct=(v/total*100) if total>0 else 0
            results+=f"{n} ({pos}) - {pct:.2f}%<br>"

    return f'''
    <h2>Dashboard ({session['role']})</h2>

    <h3>Approve Voters</h3>
    {''.join([f"{v[1]} <a href='/approve_voter/{v[0]}'>Approve</a><br>" for v in voters])}

    <h3>Candidates</h3>
    {''.join([f"{c[0]} ({c[1]})<br>" for c in candidates])}

    <h3>Results</h3>
    {results}

    <br><a href="/logout">Logout</a>
    '''

# ================= APPROVE =================
@app.route('/approve_voter/<int:id>')
def approve_voter(id):
    cursor.execute("UPDATE voters SET approved=1 WHERE id=?",(id,))
    conn.commit()
    return redirect('/dashboard')

# ================= VOTING =================
@app.route('/vote/<email>', methods=['GET','POST'])
def vote(email):

    cursor.execute("SELECT approved FROM voters WHERE email=?",(email,))
    v=cursor.fetchone()
    if not v or v[0]==0:
        return "Not approved"

    cursor.execute("SELECT name,position FROM candidates")
    data=cursor.fetchall()

    grouped={}
    for c in data:
        grouped.setdefault(c[1],[]).append(c[0])

    if request.method=="POST":
        for pos in grouped:
            choice=request.form.get(pos)
            cursor.execute("SELECT * FROM votes WHERE voter_email=? AND position=?",(email,pos))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO votes VALUES (?,?,?)",(email,choice,pos))
        conn.commit()
        return "Vote submitted"

    form=""
    for pos in grouped:
        form+=f"<h3>{pos}</h3>"
        for c in grouped[pos]:
            form+=f"<input type='radio' name='{pos}' value='{c}'> {c}<br>"

    return f'''
    <form method="POST">
    {form}
    <button>Submit</button>
    </form>
    '''

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)