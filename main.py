from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/form')
def form():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    name = request.form.get("name")
    age = request.form.get("age")

    result = "Vitamin Deficiency Detected"

    return render_template(
        "result.html",
        result=result,
        name=name,
        age=age
    )

if __name__ == "__main__":
    app.run(debug=True)