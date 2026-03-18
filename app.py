# app.py
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'
DATABASE = 'election.db'

# --------------------------
# Database helpers
# --------------------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT NOT NULL,
            approved INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            approved INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voting INTEGER DEFAULT 0,
            registration INTEGER DEFAULT 1
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Insert default admins if missing
    cursor.execute("INSERT OR IGNORE INTO admins (id, username, password) VALUES (1,'admin1','password1')")
    cursor.execute("INSERT OR IGNORE INTO admins (id, username, password) VALUES (2,'admin2','password2')")

    conn.commit()
    conn.close()

init_db()

# --------------------------
# Homepage
# --------------------------
@app.route('/')
def home():
    return '''
    <h1>Alumni Election System</h1>
    <ul>
        <li><a href="/admin/login">Admin Login</a></li>
        <li><a href="/candidate/apply">Candidate Application</a></li>
        <li><a href="/voter/register">Voter Registration</a></li>
    </ul>
    '''

# --------------------------
# Admin login
# --------------------------
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        conn=get_db_connection()
        cursor=conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE username=? AND password=?",(username,password))
        admin=cursor.fetchone()
        conn.close()
        if admin:
            session['admin']=username
            return redirect(url_for('admin_dashboard'))
        else:
            return "Invalid credentials"
    return '''
    <h1>Admin Login</h1>
    <form method="post">
        Username:<input name="username"><br>
        Password:<input type="password" name="password"><br>
        <input type="submit" value="Login">
    </form>
    <br><a href="/">Back to Home</a>
    '''

# --------------------------
# Candidate application
# --------------------------
@app.route('/candidate/apply', methods=['GET','POST'])
def candidate_apply():
    if request.method=='POST':
        name=request.form['name']
        position=request.form['position']
        conn=get_db_connection()
        cursor=conn.cursor()
        cursor.execute("INSERT INTO candidates (name, position, approved) VALUES (?,?,0)",(name,position))
        conn.commit()
        conn.close()
        return "Application submitted! Await admin approval. <br><a href='/'>Back to Home</a>"
    return '''
    <h1>Candidate Application</h1>
    <form method="post">
        Name:<input name="name"><br>
        Position:<input name="position"><br>
        <input type="submit" value="Apply">
    </form>
    <br><a href="/">Back to Home</a>
    '''

# --------------------------
# Voter registration
# --------------------------
@app.route('/voter/register', methods=['GET','POST'])
def voter_register():
    if request.method=='POST':
        email=request.form['email']
        conn=get_db_connection()
        cursor=conn.cursor()
        try:
            cursor.execute("INSERT INTO voters (email, approved) VALUES (?,0)",(email,))
            conn.commit()
            message="Registration successful! Await admin approval."
        except sqlite3.IntegrityError:
            message="Email already registered."
        conn.close()
        return f"{message} <br><a href='/'>Back to Home</a>"
    return '''
    <h1>Voter Registration</h1>
    <form method="post">
        Email:<input name="email"><br>
        <input type="submit" value="Register">
    </form>
    <br><a href="/">Back to Home</a>
    '''

# --------------------------
# Admin dashboard & management
# --------------------------
@app.route('/admin')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    conn=get_db_connection()
    cursor=conn.cursor()

    # Candidates
    cursor.execute("SELECT * FROM candidates")
    candidates=cursor.fetchall()
    # Voters
    cursor.execute("SELECT * FROM voters")
    voters=cursor.fetchall()
    # Settings
    cursor.execute("SELECT voting, registration FROM settings WHERE id=1")
    setting=cursor.fetchone()
    # Results
    cursor.execute("SELECT position, COUNT(*) as votes FROM candidates WHERE approved=1 GROUP BY position")
    results=cursor.fetchall()
    conn.close()

    cand_html="<h2>Candidates</h2><ul>"
    for c in candidates:
        approve_btn = f"<a href='/admin/approve_candidate/{c['id']}'>Approve</a>" if c['approved']==0 else ""
        cand_html+=f"<li>{c['name']} - {c['position']} (Approved:{c['approved']}) {approve_btn}</li>"
    cand_html+="</ul>"

    voter_html="<h2>Voters</h2><ul>"
    for v in voters:
        approve_btn = f"<a href='/admin/approve_voter/{v['id']}'>Approve</a>" if v['approved']==0 else ""
        voter_html+=f"<li>{v['email']} (Approved:{v['approved']}) {approve_btn}</li>"
    voter_html+="</ul>"

    res_html="<h2>Election Results</h2><ul>"
    for r in results:
        res_html+=f"<li>{r['position']}: {r['votes']} votes</li>"
    res_html+="</ul>"

    voting_status="ON" if setting['voting'] else "OFF"
    reg_status="ON" if setting['registration'] else "OFF"

    return f"""
    <h1>Admin Dashboard</h1>
    <p>Voting:{voting_status} | Registration:{reg_status}</p>
    {cand_html}
    {voter_html}
    {res_html}
    <br><a href='/admin/toggle_voting'>Toggle Voting</a>
    <br><a href='/admin/toggle_registration'>Toggle Registration</a>
    <br><a href='/admin/logout'>Logout</a>
    """

# --------------------------
# Approvals & toggles
# --------------------------
@app.route('/admin/approve_candidate/<int:id>')
def approve_candidate(id):
    if 'admin' not in session: return redirect(url_for('admin_login'))
    conn=get_db_connection()
    conn.execute("UPDATE candidates SET approved=1 WHERE id=?",(id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve_voter/<int:id>')
def approve_voter(id):
    if 'admin' not in session: return redirect(url_for('admin_login'))
    conn=get_db_connection()
    conn.execute("UPDATE voters SET approved=1 WHERE id=?",(id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_voting')
def toggle_voting():
    if 'admin' not in session: return redirect(url_for('admin_login'))
    conn=get_db_connection()
    val=conn.execute("SELECT voting FROM settings WHERE id=1").fetchone()['voting']
    conn.execute("UPDATE settings SET voting=? WHERE id=1",(0 if val else 1,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_registration')
def toggle_registration():
    if 'admin' not in session: return redirect(url_for('admin_login'))
    conn=get_db_connection()
    val=conn.execute("SELECT registration FROM settings WHERE id=1").fetchone()['registration']
    conn.execute("UPDATE settings SET registration=? WHERE id=1",(0 if val else 1,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

# --------------------------
# Admin logout
# --------------------------
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('home'))

# --------------------------
# Run app
# --------------------------
if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=port)