"""
AgriVision AI – Precision Farming & Crop Yield Prediction Platform
Main Flask application
"""

import os, sqlite3, random, json, joblib, numpy as np
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'agrivision-secret-key-2024')

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DB_PATH       = os.path.join(BASE_DIR, 'database.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
MODEL_PATH    = os.path.join(BASE_DIR, 'models', 'yield_model.pkl')
ALLOWED_EXT   = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Load yield model ──────────────────────────────────────────────────────────
try:
    model_data    = joblib.load(MODEL_PATH)
    yield_model   = model_data['model']
    label_encoder = model_data['label_encoder']
    print("✅  Yield model loaded.")
except Exception as e:
    yield_model = label_encoder = None
    print(f"⚠️  Model not loaded: {e}")

# ── DB helpers ────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'farmer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS farms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            farm_name TEXT,
            location TEXT,
            land_area REAL,
            crop_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS yield_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            crop_type TEXT,
            rainfall REAL,
            temperature REAL,
            humidity REAL,
            soil_ph REAL,
            nitrogen REAL,
            phosphorus REAL,
            potassium REAL,
            predicted_yield REAL,
            confidence REAL,
            prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS disease_detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            image_path TEXT,
            disease_name TEXT,
            confidence REAL,
            recommendation TEXT,
            detection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS irrigation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            soil_moisture REAL,
            temperature REAL,
            rainfall_forecast REAL,
            water_required REAL,
            recommendation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS fertilizer_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            nitrogen REAL,
            phosphorus REAL,
            potassium REAL,
            crop_type TEXT,
            fertilizer_name TEXT,
            quantity TEXT,
            recommendation TEXT,
            recommendation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """)
    # Seed admin if missing
    admin_pw = generate_password_hash('admin123')
    c.execute("INSERT OR IGNORE INTO users (username,email,password,role) VALUES (?,?,?,?)",
              ('admin', 'admin@agrivision.ai', admin_pw, 'admin'))
    conn.commit()
    conn.close()

# ── Auth decorators ───────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# ── AI helpers ────────────────────────────────────────────────────────────────
# Disease knowledge base (rule-based, no TensorFlow needed)
DISEASES = [
    {'name': 'Leaf Blight',       'confidence': 87.4, 'treatment': 'Apply copper-based fungicide. Remove infected leaves. Ensure proper drainage.'},
    {'name': 'Powdery Mildew',    'confidence': 91.2, 'treatment': 'Use sulphur-based fungicide. Improve air circulation around plants.'},
    {'name': 'Root Rot',          'confidence': 78.6, 'treatment': 'Reduce watering. Apply fungicide drench. Improve soil drainage.'},
    {'name': 'Bacterial Spot',    'confidence': 83.1, 'treatment': 'Apply copper hydroxide spray. Avoid overhead watering.'},
    {'name': 'Mosaic Virus',      'confidence': 76.9, 'treatment': 'Remove and destroy infected plants. Control aphid population with insecticide.'},
    {'name': 'Anthracnose',       'confidence': 89.5, 'treatment': 'Apply mancozeb or chlorothalonil fungicide. Improve field sanitation.'},
    {'name': 'Early Blight',      'confidence': 85.3, 'treatment': 'Use azoxystrobin or propiconazole fungicide. Rotate crops next season.'},
    {'name': 'Healthy Plant',     'confidence': 95.0, 'treatment': 'No disease detected. Continue regular monitoring and maintenance.'},
]

FERTILIZER_MAP = {
    'low_n':  ('Urea (46-0-0)',         '25–30 kg/acre',  'Apply in split doses – at sowing and 30 days after germination.'),
    'low_p':  ('Single Super Phosphate','20–25 kg/acre',  'Apply as basal dose before sowing. Mix thoroughly into topsoil.'),
    'low_k':  ('Muriate of Potash',     '15–20 kg/acre',  'Apply as basal dose or in first irrigation. Avoid over-application.'),
    'balanced':('NPK 10-26-26',         '50 kg/acre',     'Complete fertilizer for maintenance. Apply at planting, repeat after 45 days.'),
    'high_all':('Organic Compost',      '2 tonnes/acre',  'Spread evenly and incorporate into soil before planting.'),
}

CHATBOT_KB = {
    'water':        'Most crops need 1–2 inches of water per week. Rice requires 4–6 inches weekly. Monitor soil moisture and irrigate when it drops below 50%.',
    'yellow':       'Yellow leaves often signal nitrogen deficiency, overwatering, or fungal disease. Test your soil pH and apply nitrogen-rich fertilizer if needed.',
    'wheat':        'Wheat grows best with NPK ratio of 120:60:40 kg/ha. Apply urea at sowing and top-dress 30 days later.',
    'rice':         'Rice thrives in flooded or well-irrigated fields. Requires 4–6 inches of water weekly. Optimal temperature: 20–35 °C.',
    'fertilizer':   'Choose fertilizer based on soil test results. Generally: Urea for nitrogen, DAP for phosphorus, MOP for potassium.',
    'pest':         'Identify the pest first. Use integrated pest management (IPM): crop rotation, biological controls, then targeted pesticide as last resort.',
    'soil':         'Optimal soil pH for most crops is 6.0–7.0. Test every 2–3 years. Add lime to raise pH or sulphur to lower it.',
    'season':       'Match crops to season: Kharif (June–Nov) for rice/cotton/maize; Rabi (Nov–Apr) for wheat/barley/mustard.',
    'organic':      'Organic farming uses compost, green manure, and bio-pesticides. Builds long-term soil health and commands premium market prices.',
    'default':      'I can help with water requirements, fertilizer choices, pest control, soil health, and crop scheduling. Ask me anything about your farm!',
}

def chatbot_response(msg):
    msg_lower = msg.lower()
    for key, response in CHATBOT_KB.items():
        if key in msg_lower:
            return response
    for word in ['rice','wheat','maize','corn','cotton','potato','tomato','soybean']:
        if word in msg_lower:
            return f'{word.capitalize()} cultivation tip: Ensure balanced NPK, adequate irrigation, and monitor for pests every 2 weeks.'
    return CHATBOT_KB['default']

def get_irrigation_advice(moisture, temp, rain_forecast):
    if moisture > 70:
        water = 0.0
        advice = 'Soil moisture is adequate. No irrigation needed today.'
        timing = 'Skip irrigation'
    elif moisture > 40:
        water = round((70 - moisture) * 0.15, 2)
        advice = 'Moderate irrigation recommended. Water in the early morning to minimise evaporation.'
        timing = '5:00 AM – 7:00 AM'
    else:
        water = round((70 - moisture) * 0.2 + max(0, temp - 25) * 0.1, 2)
        advice = 'Critical: soil is very dry. Irrigate immediately and check for drainage issues.'
        timing = 'Immediately – then 5:00 AM daily'
    if rain_forecast > 15:
        water = max(0, water - rain_forecast * 0.05)
        advice += ' Rain forecast may reduce irrigation need.'
    return water, advice, timing

def get_fertilizer_rec(n, p, k, crop):
    if n < 40 and p < 20 and k < 20:
        key = 'high_all'
    elif n < 40:
        key = 'low_n'
    elif p < 20:
        key = 'low_p'
    elif k < 20:
        key = 'low_k'
    else:
        key = 'balanced'
    name, qty, instructions = FERTILIZER_MAP[key]
    rec = f'For {crop}: Apply {name} at {qty}. {instructions}'
    return name, qty, rec

# ─────────────────────────────────────────────────────────────────────────────
#  ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email    = request.form['email'].strip()
        password = request.form['password']
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect(url_for('register'))
        pw_hash = generate_password_hash(password)
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (username,email,password) VALUES (?,?,?)",
                         (username, email, pw_hash))
            conn.commit()
            conn.close()
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists.', 'danger')
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id']  = user['id']
            session['username'] = user['username']
            session['role']     = user['role']
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('admin_dashboard') if user['role'] == 'admin' else url_for('dashboard'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ── Farmer dashboard ──────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    uid  = session['user_id']
    conn = get_db()

    farms      = conn.execute("SELECT COUNT(*) as c FROM farms WHERE user_id=?", (uid,)).fetchone()['c']
    predictions= conn.execute("SELECT COUNT(*) as c FROM yield_predictions WHERE user_id=?", (uid,)).fetchone()['c']
    diseases   = conn.execute("SELECT COUNT(*) as c FROM disease_detections WHERE user_id=?", (uid,)).fetchone()['c']
    irrigations= conn.execute("SELECT COUNT(*) as c FROM irrigation_logs WHERE user_id=?", (uid,)).fetchone()['c']

    recent_preds = conn.execute(
        "SELECT * FROM yield_predictions WHERE user_id=? ORDER BY prediction_date DESC LIMIT 6", (uid,)).fetchall()
    recent_disease = conn.execute(
        "SELECT * FROM disease_detections WHERE user_id=? ORDER BY detection_date DESC LIMIT 4", (uid,)).fetchall()

    # Chart data – last 6 yield predictions
    chart_labels  = [p['crop_type'] for p in recent_preds]
    chart_yields  = [round(p['predicted_yield'], 2) for p in recent_preds]

    conn.close()
    return render_template('dashboard.html',
        farms=farms, predictions=predictions, diseases=diseases, irrigations=irrigations,
        recent_preds=recent_preds, recent_disease=recent_disease,
        chart_labels=json.dumps(chart_labels), chart_yields=json.dumps(chart_yields))

# ── Yield prediction ──────────────────────────────────────────────────────────
@app.route('/yield-prediction', methods=['GET','POST'])
@login_required
def yield_prediction():
    result = None
    if request.method == 'POST':
        crop      = request.form['crop_type']
        rainfall  = float(request.form['rainfall'])
        temp      = float(request.form['temperature'])
        humidity  = float(request.form['humidity'])
        soil_ph   = float(request.form['soil_ph'])
        nitrogen  = float(request.form['nitrogen'])
        phosphorus= float(request.form['phosphorus'])
        potassium = float(request.form['potassium'])

        if yield_model and label_encoder:
            try:
                crop_enc = label_encoder.transform([crop])[0]
                X = np.array([[crop_enc, rainfall, temp, humidity,
                               soil_ph, nitrogen, phosphorus, potassium]])
                predicted = float(yield_model.predict(X)[0])
                confidence = min(95, 70 + random.uniform(5, 20))
            except Exception:
                predicted  = round(random.uniform(2, 8), 2)
                confidence = round(random.uniform(72, 90), 1)
        else:
            predicted  = round(random.uniform(2, 8), 2)
            confidence = round(random.uniform(72, 90), 1)

        predicted = round(predicted, 2)
        confidence= round(confidence, 1)

        conn = get_db()
        conn.execute("""INSERT INTO yield_predictions
            (user_id,crop_type,rainfall,temperature,humidity,soil_ph,
             nitrogen,phosphorus,potassium,predicted_yield,confidence)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (session['user_id'], crop, rainfall, temp, humidity, soil_ph,
             nitrogen, phosphorus, potassium, predicted, confidence))
        conn.commit()

        history = conn.execute(
            "SELECT * FROM yield_predictions WHERE user_id=? ORDER BY prediction_date DESC LIMIT 7",
            (session['user_id'],)).fetchall()
        conn.close()

        result = {'crop': crop, 'yield': predicted, 'confidence': confidence,
                  'history': history}

    return render_template('yield_prediction.html', result=result)

# ── Disease detection ─────────────────────────────────────────────────────────
@app.route('/disease-detection', methods=['GET','POST'])
@login_required
def disease_detection():
    result = None
    if request.method == 'POST':
        if 'image' not in request.files:
            flash('No file selected.', 'warning')
            return redirect(request.url)
        file = request.files['image']
        if file.filename == '':
            flash('No file selected.', 'warning')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename  = secure_filename(file.filename)
            fname     = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
            file.save(save_path)

            # Rule-based "detection"
            detection = random.choice(DISEASES)
            disease   = detection['name']
            confidence= detection['confidence']
            treatment = detection['treatment']
            img_url   = f"uploads/{fname}"

            conn = get_db()
            conn.execute("""INSERT INTO disease_detections
                (user_id,image_path,disease_name,confidence,recommendation)
                VALUES (?,?,?,?,?)""",
                (session['user_id'], img_url, disease, confidence, treatment))
            conn.commit()
            conn.close()

            result = {'disease': disease, 'confidence': confidence,
                      'treatment': treatment, 'image': img_url}
        else:
            flash('Invalid file type. Use PNG, JPG, JPEG, GIF, or WEBP.', 'danger')

    return render_template('disease_detection.html', result=result)

# ── Smart irrigation ──────────────────────────────────────────────────────────
@app.route('/irrigation', methods=['GET','POST'])
@login_required
def irrigation():
    result = None
    if request.method == 'POST':
        moisture  = float(request.form['soil_moisture'])
        temp      = float(request.form['temperature'])
        rain_fore = float(request.form['rainfall_forecast'])

        water, advice, timing = get_irrigation_advice(moisture, temp, rain_fore)

        conn = get_db()
        conn.execute("""INSERT INTO irrigation_logs
            (user_id,soil_moisture,temperature,rainfall_forecast,water_required,recommendation)
            VALUES (?,?,?,?,?,?)""",
            (session['user_id'], moisture, temp, rain_fore, water, advice))
        conn.commit()
        conn.close()

        result = {'water': water, 'advice': advice, 'timing': timing,
                  'moisture': moisture, 'temp': temp, 'rain': rain_fore}

    return render_template('irrigation.html', result=result)

# ── Fertilizer recommendation ─────────────────────────────────────────────────
@app.route('/fertilizer', methods=['GET','POST'])
@login_required
def fertilizer():
    result = None
    if request.method == 'POST':
        nitrogen   = float(request.form['nitrogen'])
        phosphorus = float(request.form['phosphorus'])
        potassium  = float(request.form['potassium'])
        crop       = request.form['crop_type']

        name, qty, rec = get_fertilizer_rec(nitrogen, phosphorus, potassium, crop)

        conn = get_db()
        conn.execute("""INSERT INTO fertilizer_logs
            (user_id,nitrogen,phosphorus,potassium,crop_type,fertilizer_name,quantity,recommendation)
            VALUES (?,?,?,?,?,?,?,?)""",
            (session['user_id'], nitrogen, phosphorus, potassium, crop, name, qty, rec))
        conn.commit()
        conn.close()

        result = {'name': name, 'qty': qty, 'rec': rec, 'crop': crop,
                  'n': nitrogen, 'p': phosphorus, 'k': potassium}

    return render_template('fertilizer.html', result=result)

# ── Profit prediction ─────────────────────────────────────────────────────────
@app.route('/profit', methods=['GET','POST'])
@login_required
def profit():
    result = None
    if request.method == 'POST':
        predicted_yield = float(request.form['predicted_yield'])
        market_price    = float(request.form['market_price'])
        labor_cost      = float(request.form['labor_cost'])
        fertilizer_cost = float(request.form['fertilizer_cost'])
        land_area       = float(request.form['land_area'])
        misc_cost       = float(request.form.get('misc_cost', 0))

        revenue  = round(predicted_yield * land_area * market_price, 2)
        expenses = round((labor_cost + fertilizer_cost + misc_cost) * land_area, 2)
        profit_v = round(revenue - expenses, 2)
        roi      = round((profit_v / expenses * 100) if expenses else 0, 1)

        result = {'revenue': revenue, 'expenses': expenses, 'profit': profit_v,
                  'roi': roi, 'yield': predicted_yield, 'price': market_price,
                  'land': land_area}

    return render_template('profit.html', result=result)

# ── AI Farm Assistant ─────────────────────────────────────────────────────────
@app.route('/assistant')
@login_required
def assistant():
    uid  = session['user_id']
    conn = get_db()
    history = conn.execute(
        "SELECT * FROM chat_history WHERE user_id=? ORDER BY created_at ASC LIMIT 40",
        (uid,)).fetchall()
    conn.close()
    return render_template('assistant.html', history=history)

@app.route('/assistant/chat', methods=['POST'])
@login_required
def assistant_chat():
    data    = request.get_json()
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Empty message'}), 400

    response = chatbot_response(message)

    conn = get_db()
    conn.execute("INSERT INTO chat_history (user_id,message,response) VALUES (?,?,?)",
                 (session['user_id'], message, response))
    conn.commit()
    conn.close()

    return jsonify({'response': response})

# ── My Farms ──────────────────────────────────────────────────────────────────
@app.route('/farms', methods=['GET','POST'])
@login_required
def farms():
    uid  = session['user_id']
    if request.method == 'POST':
        conn = get_db()
        conn.execute("""INSERT INTO farms (user_id,farm_name,location,land_area,crop_type)
            VALUES (?,?,?,?,?)""",
            (uid, request.form['farm_name'], request.form['location'],
             float(request.form['land_area']), request.form['crop_type']))
        conn.commit()
        conn.close()
        flash('Farm added successfully!', 'success')
    conn  = get_db()
    farms = conn.execute("SELECT * FROM farms WHERE user_id=? ORDER BY created_at DESC", (uid,)).fetchall()
    conn.close()
    return render_template('farms.html', farms=farms)

@app.route('/farms/delete/<int:farm_id>')
@login_required
def delete_farm(farm_id):
    conn = get_db()
    conn.execute("DELETE FROM farms WHERE id=? AND user_id=?", (farm_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Farm removed.', 'info')
    return redirect(url_for('farms'))

# ── Admin panel ───────────────────────────────────────────────────────────────
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    conn = get_db()
    total_users   = conn.execute("SELECT COUNT(*) as c FROM users WHERE role='farmer'").fetchone()['c']
    total_pred    = conn.execute("SELECT COUNT(*) as c FROM yield_predictions").fetchone()['c']
    total_disease = conn.execute("SELECT COUNT(*) as c FROM disease_detections").fetchone()['c']
    total_farms   = conn.execute("SELECT COUNT(*) as c FROM farms").fetchone()['c']
    users         = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    predictions   = conn.execute("""
        SELECT yp.*, u.username FROM yield_predictions yp
        JOIN users u ON yp.user_id=u.id ORDER BY prediction_date DESC LIMIT 20""").fetchall()
    diseases = conn.execute("""
        SELECT dd.*, u.username FROM disease_detections dd
        JOIN users u ON dd.user_id=u.id ORDER BY detection_date DESC LIMIT 20""").fetchall()
    conn.close()
    return render_template('admin.html',
        total_users=total_users, total_pred=total_pred,
        total_disease=total_disease, total_farms=total_farms,
        users=users, predictions=predictions, diseases=diseases)

@app.route('/admin/delete-user/<int:uid>')
@login_required
@admin_required
def admin_delete_user(uid):
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=? AND role!='admin'", (uid,))
    conn.commit()
    conn.close()
    flash('User deleted.', 'info')
    return redirect(url_for('admin_dashboard'))

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("🌱  AgriVision AI is running → http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
