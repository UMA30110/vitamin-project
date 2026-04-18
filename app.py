import pickle
import pandas as pd
from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from pymongo import MongoClient

# ✅ NEW IMPORT (for session fix)
from flask_session import Session

app = Flask(__name__)
app.secret_key = "secret123"

# ✅ SESSION FIX FOR RENDER (IMPORTANT)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

# ---------------- DATABASE ----------------
client = MongoClient("mongodb+srv://umarani:Umarani30@cluster0.52yjrxl.mongodb.net/vitamin_db")
db = client["vitamin_db"]
users_collection = db["users"]
history_collection = db["history"]

# ---------------- MODEL LOAD ----------------
try:
    model = pickle.load(open("model.pkl", "rb"))
    columns = pickle.load(open("columns.pkl", "rb"))
except:
    model = None
    columns = []

# ---------------- DEFICIENCY MAP ----------------
def map_deficiency(pred):
    pred = str(pred)
    if "A" in pred:
        return "Vitamin A Deficiency"
    elif "B12" in pred:
        return "Vitamin B12 Deficiency"
    elif "C" in pred:
        return "Vitamin C Deficiency"
    elif "D" in pred:
        return "Vitamin D Deficiency"
    elif "Iron" in pred:
        return "Iron Deficiency"
    else:
        return "General Deficiency"

# ---------------- ROUTES ----------------

@app.route('/')
def home():
    if 'user' in session:
        return render_template('home.html', user=session['user'])
    return redirect('/login')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register_user', methods=['POST'])
def register_user():
    username = request.form['username'].strip().lower()
    password = request.form['password'].strip()
    confirm = request.form['confirm_password'].strip()

    if password != confirm:
        return "<script>alert('Passwords do not match!'); window.location='/register';</script>"

    if users_collection.find_one({"username": username}):
        return "<script>alert('User already exists!'); window.location='/register';</script>"

    users_collection.insert_one({"username": username, "password": password})
    return redirect('/login')

@app.route('/login_user', methods=['POST'])
def login_user():
    username = request.form['username'].strip().lower()
    password = request.form['password'].strip()

    user = users_collection.find_one({"username": username})

    if not user:
        return "User not found!"

    if user["password"] != password:
        return "Incorrect password!"

    session['user'] = username
    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route('/form')
def form():
    if 'user' in session:
        return render_template('index.html')
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return render_template('dashboard.html')
    return redirect('/login')

@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect('/login')

    user = session.get("user")

    history = list(
        history_collection.find({"user": user}).sort("date", -1)
    )

    return render_template("profile.html", user=user, history=history)

# ---------------- PREDICT ----------------

@app.route('/predict', methods=['POST'])
def predict():
    if 'user' not in session:
        return redirect('/login')

    try:
        data = request.form.to_dict()
        df = pd.DataFrame([data])

        df.columns = df.columns.str.replace(" ", "_")
        df = df.replace({"Yes": 1, "No": 0, "yes": 1, "no": 0})

        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except:
                pass

        df = pd.get_dummies(df)

        if len(columns) > 0:
            for col in columns:
                if col not in df.columns:
                    df[col] = 0
            df = df.reindex(columns=columns, fill_value=0)

        if model is not None:
            try:
                pred = model.predict(df)[0]
                result = map_deficiency(pred)
            except:
                result = "Vitamin Deficiency Detected"
        else:
            result = "Vitamin Deficiency Detected (Demo Mode)"

        risk_score = sum([1 for v in data.values() if v == "1"])

        if risk_score <= 2:
            risk = "Low"
        elif risk_score <= 4:
            risk = "Medium"
        else:
            risk = "High"

        explanation = get_explanation(result)
        foods = get_food(result)

        history_collection.insert_one({
            "user": session.get("user"),
            "name": data.get("name"),
            "age": data.get("age"),
            "result": result,
            "date": datetime.now()
        })

        return render_template(
            "result.html",
            result=result,
            name=data.get("name"),
            age=data.get("age"),
            explanation=explanation,
            risk=risk,
            foods=foods
        )

    except Exception as e:
        return "Error: " + str(e)

# ---------------- EXTRA FUNCTIONS ----------------

def get_explanation(result):
    if "Iron" in result:
        return "Iron deficiency causes weakness and fatigue."
    elif "B12" in result:
        return "Vitamin B12 affects nerves and energy."
    elif "Vitamin C" in result:
        return "Vitamin C improves immunity."
    elif "Vitamin A" in result:
        return "Vitamin A supports vision."
    elif "Vitamin D" in result:
        return "Vitamin D strengthens bones."
    else:
        return "General nutritional issue."

def get_food(result):
    if "Iron" in result:
        return ["Spinach", "Dates", "Beetroot"]
    elif "B12" in result:
        return ["Milk", "Eggs", "Fish"]
    elif "Vitamin C" in result:
        return ["Orange", "Lemon", "Amla"]
    elif "Vitamin A" in result:
        return ["Carrot", "Mango"]
    elif "Vitamin D" in result:
        return ["Sunlight", "Milk"]
    else:
        return ["Balanced diet"]
    
    
    
from flask import send_file
import io

@app.route('/download_report')
def download_report():
    username = session.get("user", "User")

    report_text = f"""
VitaPredict Health Report
-----------------------------

Name: {username}

Result: Vitamin Deficiency Analysis Completed

Advice:
- Maintain balanced diet
- Follow healthy lifestyle
- Consult doctor if needed

-----------------------------
AI-Based System | Not Medical Diagnosis
"""

    buffer = io.BytesIO()
    buffer.write(report_text.encode('utf-8'))
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="vitapredict_report.txt",
        mimetype="text/plain"
    )

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)