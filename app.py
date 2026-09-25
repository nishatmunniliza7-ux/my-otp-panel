import os
import time
import sqlite3
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__, template_folder='templates')
app.secret_key = "secure_otp_session_key_2026"

USER_NAME = "Accszone3"
API_KEY = "Tm5vM1NPMmRVR0NVUndpWFNZUW9QT09"

API_ROUTERS = [
    "https://durianrcs.com",
    "https://durianrcs.com",
    "https://durianrcs.com"
]

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            credits INTEGER,
            status TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            phone TEXT,
            pid TEXT,
            otp TEXT,
            status TEXT,
            timestamp TEXT
        )
    ''')
    try:
        cursor.execute("INSERT INTO users (username, password, credits, status) VALUES (?, ?, ?, ?)", 
                       ('Nirob FB', '12345678', 5000, 'active'))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

init_db()

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        if user and user[0] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT credits FROM users WHERE username = ?", (session['username'],))
    user_data = cursor.fetchone()
    credits = user_data[0] if user_data else 0
    cursor.execute("SELECT phone, pid, otp, status FROM history WHERE username = ? ORDER BY id DESC", (session['username'],))
    history_data = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', username=session['username'], credits=credits, history=history_data)

@app.route('/api/get-number')
def get_number():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"})
    pid = request.args.get('pid', '0544')
    cuy = request.args.get('cuy', 'us')
    cost = 140 if pid == '0544' else 60
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT credits FROM users WHERE username = ?", (session['username'],))
    user_data = cursor.fetchone()
    user_credits = user_data[0] if user_data else 0
    
    if user_credits < cost:
        conn.close()
        return jsonify({"status": "error", "message": "Insufficient credits balance"})
        
    endpoint = f"/getMobile?name={USER_NAME}&ApiKey={API_KEY}&cuy={cuy}&pid={pid}&num=1&noblack=0&serial=2"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache'
    }
    
    res_data = None
    for base_url in API_ROUTERS:
        try:
            response = requests.get(base_url + endpoint, headers=headers, timeout=12)
            if response.status_code == 200:
                res_data = response.json()
                break
        except:
            continue
            
    if res_data and (res_data.get('code') == 200 or str(res_data.get('code')) == '200'):
        raw_phone = res_data.get('data')
        phone = raw_phone if not isinstance(raw_phone, list) else (raw_phone[0] if len(raw_phone) > 0 else None)
        
        if phone:
            new_credits = user_credits - cost
            cursor.execute("UPDATE users SET credits = ? WHERE username = ?", (new_credits, session['username']))
            cursor.execute("INSERT INTO history (username, phone, pid, otp, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                           (session['username'], str(phone), pid, 'Waiting...', 'Pending', str(time.time())))
            conn.commit()
            conn.close()
            return jsonify({"status": "success", "number": phone, "pid": pid, "new_credits": new_credits})
            
    conn.close()
    err_msg = res_data.get('msg') if res_data else "Supplier Blocked Connection"
    return jsonify({"status": "error", "message": f"{err_msg}"})

@app.route('/api/check-otp')
def check_otp():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"})
    phone = request.args.get('phone')
    pid = request.args.get('pid')
    
    endpoint = f"/getMsg?name={USER_NAME}&ApiKey={API_KEY}&pn={phone}&pid={pid}&serial=2"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for _ in range(24):
        res_data = None
        for base_url in API_ROUTERS:
            try:
                response = requests.get(base_url + endpoint, headers=headers, timeout=10)
                if response.status_code == 200:
                    res_data = response.json()
                    break
            except:
                continue
                
        if res_data and (res_data.get('code') == 200 or str(res_data.get('code')) == '200'):
            otp_code = res_data.get('data')
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute("UPDATE history SET otp = ?, status = 'Success' WHERE username = ? AND phone = ?", 
                           (str(otp_code), session['username'], phone))
            conn.commit()
            conn.close()
            return jsonify({"status": "received", "otp": otp_code})
        time.sleep(5)
    return jsonify({"status": "timeout", "otp": None})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
