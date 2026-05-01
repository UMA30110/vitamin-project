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
    le = pickle.load(open("label_encoder.pkl", "rb"))
except:
    model = None
    columns = []

# ---------------- DEFICIENCY MAP ----------------
def map_deficiency(pred):
    pred = str(pred).lower()

    if pred in ["vitamin a", "a"]:
        return "Vitamin A Deficiency"
    elif pred in ["vitamin b12", "b12"]:
        return "Vitamin B12 Deficiency"
    elif pred in ["vitamin c", "c"]:
        return "Vitamin C Deficiency"
    elif pred in ["vitamin d", "d"]:
        return "Vitamin D Deficiency"
    elif pred in ["iron"]:
        return "Iron Deficiency"
    else:
        return f"Detected: {pred}"

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
        # keep copy
        
# ✅ store values properly
        # store values
        name = data.get("name")
        age = data.get("age")

        
              # remove only for model
        data.pop("name", None)
        data.pop("age", None)
        print("INPUT DATA:", data)
        df = pd.DataFrame([data])

        print("DATAFRAME BEFORE PROCESSING:")
        print(df)
        df.columns = df.columns.str.replace(" ", "_")
        df = df.replace({"Yes": 1, "No": 0, "yes": 1, "no": 0})

        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except:
                pass
        df = pd.get_dummies(df)

        print("AFTER DUMMIES:", df.shape)

# ✅ ALIGN WITH TRAINING COLUMNS
        df = df.reindex(columns=columns)
        df = df.fillna(0)
        df = df.astype(int)

        print("AFTER REINDEX:", df.shape)

         
        print(df.head())

        if model is not None:
          try:
               pred = model.predict(df)[0]
               print("RAW PRED:", pred)   # ✅ ADD THIS

               pred = le.inverse_transform([pred])[0]
               print("FINAL PRED:", pred)  # ✅ ADD THIS

               result = pred
               session['last_result'] = result
               session['last_name'] = name
               session['last_age'] = age
              
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
            "name": name,
            "age": age,
            "result": result,
            "date": datetime.now()
        })

        return render_template(
            "result.html",
            result=result,
            name=name,
            age=age,
            explanation=explanation,
            risk=risk,
            foods=foods
        )

    except Exception as e:
        return "Error: " + str(e)
    

@app.route('/forgot')
def forgot():
    return render_template('forgot.html')

@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    username = request.form['username'].strip().lower()

    user = users_collection.find_one({"username": username})

    if user:
        return f"<h2>Your Password is: {user['password']}</h2>"
    else:
        return "<h3>User not found</h3>"
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
    
    
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
from flask import send_file


@app.route('/download_report')
def download_report():
    result = session.get("last_result", "No Data")
    name = session.get("last_name", "User")
    age = session.get("last_age", "N/A")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("VitaPredict Health Report", styles['Title']))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"<b>Name:</b> {name}", styles['Normal']))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"<b>Age:</b> {age}", styles['Normal']))
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"<b>Result:</b> {result}", styles['Normal']))
    content.append(Spacer(1, 10))

    content.append(Paragraph("<b>Recommendations:</b>", styles['Heading2']))
    content.append(Paragraph("• Maintain balanced diet", styles['Normal']))
    content.append(Paragraph("• Include fruits and vegetables", styles['Normal']))
    content.append(Paragraph("• Stay hydrated", styles['Normal']))
    content.append(Spacer(1, 10))

    content.append(Paragraph("<b>Medical Advice:</b>", styles['Heading2']))
    content.append(Paragraph("Consult a healthcare professional if symptoms persist.", styles['Normal']))
    content.append(Spacer(1, 10))

    content.append(Paragraph("Disclaimer: AI-based prediction for educational purposes only.", styles['Italic']))

    doc.build(content)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="vitapredict_report.pdf",
        mimetype="application/pdf"
    )
# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)