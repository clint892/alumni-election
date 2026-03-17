import os
import sqlite3
from flask import Flask, request, render_template_string, redirect, session

app = Flask(__name__)
app.secret_key = "secret123"

conn = sqlite3.connect("election.db", check_same_thread=False)
cursor = conn.cursor()

# ================= HOME =================
@app.route('/')
def home():
    return '''
    <h1>Election System</h1>
    <a href="/voter_register">Register Voter</a><br><br>
    <a href="/candidate_apply">Apply Candidate</a><br><br>
    <a href="/admin_login">Admin Login</a>
    '''

# ================= VOTER (UNCHANGED) =================
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

# ================= CANDIDATE (EMAIL REMOVED) =================
@app.route('/candidate_apply', methods=['GET','POST'])
def candidate_apply():
    msg=""
    if request.method=="POST":
        name=request.form['name']
        position=request.form['position']
        try:
            cursor.execute(
                "INSERT INTO candidates (name, position, approved) VALUES (?, ?, 0)",
                (name, position)
            )
            conn.commit()
            msg="Application submitted. Wait for admin approval."
        except:
            msg="Already applied."
    return f'''
    <h2>Candidate Application</h2>
    <form method="POST">
    <input type="text" name="name" placeholder="Full Name" required><br>
    <input type="text" name="position" placeholder="Position" required><br>
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
        if u=="admin" and p=="admin":
            session['admin']=u
            return redirect('/dashboard')
        else:
            msg="Wrong login"
    return f'''
    <h2>Admin Login</h2>
    <form method="POST">
    <input name="username"><br>
    <input name="password" type="password"><br>
    <button>Login</button>
    </form>
    {msg}
    '''

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect('/admin_login')

    cursor.execute("SELECT * FROM candidates")
    candidates = cursor.fetchall()

    return f'''
    <h2>Admin Dashboard</h2>
    <h3>Candidates</h3>
    {''.join([f"{c[0]} - {c[1]}<br>" for c in candidates])}
    <br><a href="/logout">Logout</a>
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