# Database operations for detections and repairs CSV files
# Handles all CSV read/write operations for the Pothole Detection System
# Author: Hasan Nayon

import csv
import os
from datetime import datetime, timedelta
from config import DETECTIONS_CSV, REPAIRS_CSV

def init_csv_files():
    """Initialize CSV files with headers if they don't exist"""
    if not os.path.exists(DETECTIONS_CSV):
        with open(DETECTIONS_CSV, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['ID', 'Timestamp', 'Image_Path', 'Latitude', 'Longitude', 'Detection_Type', 'Confidence'])
    
    if not os.path.exists(REPAIRS_CSV):
        with open(REPAIRS_CSV, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['ID', 'Timestamp', 'Image_Path', 'Latitude', 'Longitude', 'Detection_Type', 'Confidence', 'Repair_Date', 'Technician', 'Notes'])

def get_next_detection_id():
    """Get the next available detection ID"""
    max_id = 0
    for csv_file in [DETECTIONS_CSV, REPAIRS_CSV]:
        if os.path.exists(csv_file):
            with open(csv_file, 'r') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        id_val = int(row.get('ID', 0))
                        if id_val > max_id:
                            max_id = id_val
                    except:
                        pass
    return max_id + 1

def add_detection(image_path, latitude, longitude, detection_type, confidence):
    """Add a new detection to detections.csv"""
    detection_id = get_next_detection_id()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(DETECTIONS_CSV, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([detection_id, timestamp, image_path, latitude, longitude, detection_type, confidence])
    
    return detection_id

def get_all_detections():
    """Read all active detections from detections.csv"""
    detections = []
    if os.path.exists(DETECTIONS_CSV):
        with open(DETECTIONS_CSV, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    detections.append({
                        'id': int(row.get('ID', 0)),
                        'timestamp': row.get('Timestamp', ''),
                        'image_path': row.get('Image_Path', ''),
                        'lat': float(row.get('Latitude', 0) or 0),
                        'lng': float(row.get('Longitude', 0) or 0),
                        'type': row.get('Detection_Type', 'pothole'),
                        'confidence': float(row.get('Confidence', 0) or 0)
                    })
                except Exception as e:
                    print(f"Error parsing detection: {e}")
    return detections

def get_all_repairs():
    """Read all repairs from repairs.csv"""
    repairs = []
    if os.path.exists(REPAIRS_CSV):
        with open(REPAIRS_CSV, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    repairs.append({
                        'id': int(row.get('ID', 0)),
                        'timestamp': row.get('Timestamp', ''),
                        'image_path': row.get('Image_Path', ''),
                        'lat': float(row.get('Latitude', 0) or 0),
                        'lng': float(row.get('Longitude', 0) or 0),
                        'type': row.get('Detection_Type', 'pothole'),
                        'confidence': float(row.get('Confidence', 0) or 0),
                        'repair_date': row.get('Repair_Date', ''),
                        'technician': row.get('Technician', ''),
                        'notes': row.get('Notes', '')
                    })
                except Exception as e:
                    print(f"Error parsing repair: {e}")
    return repairs

def move_to_repairs(detection_id, technician='', notes=''):
    """Move a detection from detections.csv to repairs.csv"""
    detections = get_all_detections()
    detection = next((d for d in detections if d['id'] == detection_id), None)
    
    if not detection:
        return False, "Detection not found"
    
    # Add to repairs.csv
    repair_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(REPAIRS_CSV, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            detection['id'],
            detection['timestamp'],
            detection['image_path'],
            detection['lat'],
            detection['lng'],
            detection['type'],
            detection['confidence'],
            repair_date,
            technician,
            notes
        ])
    
    # Remove from detections.csv
    remaining = [d for d in detections if d['id'] != detection_id]
    with open(DETECTIONS_CSV, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['ID', 'Timestamp', 'Image_Path', 'Latitude', 'Longitude', 'Detection_Type', 'Confidence'])
        for d in remaining:
            writer.writerow([d['id'], d['timestamp'], d['image_path'], d['lat'], d['lng'], d['type'], d['confidence']])
    
    return True, f"{detection['type'].title()} #{detection_id} has been fixed!"

def get_detection_stats():
    """Calculate detection statistics from both CSVs"""
    detections = get_all_detections()
    repairs = get_all_repairs()
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    
    # Count by type
    total_potholes = sum(1 for d in detections if d['type'].lower() == 'pothole')
    total_cracks = sum(1 for d in detections if d['type'].lower() == 'crack')
    
    # Fixed counts
    fixed_potholes = sum(1 for r in repairs if r['type'].lower() == 'pothole')
    fixed_cracks = sum(1 for r in repairs if r['type'].lower() == 'crack')
    
    stats = {
        'total_detections': len(detections),
        'total_potholes': total_potholes,
        'total_cracks': total_cracks,
        'fixed_count': len(repairs),
        'fixed_potholes': fixed_potholes,
        'fixed_cracks': fixed_cracks,
        'avg_confidence': round(sum(d['confidence'] * 100 for d in detections) / len(detections), 1) if detections else 0,
        'high_severity': sum(1 for d in detections if d['confidence'] >= 0.8),
        'medium_severity': sum(1 for d in detections if 0.5 <= d['confidence'] < 0.8),
        'low_severity': sum(1 for d in detections if d['confidence'] < 0.5),
        'today_count': sum(1 for d in detections if d['timestamp'].startswith(str(today))),
        'week_count': len([d for d in detections if d['timestamp'][:10] >= str(week_ago)])
    }
    return stats
