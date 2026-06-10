# 🌱 AgriVision AI

**AI-Powered Precision Farming & Crop Yield Prediction Platform**

A full-stack Flask web application that helps farmers make data-driven decisions
using machine learning — from yield prediction and disease detection to smart
irrigation, fertilizer recommendations, and profit forecasting.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🌾 **Yield Prediction** | Random Forest ML model trained on 1,000+ agricultural data points |
| 🔬 **Disease Detection** | Upload a plant photo for instant AI diagnosis |
| 💧 **Smart Irrigation** | Water requirement calculator based on soil moisture & weather |
| 🌿 **Fertilizer Advisor** | NPK-based personalised fertilizer recommendations |
| 💰 **Profit Predictor** | Revenue, expenses & ROI calculator with charts |
| 🤖 **Farm Assistant** | 24/7 AI chatbot with farming knowledge base |
| 📊 **Farmer Dashboard** | Charts, stats, and activity history |
| 🛡️ **Admin Panel** | User management, platform analytics, report viewing |

---

## 🚀 Quick Start

### 1. Clone / download the project

```bash
git clone https://github.com/yourname/agrivision-ai.git
cd AgriVisionAI
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Train the ML model (one-time setup)

```bash
python train_model.py
```

This generates `models/yield_model.pkl`.

### 5. Run the application

```bash
python app.py
```

Open your browser at **http://127.0.0.1:5000**

---

## 🔑 Default Credentials

| Role  | Username | Password  |
|-------|----------|-----------|
| Admin | `admin`  | `admin123` |

Create a farmer account via the **Register** page.

---

## 📁 Project Structure

```
AgriVisionAI/
│
├── app.py                  ← Main Flask application
├── train_model.py          ← ML model training script
├── database.db             ← SQLite database (auto-created)
├── requirements.txt
├── README.md
│
├── models/
│   └── yield_model.pkl     ← Trained Random Forest model
│
├── templates/
│   ├── base.html           ← Base layout with sidebar
│   ├── index.html          ← Landing page
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html      ← Farmer dashboard
│   ├── yield_prediction.html
│   ├── disease_detection.html
│   ├── irrigation.html
│   ├── fertilizer.html
│   ├── profit.html
│   ├── assistant.html      ← AI chatbot
│   ├── farms.html
│   └── admin.html
│
└── static/
    ├── css/style.css
    ├── js/app.js
    ├── images/
    └── uploads/            ← User-uploaded plant images
```

---

## 🛠️ Technology Stack

- **Backend:** Python 3.9+, Flask 2.x
- **Database:** SQLite (via Python's built-in `sqlite3`)
- **ML/AI:** Scikit-learn (Random Forest), rule-based disease & chatbot engine
- **Frontend:** HTML5, CSS3, Bootstrap 5, Chart.js
- **Auth:** Werkzeug password hashing, Flask sessions

---

## 🌐 Deployment on Render

1. Push your project to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Set **Build Command:** `pip install -r requirements.txt && python train_model.py`
4. Set **Start Command:** `python app.py`
5. Add environment variable: `SECRET_KEY` = (a long random string)

> Note: For persistent file storage on Render, configure a Disk and update
> `UPLOAD_FOLDER` and `DB_PATH` to point to the mounted disk path.

---

## 📝 Environment Variables

| Variable     | Default                        | Description                   |
|--------------|--------------------------------|-------------------------------|
| `SECRET_KEY` | `agrivision-secret-key-2024`   | Flask session secret (change in prod!) |

---

## 📜 License

MIT License — free to use for education, personal projects, and startup MVPs.

---

*Built with ❤️ for farmers everywhere · AgriVision AI 2024*
