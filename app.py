# Main Flask Application for Pothole Detection System
# Real-time road damage detection with YOLOv8, GPS tracking, and AI assistant
# Author: Hasan Nayon
# Repository: https://github.com/HasanNayon/geospatial-ai

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

# Import from modules
from config import (
    SECRET_KEY, UPLOAD_FOLDER, RESULT_FOLDER, DASHCAM_FOLDER,
    DETECTIONS_CSV, REPAIRS_CSV, DETECTION_CONFIDENCE, CAPTURE_COOLDOWN
)
from database import (
    init_csv_files, add_detection, get_all_detections, get_all_repairs,
    move_to_repairs, get_detection_stats
)
from utils import get_automatic_location, nearest_neighbor_path
from llm_assistant import process_chat_message

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize CSV files
init_csv_files()

# Load model lazily
model = None

def get_model():
    global model
    if model is None:
        print("Loading YOLO model...")
        model = YOLO("best.pt")
        model.fuse()
        print("Model loaded and optimized!")
    return model

# Store latest location from browser
latest_location = {
    'latitude': None, 
    'longitude': None,
    'source': 'none',
    'last_update': None
}

# ============= PAGE ROUTES =============

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/assistant")
def assistant():
    return render_template("assistant.html")

@app.route("/dashboard")
def dashboard():
    detections = get_all_detections()
    template_detections = [{
        'ID': d['id'],
        'Timestamp': d['timestamp'],
        'Image_Path': d['image_path'],
        'Latitude': d['lat'],
        'Longitude': d['lng'],
        'Detection_Type': d['type'],
        'Confidence': d['confidence']
    } for d in detections]
    return render_template("dashboard.html", detections=template_detections)

@app.route("/dashcam")
def dashcam():
    return render_template("dashcam.html")

@app.route("/detections")
def view_detections():
    detections = get_all_detections()
    template_detections = [{
        'Timestamp': d['timestamp'],
        'Image_Path': d['image_path'],
        'Latitude': d['lat'],
        'Longitude': d['lng'],
        'Detection_Type': d['type'],
        'Confidence': d['confidence']
    } for d in detections]
    return render_template('detections.html', detections=template_detections)

# ============= FILE SERVING ROUTES =============

@app.route("/Dataset/<path:filename>")
def serve_dataset(filename):
    return send_from_directory("Dataset", filename)

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

# ============= DETECTION ROUTES =============

@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return "No file found"

    image = request.files["image"]
    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    image.save(image_path)
    
    latitude = request.form.get('latitude', '0.0')
    longitude = request.form.get('longitude', '0.0')

    m = get_model()
    results = m.predict(image_path, conf=DETECTION_CONFIDENCE, save=True, 
                       project=RESULT_FOLDER, name="output", exist_ok=True, 
                       imgsz=640, verbose=False)

    detection_made = False
    detection_id = None
    for result in results:
        boxes = result.boxes
        for box in boxes:
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            class_names = ["pothole", "crack"]
            detection_type = class_names[cls] if cls < len(class_names) else "pothole"
            
            detection_id = add_detection(
                f'static/uploads/{image.filename}',
                latitude, longitude, detection_type, conf
            )
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

# ============= VIDEO FEED =============

last_capture_time = 0

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_frames():
    global last_capture_time
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 416)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 416)
    camera.set(cv2.CAP_PROP_FPS, 15)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    classNames = ["pothole"]
    m = get_model()
    frame_count = 0
    skip_frames = 2
    
    while True:
        success, frame = camera.read()
        if not success:
            break
        
        frame_count += 1
        
        if frame_count % skip_frames == 0:
            results = m(frame, stream=True, conf=DETECTION_CONFIDENCE, iou=0.5, 
                       imgsz=416, half=False, verbose=False)
        else:
            results = []
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 3)
                
                conf = math.ceil((box.conf[0] * 100)) / 100
                cls = int(box.cls[0])
                class_name = classNames[cls]
                label = f'{class_name} {conf}'
                
                t_size = cv2.getTextSize(label, 0, fontScale=1, thickness=2)[0]
                c2 = x1 + t_size[0], y1 - t_size[1] - 3
                cv2.rectangle(frame, (x1, y1), c2, [255, 0, 255], -1, cv2.LINE_AA)
                cv2.putText(frame, label, (x1, y1 - 2), 0, 1, [255, 255, 255], thickness=1, lineType=cv2.LINE_AA)
                
                current_time = datetime.now().timestamp()
                if current_time - last_capture_time > CAPTURE_COOLDOWN:
                    last_capture_time = current_time
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'pothole_{timestamp}.jpg'
                    filepath = os.path.join(DASHCAM_FOLDER, filename)
                    cv2.imwrite(filepath, frame)
                    
                    lat = latest_location.get('latitude', 0)
                    lng = latest_location.get('longitude', 0)
                    
                    detection_id = add_detection(filepath, lat or 0, lng or 0, class_name, float(conf))
                    
                    socketio.emit('detection_alert', {
                        'id': detection_id,
                        'timestamp': timestamp,
                        'confidence': float(conf),
                        'type': class_name,
                        'location': f"{lat}, {lng}" if lat and lng else "Unknown"
                    })
        
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
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
        
        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'pothole_{timestamp}.jpg'
        filepath = os.path.join(DASHCAM_FOLDER, filename)
        
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        
        m = get_model()
        results = m.predict(filepath, conf=0.5)
        
        detection_info = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                detection_type = "pothole"
                
                add_detection(filepath, latitude, longitude, detection_type, conf)
                
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

# ============= LOCATION HANDLING =============

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
    else:
        print("✗ Could not get automatic location")

def update_location_periodically():
    while True:
        threading.Event().wait(60)
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

# ============= API ROUTES =============

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Main chat endpoint for LLM assistant"""
    try:
        data = request.json
        user_message = data.get('message', '')
        history = data.get('history', [])
        
        result = process_chat_message(user_message, history)
        return jsonify(result)
    
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update-fix', methods=['POST'])
def api_update_fix():
    """Fix a detection - moves it from detections.csv to repairs.csv"""
    try:
        data = request.json
        detection_id = int(data.get('detection_id'))
        technician = data.get('technician', '')
        notes = data.get('notes', '')
        
        success, message = move_to_repairs(detection_id, technician, notes)
        
        if success:
            new_stats = get_detection_stats()
            return jsonify({
                'success': True, 
                'message': message,
                'new_stats': new_stats
            })
        else:
            return jsonify({'success': False, 'error': message}), 404
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """Get current detection statistics"""
    try:
        stats = get_detection_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/detection/<int:detection_id>', methods=['GET'])
def api_get_detection(detection_id):
    """Get a specific detection by ID"""
    try:
        detections = get_all_detections()
        detection = next((d for d in detections if d['id'] == detection_id), None)
        if detection:
            return jsonify({'success': True, 'detection': detection})
        else:
            return jsonify({'success': False, 'error': 'Detection not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/detections/risk/<risk_level>')
def api_get_by_risk(risk_level):
    """Get detections filtered by risk level"""
    try:
        detections = get_all_detections()
        
        if risk_level == 'high':
            filtered = [d for d in detections if d['confidence'] >= 0.8]
        elif risk_level == 'medium':
            filtered = [d for d in detections if 0.5 <= d['confidence'] < 0.8]
        elif risk_level == 'low':
            filtered = [d for d in detections if d['confidence'] < 0.5]
        else:
            filtered = detections
        
        return jsonify({
            'success': True, 
            'risk_level': risk_level,
            'count': len(filtered),
            'detections': sorted(filtered, key=lambda x: -x['confidence'])
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download-report')
def api_download_report():
    """Generate and download report CSV"""
    try:
        stats = get_detection_stats()
        detections = get_all_detections()
        
        report_file = 'report_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.csv'
        report_path = os.path.join('static', report_file)
        
        with open(report_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Pothole Detection System - Report'])
            writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow([])
            writer.writerow(['Summary Statistics'])
            writer.writerow(['Total Detections', stats['total_detections']])
            writer.writerow(['Potholes', stats['total_potholes']])
            writer.writerow(['Cracks', stats['total_cracks']])
            writer.writerow(['Average Confidence', f"{stats['avg_confidence']}%"])
            writer.writerow(['High Severity', stats['high_severity']])
            writer.writerow(['Medium Severity', stats['medium_severity']])
            writer.writerow(['Low Severity', stats['low_severity']])
            writer.writerow([])
            writer.writerow(['Detailed Detections'])
            writer.writerow(['ID', 'Type', 'Confidence', 'Latitude', 'Longitude', 'Timestamp'])
            for d in detections:
                writer.writerow([d['id'], d['type'], d['confidence'], d['lat'], d['lng'], d['timestamp']])
        
        return send_from_directory('static', report_file, as_attachment=True)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get-path', methods=['POST'])
def api_get_path():
    """Calculate shortest path for given number of detections"""
    try:
        data = request.json
        count = data.get('count', 10)
        detection_type = data.get('type', 'all')
        
        detections = get_all_detections()
        
        if detection_type != 'all':
            detections = [d for d in detections if d['type'].lower() == detection_type.lower()]
        
        priority_detections = sorted(detections, key=lambda x: -x['confidence'])[:count]
        
        if priority_detections:
            path_order, total_dist = nearest_neighbor_path(priority_detections)
            ordered_points = [priority_detections[i] for i in path_order]
            route_polyline = [[p['lat'], p['lng']] for p in ordered_points]
            
            return jsonify({
                'success': True,
                'data': {
                    'points': ordered_points,
                    'total_distance': round(total_dist, 2),
                    'estimated_time': f"{int(total_dist / 30 * 60)} mins",
                    'route_polyline': route_polyline
                }
            })
        else:
            return jsonify({'success': False, 'error': 'No detections found'}), 404
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ============= MAIN =============

if __name__ == "__main__":
    print("Initializing automatic location tracking...")
    initialize_location()
    
    location_thread = threading.Thread(target=update_location_periodically, daemon=True)
    location_thread.start()
    
    print("\n" + "="*60)
    print("🚀 Flask Server Starting...")
    print("📍 Dashboard: http://localhost:5000/dashboard")
    print("🤖 Assistant: http://localhost:5000/assistant")
    print("📹 Camera: http://localhost:5000/dashcam")
    print("="*60 + "\n")
    
    socketio.run(app, debug=False, host='0.0.0.0', port=5000, 
                allow_unsafe_werkzeug=True)
