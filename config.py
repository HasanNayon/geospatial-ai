# Configuration settings for Pothole Detection System
# Author: Hasan Nayon
# Repository: https://github.com/HasanNayon/geospatial-ai

import os

# Groq API Configuration
# Get your API key from: https://console.groq.com/keys
GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Flask Configuration
SECRET_KEY = 'pothole-detection-secret'

# File paths
UPLOAD_FOLDER = "static/uploads"
RESULT_FOLDER = "static/results"
DASHCAM_FOLDER = "static/dashcam_captures"
DETECTIONS_CSV = "detections.csv"
REPAIRS_CSV = "repairs.csv"

# Detection settings
DETECTION_CONFIDENCE = 0.4
CAPTURE_COOLDOWN = 5  # seconds between automatic captures

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)
os.makedirs(DASHCAM_FOLDER, exist_ok=True)
