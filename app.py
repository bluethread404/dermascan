from flask import Flask, render_template, request, redirect, session, flash
import os
import numpy as np
from werkzeug.utils import secure_filename
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret_key"

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

try:
    print("Loading model...")
    model = load_model("model/vgg16_skin_cancer.h5")
    print("Model loaded successfully")
except Exception as e:
    print("Error loading model:")
    print(e)
    model = None

try:
    print("Connecting to MySQL...")

    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",  # Put your MySQL password here if needed
        database="skin_cancer_db1"
    )

    cursor = db.cursor(dictionary=True)

    print("Database connected successfully")

except Exception as e:
    print("Database connection error:")
    print(e)

# =========================
# Register Route
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role", "user") # Default to 'user' if not selected

        # Check if username already exists
        try:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                flash("Ce nom d'utilisateur est déjà pris.", "danger")
                return render_template("register.html")
            
            # Hash password
            hashed_password = generate_password_hash(password)

            # Insert new user
            query = "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)"
            cursor.execute(query, (username, hashed_password, role))
            db.commit()

            flash("Compte créé avec succès ! Veuillez vous connecter.", "success")
            return redirect("/")

        except Exception as e:
            print("Registration error:", e)
            flash("Une erreur est survenue lors de l'inscription.", "danger")
            return redirect("/register")

    return render_template("register.html")
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            query = "SELECT * FROM users WHERE username=%s"
            cursor.execute(query, (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user["password"], password):
                session["user"] = user["username"]
                session["role"] = user["role"]  # <--- ADD THIS LINE
                
                flash("Connexion réussie", "success")
                return redirect("/dashboard")
            else:
                flash("Nom d'utilisateur ou mot de passe invalide", "danger")

        except Exception as e:
            print(e)
            flash("Erreur de base de données", "danger")

    return render_template("login.html")

# =========================
# Dashboard
# =========================

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    return render_template("dashboard.html")

# =========================
# Prediction Route
# =========================

@app.route("/predict", methods=["GET", "POST"])
def predict():

    if "user" not in session:
        return redirect("/")

    if request.method == "POST":

        try:
            name = request.form["name"]
            age = request.form["age"]

            if "image" not in request.files:
                flash("No image uploaded", "warning")
                return redirect("/predict")

            file = request.files["image"]

            if file.filename == "":
                flash("Please choose an image", "warning")
                return redirect("/predict")

            # Secure filename
            filename = secure_filename(file.filename)

            filepath = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            # Save image
            file.save(filepath)

            # =========================
            # Image Processing
            # =========================

            img = image.load_img(
                filepath,
                target_size=(224, 224)
            )

            img_array = image.img_to_array(img)

            img_array = img_array / 255.0

            img_array = np.expand_dims(img_array, axis=0)

            # =========================
            # Prediction
            # =========================

            prediction = model.predict(img_array)

            pred = float(prediction[0][0])

            if pred > 0.5:
                result = "Malignant"
            else:
                result = "Benign"

            probability = round(pred * 100, 2)

            # =========================
            # Save to Database
            # =========================

            query = """
                INSERT INTO patients
                (name, age, result, probability, image_path)
                VALUES (%s, %s, %s, %s, %s)
            """

            values = (
                name,
                age,
                result,
                probability,
                filepath
            )

            cursor.execute(query, values)

            db.commit()
            last_id = cursor.lastrowid

            flash("Analysis completed successfully", "success")

            return render_template(
                "result.html",
                result=result,
                prob=probability,
                img=filepath,
                analysis_id=last_id,  
            )

        except Exception as e:

            print("Prediction error:")
            print(e)

            flash("System error occurred", "danger")

            return redirect("/predict")

    return render_template("predict.html")

# =========================
# Patients Route
# =========================

@app.route("/patients")
def patients():

    if "user" not in session:
        return redirect("/")

    try:
        query = """
            SELECT * FROM patients
            ORDER BY id DESC
        """

        cursor.execute(query)

        data = cursor.fetchall()

        return render_template(
            "patients.html",
            patients=data
        )

    except Exception as e:

        print(e)

        flash("Error loading patients", "danger")

        return redirect("/dashboard")
@app.route("/symptom_quiz/<int:analysis_id>")
def symptom_quiz(analysis_id):
    if "user" not in session:
        return redirect("/")

    # Pull the prediction context to display in the header
    try:
        cursor.execute(
            "SELECT result, probability FROM patients WHERE id = %s",
            (analysis_id,)
        )
        row = cursor.fetchone()
        result  = row["result"]      if row else "Malignant"
        prob    = row["probability"] if row else 0
    except Exception as e:
        print(e)
        result, prob = "Malignant", 0

    return render_template(
        "symptom_quiz.html",
        analysis_id=analysis_id,
        result=result,
        prob=prob,
    )


@app.route("/submit_quiz", methods=["POST"])
def submit_quiz():
    if "user" not in session:
        return redirect("/")

    try:
        analysis_id      = request.form.get("analysis_id")
        growth           = request.form.get("growth")
        itching          = request.form.get("itching")
        bleeding         = request.form.get("bleeding")
        pain             = request.form.get("pain")
        color_change     = request.form.get("color_change")
        irregular_border = request.form.get("irregular_border")
        systemic         = request.form.get("systemic_symptoms")
        risk_score       = int(request.form.get("risk_score", 0))

        # ── Risk tier logic ─────────────────────────────────
        if risk_score <= 3:
            risk_level = "Faible"
            risk_color = "#27ae60"
            risk_pct   = 22
            risk_desc  = "Aucun symptôme particulièrement préoccupant détecté."
            actions = [
                {
                    "text":  "Continuez à surveiller la lésion chaque mois",
                    "icon":  '<circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>',
                    "color": "#27ae60",
                    "bg":    "#edfbf3",
                },
                {
                    "text":  "Prenez des photos régulières pour comparer l'évolution",
                    "icon":  '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="12" cy="12" r="3"/>',
                    "color": "#27ae60",
                    "bg":    "#edfbf3",
                },
                {
                    "text":  "Mentionnez la lésion lors de votre prochain bilan dermatologique annuel",
                    "icon":  '<path d="M20 7H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
                    "color": "#27ae60",
                    "bg":    "#edfbf3",
                },
                {
                    "text":  "Appliquez une protection solaire SPF 50+ quotidiennement",
                    "icon":  '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>',
                    "color": "#27ae60",
                    "bg":    "#edfbf3",
                },
            ]
        elif risk_score <= 7:
            risk_level = "Modéré"
            risk_color = "#e8a020"
            risk_pct   = 55
            risk_desc  = "Certains signes méritent une attention médicale dans les prochaines semaines."
            actions = [
                {
                    "text":  "Prenez rendez-vous avec un dermatologue dans les 2 à 4 semaines",
                    "icon":  '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
                    "color": "#e8a020",
                    "bg":    "#fef9ec",
                },
                {
                    "text":  "Photographiez la lésion chaque semaine pour suivre les changements",
                    "icon":  '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="12" cy="12" r="3"/>',
                    "color": "#e8a020",
                    "bg":    "#fef9ec",
                },
                {
                    "text":  "Évitez toute manipulation, grattage ou frottement de la lésion",
                    "icon":  '<circle cx="12" cy="12" r="10"/><line x1="8" y1="8" x2="16" y2="16"/><line x1="16" y1="8" x2="8" y2="16"/>',
                    "color": "#e8a020",
                    "bg":    "#fef9ec",
                },
                {
                    "text":  "Signalez à votre médecin généraliste si les symptômes s'aggravent avant le rendez-vous",
                    "icon":  '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.77 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 8.91a16 16 0 0 0 6 6l.91-.91a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/>',
                    "color": "#e8a020",
                    "bg":    "#fef9ec",
                },
            ]
        else:
            risk_level = "Élevé"
            risk_color = "#e05555"
            risk_pct   = 90
            risk_desc  = "Plusieurs signes préoccupants ont été détectés. Une consultation urgente est recommandée."
            actions = [
                {
                    "text":  "Consultez un dermatologue en urgence — dans les 48 à 72 heures",
                    "icon":  '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
                    "color": "#e05555",
                    "bg":    "#fff0f0",
                },
                {
                    "text":  "Évitez tout contact ou grattage — ne manipulez pas la lésion",
                    "icon":  '<circle cx="12" cy="12" r="10"/><line x1="8" y1="8" x2="16" y2="16"/><line x1="16" y1="8" x2="8" y2="16"/>',
                    "color": "#e05555",
                    "bg":    "#fff0f0",
                },
                {
                    "text":  "Si des saignements surviennent, couvrez avec un pansement propre et sec",
                    "icon":  '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
                    "color": "#e05555",
                    "bg":    "#fff0f0",
                },
                {
                    "text":  "Prenez des photos quotidiennes jusqu'à votre consultation",
                    "icon":  '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="12" cy="12" r="3"/>',
                    "color": "#e05555",
                    "bg":    "#fff0f0",
                },
                {
                    "text":  "Informez votre médecin généraliste dès aujourd'hui pour une orientation rapide",
                    "icon":  '<path d="M20 7H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/>',
                    "color": "#e05555",
                    "bg":    "#fff0f0",
                },
            ]

        # ── Save to database ─────────────────────────────────
        cursor.execute(
            """
            INSERT INTO symptom_quiz
              (analysis_id, growth, itching, bleeding, pain,
               color_change, irregular_border, systemic_symptoms,
               risk_score, risk_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                analysis_id, growth, itching, bleeding, pain,
                color_change, irregular_border, systemic,
                risk_score, risk_level,
            ),
        )
        db.commit()

        return render_template(
            "quiz_result.html",
            risk_level=risk_level,
            risk_color=risk_color,
            risk_pct=risk_pct,
            risk_desc=risk_desc,
            actions=actions,
        )

    except Exception as e:
        print("Quiz submission error:", e)
        flash("Erreur lors de l'enregistrement du questionnaire.", "danger")
        return redirect("/dashboard")

# =========================
# Logout
# =========================

@app.route("/logout")
def logout():

    session.clear()

    flash("Logged out successfully", "info")

    return redirect("/")

# =========================
# Run App
# =========================

if __name__ == "__main__":

    print("Starting Flask server...")

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
# ============================================================
# ADD THESE ROUTES TO YOUR app.py
# ============================================================
# Also add this table to your MySQL database:
#
# CREATE TABLE symptom_quiz (
#   id            INT AUTO_INCREMENT PRIMARY KEY,
#   analysis_id   INT,
#   growth        VARCHAR(20),
#   itching       VARCHAR(20),
#   bleeding      VARCHAR(10),
#   pain          VARCHAR(20),
#   color_change  VARCHAR(20),
#   irregular_border VARCHAR(20),
#   systemic_symptoms VARCHAR(10),
#   risk_score    INT,
#   risk_level    VARCHAR(20),
#   created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );
# ============================================================


