from flask import Flask, render_template, request, send_from_directory, Response, jsonify
from flask_socketio import SocketIO, emit
from ultralytics import YOLO
import os
import cv2
import csv
from datetime import datetime
import base64
import math
import threading
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pothole-detection-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Function to get automatic location from IP
def get_automatic_location():
    try:
        # Try multiple IP geolocation services
        services = [
            'https://ipapi.co/json/',
            'http://ip-api.com/json/',
            'https://geolocation-db.com/json/'
        ]
        
        for service in services:
            try:
                response = requests.get(service, timeout=3)
                data = response.json()
                
                # Different services have different field names
                lat = data.get('latitude') or data.get('lat')
                lon = data.get('longitude') or data.get('lon')
                
                if lat and lon:
                    return {
                        'latitude': lat,
                        'longitude': lon,
                        'city': data.get('city', 'Unknown'),
                        'country': data.get('country_name') or data.get('country', 'Unknown')
                    }
            except:
                continue
        
        return None
    except Exception as e:
        print(f"Location error: {e}")
        return None

# Load model lazily (only when needed)
model = None

def get_model():
    global model
    if model is None:
        print("Loading YOLO model...")
        model = YOLO("best.pt")
        model.fuse()  # Fuse model layers for faster inference
        print("Model loaded and optimized!")
    return model

UPLOAD_FOLDER = "static/uploads"
RESULT_FOLDER = "static/results"
DASHCAM_FOLDER = "static/dashcam_captures"
CSV_FILE = "pothole_detections.csv"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)
os.makedirs(DASHCAM_FOLDER, exist_ok=True)

# Initialize CSV file with headers if it doesn't exist
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'Image_Path', 'Latitude', 'Longitude', 'Detection_Type', 'Confidence'])

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    # Read dashboard CSV data
    detections = []
    csv_file = 'dashboard_new.csv' if os.path.exists('dashboard_new.csv') else 'dashboard_detections.csv'
    if os.path.exists(csv_file):
        with open(csv_file, 'r') as file:
            reader = csv.DictReader(file)
            detections = list(reader)
    return render_template("dashboard.html", detections=detections)

@app.route("/dashcam")
def dashcam():
    return render_template("dashcam.html")

@app.route("/Dataset/<path:filename>")
def serve_dataset(filename):
    """Serve images from Dataset folder"""
    return send_from_directory("Dataset", filename)

@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return "No file found"

    image = request.files["image"]
    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    image.save(image_path)
    
    # Get location from form
    latitude = request.form.get('latitude', '0.0')
    longitude = request.form.get('longitude', '0.0')

    # Run detection with optimized settings
    m = get_model()
    results = m.predict(image_path, conf=0.4, save=True, project=RESULT_FOLDER, name="output", exist_ok=True, imgsz=640, verbose=False)

    # YOLO saves output image automatically
    output_image = os.path.join(RESULT_FOLDER, "output", image.filename)
    
    # Save detection to CSV if pothole or crack detected
    detection_made = False
    for result in results:
        boxes = result.boxes
        for box in boxes:
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            class_names = ["pothole", "crack"]
            detection_type = class_names[cls] if cls < len(class_names) else "pothole"
            
            # Save to CSV
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(CSV_FILE, 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([timestamp, f'static/uploads/{image.filename}', latitude, longitude, detection_type, conf])
            
            detection_made = True
            break
        if detection_made:
            break

    return render_template("result.html",
                           input_image=image.filename,
                           output_image=image.filename,
                           latitude=latitude,
                           longitude=longitude,
                           detection_saved=detection_made,
                           current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Global variables for automatic capture
last_capture_time = 0
capture_cooldown = 5  # seconds between automatic captures (reduced frequency)

def generate_frames():
    global last_capture_time
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 416)  # Lower resolution for faster processing
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 416)
    camera.set(cv2.CAP_PROP_FPS, 15)  # Lower FPS
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    classNames = ["pothole"]
    
    # Load model when video feed starts
    m = get_model()
    
    frame_count = 0
    skip_frames = 2  # Process every 3rd frame for performance
    
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            frame_count += 1
            detection_found = False
            
            # Skip frames for better performance
            if frame_count % skip_frames == 0:
                # Run YOLO detection with lighter settings
                results = m(frame, stream=True, conf=0.4, iou=0.5, imgsz=416, half=False, verbose=False)
            else:
                # Skip detection, just pass through frame
                results = []
            
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    detection_found = True
                    
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    
                    # Draw rectangle
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 3)
                    
                    # Get confidence and class
                    conf = math.ceil((box.conf[0] * 100)) / 100
                    cls = int(box.cls[0])
                    class_name = classNames[cls]
                    label = f'{class_name} {conf}'
                    
                    # Draw label
                    t_size = cv2.getTextSize(label, 0, fontScale=1, thickness=2)[0]
                    c2 = x1 + t_size[0], y1 - t_size[1] - 3
                    cv2.rectangle(frame, (x1, y1), c2, [255, 0, 255], -1, cv2.LINE_AA)
                    cv2.putText(frame, label, (x1, y1 - 2), 0, 1, [255, 255, 255], thickness=1, lineType=cv2.LINE_AA)
                    
                    # Automatic capture when detection found
                    current_time = datetime.now().timestamp()
                    if current_time - last_capture_time > capture_cooldown:
                        last_capture_time = current_time
                        # Save frame automatically
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f'pothole_{timestamp}.jpg'
                        filepath = os.path.join(DASHCAM_FOLDER, filename)
                        cv2.imwrite(filepath, frame)
                        
                        # Get location from latest browser update
                        lat = latest_location.get('latitude', 'N/A')
                        lng = latest_location.get('longitude', 'N/A')
                        
                        # Save to CSV with location
                        with open(CSV_FILE, 'a', newline='') as file:
                            writer = csv.writer(file)
                            writer.writerow([
                                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                filepath,
                                lat if lat else 'N/A',
                                lng if lng else 'N/A',
                                class_name,
                                float(conf)
                            ])
                        
                        # Notify browser about new detection
                        socketio.emit('detection_alert', {
                            'timestamp': timestamp,
                            'confidence': float(conf),
                            'type': class_name,
                            'location': f"{lat}, {lng}" if lat and lng else "N/A"
                        })
            
            # Encode frame with lower quality for faster streaming
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]  # Reduce JPEG quality
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)
            frame = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    camera.release()

@app.route('/capture_detection', methods=['POST'])
def capture_detection():
    try:
        data = request.json
        image_data = data.get('image')
        latitude = data.get('latitude', 'N/A')
        longitude = data.get('longitude', 'N/A')
        
        # Decode base64 image
        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'pothole_{timestamp}.jpg'
        filepath = os.path.join(DASHCAM_FOLDER, filename)
        
        # Save image
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        # Run detection on saved image
        results = model.predict(filepath, conf=0.5)
        
        detection_info = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                detection_type = "pothole"
                
                # Save to CSV
                with open(CSV_FILE, 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        filepath,
                        latitude,
                        longitude,
                        detection_type,
                        conf
                    ])
                
                detection_info.append({
                    'type': detection_type,
                    'confidence': conf,
                    'timestamp': timestamp
                })
        
        return jsonify({
            'success': True,
            'message': 'Detection captured successfully',
            'detections': detection_info,
            'filepath': filepath
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/detections')
def view_detections():
    detections = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r') as file:
            reader = csv.DictReader(file)
            detections = list(reader)
    return render_template('detections.html', detections=detections)

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


# Store latest location from browser with source tracking
latest_location = {
    'latitude': None, 
    'longitude': None,
    'source': 'none',
    'last_update': None
}

# Initialize location on startup
def initialize_location():
    global latest_location
    location = get_automatic_location()
    if location:
        latest_location['latitude'] = location['latitude']
        latest_location['longitude'] = location['longitude']
        latest_location['source'] = 'ip'
        latest_location['last_update'] = datetime.now()
        print(f"✓ Fallback location initialized: {location['city']}, {location['country']}")
        print(f"  Coordinates: {location['latitude']}, {location['longitude']}")
        print(f"  ⚠️  This is approximate. GPS will update as you move.")
    else:
        print("✗ Could not get automatic location")

# Update location periodically (every 60 seconds) - but don't override GPS
def update_location_periodically():
    while True:
        threading.Event().wait(60)  # Wait 60 seconds
        # Only update from IP if no GPS location received in last 2 minutes
        if latest_location['source'] != 'gps' or \
           (latest_location['last_update'] and \
            (datetime.now() - latest_location['last_update']).seconds > 120):
            location = get_automatic_location()
            if location:
                latest_location['latitude'] = location['latitude']
                latest_location['longitude'] = location['longitude']
                latest_location['source'] = 'ip'
                latest_location['last_update'] = datetime.now()

@socketio.on('update_location')
def handle_location(data):
    global latest_location
    latest_location['latitude'] = data.get('latitude')
    latest_location['longitude'] = data.get('longitude')
    latest_location['source'] = data.get('source', 'gps')
    latest_location['last_update'] = datetime.now()
    print(f"📍 GPS Location updated: {latest_location['latitude']:.6f}, {latest_location['longitude']:.6f}")

@socketio.on('detection_captured')
def handle_detection_notification(data):
    emit('new_detection', {'count': data.get('count', 0)}, broadcast=True)

@app.route('/get_current_location')
def get_current_location():
    return jsonify(latest_location)

if __name__ == "__main__":
    # Initialize location on startup
    print("Initializing automatic location tracking...")
    initialize_location()
    
    # Start background thread for periodic location updates
    location_thread = threading.Thread(target=update_location_periodically, daemon=True)
    location_thread.start()
    
    print("\n" + "="*60)
    print("🚀 Flask Server Starting...")
    print("📍 Dashboard: http://localhost:5000/dashboard")
    print("📹 Camera: http://localhost:5000/dashcam")
    print("="*60 + "\n")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True, use_reloader=False)
