from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- DATABASE ----------------
def get_db():
    return sqlite3.connect("database.db")

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # USERS TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)

    # IOT DATA TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS iot_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temperature REAL,
            humidity REAL,
            fire TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- AUTH ----------------

@app.route('/')
def login():
    return render_template("login.html")

@app.route('/signup')
def signup():
    return render_template("signup.html")

@app.route('/register_user', methods=['POST'])
def register_user():
    email = request.form.get("email")
    password = request.form.get("password")

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
        conn.commit()
    except:
        conn.close()
        return "User already exists"

    conn.close()
    return redirect('/')

@app.route('/login_user', methods=['POST'])
def login_user():
    email = request.form.get("email")
    password = request.form.get("password")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
    user = cur.fetchone()

    conn.close()

    if user:
        session['user'] = email
        return redirect('/dashboard')

    return "Invalid login"

# ---------------- PROTECTED ROUTES ----------------

def is_logged_in():
    return 'user' in session

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect('/')
    return render_template("dashboard.html")

@app.route('/about')
def about():
    if not is_logged_in():
        return redirect('/')
    return render_template("about.html")

@app.route('/setting')
def setting():
    if not is_logged_in():
        return redirect('/')
    return render_template("setting.html", msg="")

# ---------------- LOGOUT ----------------

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------- CHANGE PASSWORD ----------------

@app.route('/change_password', methods=['POST'])
def change_password():
    if not is_logged_in():
        return redirect('/')

    old = request.form.get("oldPass")
    new = request.form.get("newPass")
    email = session['user']

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT password FROM users WHERE email=?", (email,))
    data = cur.fetchone()

    if not data:
        conn.close()
        return render_template("setting.html", msg="User not found")

    if old != data[0]:
        conn.close()
        return render_template("setting.html", msg="Wrong old password")

    cur.execute("UPDATE users SET password=? WHERE email=?", (new, email))
    conn.commit()
    conn.close()

    return render_template("setting.html", msg="Password updated successfully")

# ---------------- REAL-TIME IOT ----------------

# GET latest data (dashboard use)
@app.route('/data')
def data():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT temperature, humidity, fire 
        FROM iot_data 
        ORDER BY id DESC LIMIT 1
    """)

    row = cur.fetchone()
    conn.close()

    if row:
        return jsonify({
            "temperature": row[0],
            "humidity": row[1],
            "fire": row[2]
        })

    return jsonify({
        "temperature": 0,
        "humidity": 0,
        "fire": "NO"
    })

# SENSOR POST API (ESP32 will use this)
@app.route('/update', methods=['POST'])
def update():
    temp = request.form.get("temperature")
    hum = request.form.get("humidity")
    fire = request.form.get("fire")

    if not temp or not hum or not fire:
        return "Missing data", 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO iot_data (temperature, humidity, fire)
        VALUES (?, ?, ?)
    """, (temp, hum, fire))

    conn.commit()
    conn.close()

    # FIRE ALERT LOGIC (backend level)
    if fire == "FIRE":
        print("🔥 FIRE ALERT TRIGGERED")

    return "OK", 200

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)