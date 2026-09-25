import os
import time
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__, template_folder='.')

USER_NAME = "Accszone3"
API_KEY = "Tm5vM1NPMmRVR0NVUndpWFNZUW9QT09"
BASE_URL = "https://durianrcs.com"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/get-number')
def get_number():
    pid = request.args.get('pid', '0544')
    api_url = f"{BASE_URL}/getMobile?name={USER_NAME}&ApiKey={API_KEY}&cuy=us&pid={pid}&num=1&noblack=0&serial=2"
    
    try:
        response = requests.get(api_url)
        res = response.json()
        
        if res.get('code') == 200:
            return jsonify({"status": "success", "number": res.get('data'), "pid": pid})
        else:
            return jsonify({"status": "error", "message": res.get('msg', 'Error fetching number')})
    except Exception as e:
        return jsonify({"status": "error", "message": "Server Connection Error"})

@app.route('/api/check-otp')
def check_otp():
    phone = request.args.get('phone')
    pid = request.args.get('pid')
    api_url = f"{BASE_URL}/getMsg?name={USER_NAME}&ApiKey={API_KEY}&pn={phone}&pid={pid}&serial=2"
    
    for _ in range(24):
        try:
            res = requests.get(api_url).json()
            if res.get('code') == 200:
                return jsonify({"status": "received", "otp": res.get('data')})
        except:
            pass
        time.sleep(5)
        
    return jsonify({"status": "timeout", "otp": None})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
