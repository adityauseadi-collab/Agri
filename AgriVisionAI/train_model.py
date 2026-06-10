"""
Train and save the crop yield prediction model.
Run this script once to generate models/yield_model.pkl
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import joblib
import os

os.makedirs('models', exist_ok=True)

# ── Synthetic agricultural training data ─────────────────────────────────────
np.random.seed(42)
n = 1000

crop_types = ['Rice', 'Wheat', 'Maize', 'Sugarcane', 'Cotton',
              'Soybean', 'Tomato', 'Potato', 'Barley', 'Sorghum']

base_yield = {
    'Rice': 4.5, 'Wheat': 3.2, 'Maize': 5.0, 'Sugarcane': 70.0,
    'Cotton': 1.5, 'Soybean': 2.8, 'Tomato': 25.0, 'Potato': 20.0,
    'Barley': 2.9, 'Sorghum': 2.1
}

crops      = np.random.choice(crop_types, n)
rainfall   = np.random.uniform(300, 2000, n)
temp       = np.random.uniform(15, 40, n)
humidity   = np.random.uniform(30, 95, n)
soil_ph    = np.random.uniform(5.0, 8.5, n)
nitrogen   = np.random.uniform(10, 140, n)
phosphorus = np.random.uniform(5, 80, n)
potassium  = np.random.uniform(10, 100, n)

yields = []
for i in range(n):
    base = base_yield[crops[i]]
    factor = (
        0.0005 * rainfall[i]
        + 0.05 * (30 - abs(temp[i] - 25))
        + 0.01 * humidity[i]
        + 0.3 * (1 - abs(soil_ph[i] - 6.5) / 3)
        + 0.008 * nitrogen[i]
        + 0.005 * phosphorus[i]
        + 0.004 * potassium[i]
        + np.random.normal(0, 0.3)
    )
    yields.append(max(0.5, base * (0.6 + 0.4 * factor / 3)))

df = pd.DataFrame({
    'crop_type': crops, 'rainfall': rainfall, 'temperature': temp,
    'humidity': humidity, 'soil_ph': soil_ph, 'nitrogen': nitrogen,
    'phosphorus': phosphorus, 'potassium': potassium, 'yield': yields
})

# ── Encode crop labels ────────────────────────────────────────────────────────
le = LabelEncoder()
df['crop_encoded'] = le.fit_transform(df['crop_type'])

X = df[['crop_encoded','rainfall','temperature','humidity',
        'soil_ph','nitrogen','phosphorus','potassium']].values
y = df['yield'].values

model = RandomForestRegressor(n_estimators=150, random_state=42, n_jobs=-1)
model.fit(X, y)

joblib.dump({'model': model, 'label_encoder': le}, 'models/yield_model.pkl')
print("✅  Yield model saved → models/yield_model.pkl")
print(f"    Crops supported: {list(le.classes_)}")
