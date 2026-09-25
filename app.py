import os
import time
import sqlite3
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__, template_folder='templates')
app.secret_key = "secure_otp_session_key_2026"

USER_NAME = "Accszone3"
API_KEY = "Tm5vM1NPMmRVR0NVUndpWFNZUW9QT09"
BASE_URL = "https://durianrcs.com"

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
    credits_row = cursor.fetchone()
    credits = credits_row[0] if credits_row else 0
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
    user_row = cursor.fetchone()
    user_credits = user_row[0] if user_row else 0
    
    if user_credits < cost:
        conn.close()
        return jsonify({"status": "error", "message": "Insufficient credits"})
        
    api_url = f"{BASE_URL}/getMobile?name={USER_NAME}&ApiKey={API_KEY}&cuy={cuy}&pid={pid}&num=1&noblack=0&serial=2"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=20)
        res_data = response.json()
        response_code = res_data.get('code')
        
        if response_code == 200 or str(response_code) == '200':
            raw_data = res_data.get('data')
            phone = None
            
            if isinstance(raw_data, list):
                if len(raw_data) > 0:
                    phone = raw_data[0]
            else:
                phone = raw_data
                
            if phone:
                new_credits = user_credits - cost
                cursor.execute("UPDATE users SET credits = ? WHERE username = ?", (new_credits, session['username']))
                cursor.execute("INSERT INTO history (username, phone, pid, otp, status, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                               (session['username'], str(phone), pid, 'Waiting...', 'Pending', str(time.time())))
                conn.commit()
                conn.close()
                return jsonify({"status": "success", "number": phone, "pid": pid, "new_credits": new_credits})
            else:
                conn.close()
                return jsonify({"status": "error", "message": "Number list is empty"})
        else:
            conn.close()
            error_msg = res_data.get('msg', f'Error Code {response_code}')
            return jsonify({"status": "error", "message": str(error_msg)})
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": "Connection Timeout"})

@app.route('/api/check-otp')
def check_otp():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"})
    phone = request.args.get('phone')
    pid = request.args.get('pid')
    
    api_url = f"{BASE_URL}/getMsg?name={USER_NAME}&ApiKey={API_KEY}&pn={phone}&pid={pid}&serial=2"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for _ in range(24):
        try:
            response = requests.get(api_url, headers=headers, timeout=15)
            res_data = response.json()
            if res_data.get('code') == 200 or str(res_data.get('code')) == '200':
                otp_code = res_data.get('data')
                conn = sqlite3.connect('database.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE history SET otp = ?, status = 'Success' WHERE username = ? AND phone = ?", 
                               (str(otp_code), session['username'], phone))
                conn.commit()
                conn.close()
                return jsonify({"status": "received", "otp": otp_code})
        except:
            pass
        time.sleep(5)
    return jsonify({"status": "timeout", "otp": None})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
