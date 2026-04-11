import pickle
import pandas as pd
from flask import Flask, render_template, request, redirect, session
from datetime import datetime
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = "secret123"

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

    # ❌ Password mismatch
    if password != confirm:
        return "<script>alert('Passwords do not match!'); window.location='/register';</script>"

    # ❌ User already exists
    if users_collection.find_one({"username": username}):
        return "<script>alert('User already exists!'); window.location='/register';</script>"

    # ✅ Insert user
    users_collection.insert_one({"username": username, "password": password})

    # ✅ Redirect to login
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

# ✅ FIXED DASHBOARD ROUTE
@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return render_template('dashboard.html')   # your dashboard page
    return redirect('/login')
@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect('/login')

    user = session.get("user")
    print("Logged user:", user)   # ✅ debug

    history = list(
        history_collection.find({"user": user}).sort("date", -1)
    )

    print("Filtered data:", history)  # ✅ debug

    return render_template("profile.html", user=user, history=history)


# ---------------- PREDICT ----------------

@app.route('/predict', methods=['POST'])
def predict():
    if 'user' not in session:
        return redirect('/login')

    try:
        data = request.form.to_dict()
        df = pd.DataFrame([data])

        # Fix column names
        df.columns = df.columns.str.replace(" ", "_")

        # Convert Yes/No
        df = df.replace({"Yes": 1, "No": 0, "yes": 1, "no": 0})

        # Convert numeric
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except:
                pass

        # Encoding
        df = pd.get_dummies(df)

        # Match model columns safely
        if len(columns) > 0:
            for col in columns:
                if col not in df.columns:
                    df[col] = 0
            df = df.reindex(columns=columns, fill_value=0)

        # Prediction
        if model is not None:
            try:
                pred = model.predict(df)[0]
                result = map_deficiency(pred)
            except:
                result = "Vitamin Deficiency Detected"
        else:
            result = "Vitamin Deficiency Detected (Demo Mode)"

        # Risk Calculation
        risk_score = sum([1 for v in data.values() if v == "1"])

        if risk_score <= 2:
            risk = "Low"
        elif risk_score <= 4:
            risk = "Medium"
        else:
            risk = "High"

        explanation = get_explanation(result)
        foods = get_food(result)

        # Save to DB
        try:
            history_collection.insert_one({
                "user": session.get("user"),
                "name": data.get("name"),
                "age": data.get("age"),
                "result": result,
                "date": datetime.now()
            })
        except:
            pass

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
    

# ---------------- DOWNLOAD REPORT ----------------

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from flask import send_file
from io import BytesIO

@app.route('/download_report')
def download_report():
    if 'user' not in session:
        return redirect('/login')

    last = history_collection.find_one(
        {"user": session.get("user")},
        sort=[("date", -1)]
    )

    if not last:
        return "No report found!"

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("<b><font size=18 color=blue>Vitamin Health Report</font></b>", styles['Title']))
    content.append(Spacer(1, 20))

    content.append(Paragraph(f"Name: {last.get('name', 'N/A')}", styles['Normal']))
    content.append(Paragraph(f"Age: {last.get('age', 'N/A')}", styles['Normal']))
    content.append(Paragraph(f"Result: {last.get('result', 'N/A')}", styles['Normal']))
    content.append(Paragraph(f"Date: {str(last.get('date'))}", styles['Normal']))

    doc.build(content)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Vitamin_Report.pdf",
        mimetype='application/pdf'
    )




# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)