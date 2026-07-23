import os
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
load_dotenv()
from utils import db
from utils.predictor import predict_diabetes
from utils.chatbot import ask_health_assistant
from utils.pdf import generate_report_pdf



app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

db.init_db()


# ---------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------
# 1. Home
# ---------------------------------------------------------------
@app.route("/")
def home():
    return render_template("home.html")


# ---------------------------------------------------------------
# 2. Login / Signup
# ---------------------------------------------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not name:
            flash("Please enter your name.", "error")
            return render_template("signup.html")

        if not email:
            flash("Please enter your email.", "error")
            return render_template("signup.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("signup.html")

        if db.get_user_by_email(email):
            flash("An account with this email already exists.", "error")
            return render_template("signup.html")

        password_hash = generate_password_hash(password)
        user_id = db.create_user(name, email, password_hash)
        session["user_id"] = user_id
        session["user_name"] = name
        flash("Account created successfully!", "success")
        return redirect(url_for("prediction_form"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        if not email or not password:
            flash("Please enter email and password.", "error")
            return render_template("login.html")
        user = db.get_user_by_email(email)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")
        return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("home"))


# ---------------------------------------------------------------
# 3 & 4. Prediction Form + AI Model
# ---------------------------------------------------------------
@app.route("/predict", methods=["GET", "POST"])
@login_required
def prediction_form():
    if request.method == "POST":
        patient_name = request.form["name"].strip()
        if not patient_name:
            flash("Please enter patient name.", "error")
            return redirect(url_for("prediction_form"))
        try:
            age = float(request.form["age"])
            height_cm = float(request.form["height"])
            weight_kg = float(request.form["weight"])
            glucose = float(request.form["blood_glucose_level"])
        except ValueError:
            flash("Please enter valid numeric values.", "error")
            return redirect(url_for("prediction_form"))

        gender = request.form["gender"]

        if age < 1 or age > 120:
            flash("Please enter a valid age.", "error")
            return redirect(url_for("prediction_form"))

        if height_cm <= 0:
            flash("Height must be greater than zero.", "error")
            return redirect(url_for("prediction_form"))

        if weight_kg <= 0:
            flash("Weight must be greater than zero.", "error")
            return redirect(url_for("prediction_form"))
        if glucose <= 0:
            flash("Blood glucose must be greater than zero.", "error")
            return redirect(url_for("prediction_form"))

        # BMI calculation
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m ** 2), 1)

        result = predict_diabetes(age, gender, bmi, glucose)

        pred_id = db.save_prediction(
            user_id=session["user_id"],
            patient_name=patient_name,
            age=age,
            gender=gender,
            height=height_cm,
            weight=weight_kg,
            bmi=bmi,
            blood_glucose_level=glucose,
            prediction=result["prediction"],
            confidence=result["confidence"],
            top_reasons="||".join(result["reasons"]),
        )

        return redirect(url_for("result", pred_id=pred_id))

    return render_template("form.html")


# ---------------------------------------------------------------
# 5. Result Page
# ---------------------------------------------------------------
@app.route("/result/<int:pred_id>")
@login_required
def result(pred_id):
    row = db.get_prediction_by_id(pred_id)
    if row is None or row["user_id"] != session["user_id"]:
        flash("Prediction not found.", "error")
        return redirect(url_for("dashboard"))

    reasons = row["top_reasons"].split("||")
    return render_template("result.html", row=row, reasons=reasons)

   # ---------------------------------------------------------------
# 6. Feedback Page
# --------------------------------------------------------------- 
@app.route("/feedback/<int:pred_id>", methods=["GET", "POST"])
@login_required
def feedback(pred_id):
    row = db.get_prediction_by_id(pred_id)
    if row is None or row["user_id"] != session["user_id"]:
        flash("Prediction not found.", "error")
        return redirect(url_for("dashboard"))

    existing = db.get_feedback_for_prediction(
        pred_id,
        session["user_id"]
    )

    if request.method == "POST":
        if existing:
            flash("You have already submitted feedback for this assessment.", "info")
            return redirect(url_for("feedback", pred_id=pred_id))

        rating = int(request.form["rating"])
        comment = request.form.get("comment", "").strip()

        db.save_feedback(pred_id, session["user_id"], rating, comment)

        flash("Thanks for your feedback!", "success")
        return redirect(url_for("dashboard"))

    return render_template(
        "feedback.html",
        row=row,
        existing=existing
    )


# ---------------------------------------------------------------
# 7. Dashboard
# ---------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    latest = db.get_latest_prediction_for_user(session["user_id"])
    history_count = len(db.get_predictions_for_user(session["user_id"]))

    health_score = None
    bmi_status = None
    glucose_status = None

    if latest:
        # Simple wellness score: higher = healthier
        if latest["prediction"] == 1:
            health_score = round(100 - latest["confidence"])
        else:
            health_score = round(latest["confidence"])

        bmi = latest["bmi"]
        if bmi < 18.5:
            bmi_status = "Underweight"
        elif bmi < 25:
            bmi_status = "Normal"
        elif bmi < 30:
            bmi_status = "Overweight"
        else:
            bmi_status = "Obese"

        glucose = latest["blood_glucose_level"]
        if glucose < 100:
            glucose_status = "Normal"
        elif glucose <= 140:
            glucose_status = "Elevated"
        else:
            glucose_status = "High"

    chat_history = db.get_chat_history(session["user_id"])
    return render_template(
        "dashboard.html",
        latest=latest,
        history_count=history_count,
        health_score=health_score,
        bmi_status=bmi_status,
        glucose_status=glucose_status,
        chat_history=chat_history, 
    )



# ---------------------------------------------------------------
# 8. AI Health Assistant
# ---------------------------------------------------------------
@app.route("/chatbot", methods=["POST"])
@login_required
def chatbot():
    user_message = request.json.get("message", "")
    latest = db.get_latest_prediction_for_user(session["user_id"])

    context = {"label": "Unknown", "confidence": "N/A", "bmi": "N/A", "glucose": "N/A"}
    if latest:
        context = {
            "label": "High Risk" if latest["prediction"] == 1 else "Low Risk",
            "confidence": latest["confidence"],
            "bmi": latest["bmi"],
            "glucose": latest["blood_glucose_level"],
        }
    reply = ask_health_assistant(user_message, context)
    db.save_chat_message(session["user_id"], "user", user_message)
    db.save_chat_message(session["user_id"], "bot", reply)
    return {"reply": reply}
    
@app.route("/chatbot/clear", methods=["POST"])
@login_required
def chatbot_clear():
    db.clear_chat_history(session["user_id"])
    return {"status": "ok"}

# ---------------------------------------------------------------
# 9. Prediction History
# ---------------------------------------------------------------
@app.route("/history")
@login_required
def history():
    rows = db.get_predictions_for_user(session["user_id"])
    return render_template("history.html", rows=rows)


# ---------------------------------------------------------------
# 10. Download PDF Report
# ---------------------------------------------------------------
@app.route("/download-report/<int:pred_id>")
@login_required
def download_report(pred_id):
    row = db.get_prediction_by_id(pred_id)
    if row is None or row["user_id"] != session["user_id"]:
        flash("Prediction not found.", "error")
        return redirect(url_for("dashboard"))

    reasons = row["top_reasons"].split("||")
    pdf_buffer = generate_report_pdf(row, reasons)

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"DiaCare_Report_{pred_id}.pdf",
    )


if __name__ == "__main__":
    app.run(debug=True)
