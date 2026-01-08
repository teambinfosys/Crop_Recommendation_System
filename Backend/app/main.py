from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np
import pandas as pd
import os
from app.services import get_coordinates, get_weather_data
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Crop Recommendation System API",
    description="Backend for ML-based crop recommendation",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Allow all frontends (for development)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Load Model and Encoders
# Load Model and Encoders
MODEL_PATH = r"C:\Users\Admin\Desktop\Crop_Recommendation_System\Backend\ml\models\crop_model.pkl"
ENCODER_PATH = r"C:\Users\Admin\Desktop\Crop_Recommendation_System\Backend\ml\models\crop_encoder.pkl"

model = None
crop_encoder = None

# Hardcoded Mappings (from Notebook)
SOIL_MAPPING = {
    'Alluvial': 0, 'Black Soil': 1, 'Clay': 2, 'Clay Loam': 3, 
    'Coastal Sandy': 4, 'Loamy': 5, 'Red Soil': 6, 'Sandy': 7, 'Sandy Loam': 8
}
SEASON_MAPPING = {
    'Kharif': 0, 'Rabi': 1, 'Zayad': 2
}

@app.on_event("startup")
def load_model():
    global model, crop_encoder
    try:
        if os.path.exists(MODEL_PATH):
            model = joblib.load(MODEL_PATH)
            print("Model loaded successfully.")
        else:
            print(f"Model file not found at {MODEL_PATH}")
            
        if os.path.exists(ENCODER_PATH):
            crop_encoder = joblib.load(ENCODER_PATH)
            print("Crop encoder loaded successfully.")
        else:
            print(f"Crop encoder not found at {ENCODER_PATH}")
    except Exception as e:
        print(f"Error loading model: {e}")

class PredictionRequest(BaseModel):
    nitrogen: int
    phosphorus: int
    potassium: int
    ph: float
    soil: str
    season: str
    location: str # "State, City, Village"

@app.get("/")
def root():
    return {"message": "Crop Recommendation System Backend is running"}

@app.post("/predict")
def predict_crop(request: PredictionRequest):
    if not model or not crop_encoder:
        raise HTTPException(status_code=500, detail="Model not loaded")

    # 1. Get Location Coordinates
    lat, lon = get_coordinates(request.location)
    if lat is None:
        raise HTTPException(status_code=400, detail="Location not found")

    # 2. Get Historical Weather Data
    weather = get_weather_data(lat, lon, request.season)
    
    # 3. Encode Inputs
    soil_cleaned = request.soil.strip().title()
    season_cleaned = request.season.strip().title()
    
    if soil_cleaned not in SOIL_MAPPING:
        # Fuzzy match or default? For now, strict.
        raise HTTPException(status_code=400, detail=f"Invalid soil type. Allowed: {list(SOIL_MAPPING.keys())}")
        
    if season_cleaned not in SEASON_MAPPING:
         raise HTTPException(status_code=400, detail=f"Invalid season. Allowed: {list(SEASON_MAPPING.keys())}")
         
    soil_val = SOIL_MAPPING[soil_cleaned]
    season_val = SEASON_MAPPING[season_cleaned]

    # 4. Prepare Input Vector (Order must match model.feature_names_in_)
    # Model expects: ['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']
    
    features = pd.DataFrame([{
        "N": request.nitrogen,
        "P": request.phosphorus,
        "K": request.potassium,
        "temperature": weather['temperature'],
        "humidity": weather['humidity'],
        "ph": request.ph,
        "rainfall": weather['rainfall']
    }])
    
    # 5. Predict
    probabilities = model.predict_proba(features)[0]
    top3_indices = np.argsort(probabilities)[-3:][::-1]
    
    recommendations = []
    for idx in top3_indices:
        crop_name = crop_encoder.inverse_transform([idx])[0]
        confidence = round(probabilities[idx] * 100, 2)
        if confidence > 0: # Only return meaningful predictions
            recommendations.append({
                "crop": crop_name,
                "confidence": confidence
            })
            
    return {
        "location": request.location,
        "weather_used": weather,
        "recommendations": recommendations
    }

