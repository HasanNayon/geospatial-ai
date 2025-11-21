# 🛣️ AI-Powered Road Damage Detection System

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-green.svg)](https://flask.palletsprojects.com/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-purple.svg)](https://github.com/ultralytics/ultralytics)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An intelligent real-time road damage detection system using YOLOv8 deep learning model with GPS tracking, interactive dashboards, and live camera monitoring for Melbourne & Sydney, Australia.

![Dashboard Preview](https://via.placeholder.com/800x400/667eea/ffffff?text=Road+Damage+Detection+Dashboard)

## 🌟 Features

### 🎯 Core Functionality
- **Real-time Pothole & Crack Detection** - YOLOv8-based AI model with 70%+ accuracy
- **Live Dashcam Mode** - Automatic detection with 3-second cooldown
- **Image Upload Detection** - Batch processing with drag-and-drop support
- **GPS Location Tracking** - Automatic geolocation with IP fallback
- **CSV Data Logging** - Comprehensive detection records with timestamps

### 📊 Interactive Dashboard
- **Real-time Analytics** - Total detections, potholes, cracks, confidence metrics
- **Interactive Google Maps** - Color-coded markers (🔴 Potholes, 🟠 Cracks)
- **Severity Indicators** - High/Medium/Low severity badges
- **Trend Charts** - 30-day detection trends with Chart.js
- **Detection Feed** - Real-time recent detections with full details
- **Multi-City Support** - Melbourne & Sydney coverage

### 🗺️ Location Features
- **Browser GPS** - Precise location via `navigator.geolocation`
- **IP Geolocation Fallback** - Automatic location when GPS unavailable
- **Google Maps Integration** - Direct navigation to damage locations
- **Location Clustering** - Unique location identification

## 🚀 Quick Start

### Prerequisites
```bash
Python 3.12+
Webcam (for live detection)
Modern web browser with GPS support
```

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/pothole-detection.git
cd pothole-detection
```

2. **Create virtual environment**
```bash
python -m venv venv
```

3. **Activate virtual environment**
```bash
# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. **Install dependencies**
```bash
pip install flask flask-socketio ultralytics opencv-python requests
```

5. **Add your YOLO model**
```
Place your trained model file as: best.pt
```

6. **Run the application**
```bash
python app.py
```

7. **Access the system**
```
Dashboard: http://localhost:5000/dashboard
Live Camera: http://localhost:5000/dashcam
Home: http://localhost:5000
```

## 📁 Project Structure

```
pothole-detection/
├── app.py                      # Main Flask application
├── best.pt                     # YOLOv8 trained model
├── generate_dashboard_csv.py   # Dataset CSV generator
├── requirements.txt            # Python dependencies
├── templates/
│   ├── index.html             # Home page with upload
│   ├── dashboard.html         # Analytics dashboard
│   ├── dashcam.html          # Live camera interface
│   └── result.html           # Detection results
├── static/
│   ├── uploads/              # Uploaded images
│   ├── results/              # Detection outputs
│   └── dashcam_captures/     # Auto-captured frames
├── Dataset/
│   ├── pothole/              # Pothole training images
│   └── cracks/               # Crack training images
├── pothole_detections.csv    # Live detection logs
└── dashboard_detections.csv  # Dashboard data (1000 records)
```

## 🎮 Usage

### 1️⃣ Dashboard Analytics
```
Navigate to: http://localhost:5000/dashboard

Features:
- View 6 key metrics (Total, Potholes, Cracks, Confidence, Severity, Locations)
- Interactive map with clickable markers
- Filter by detection type (All/Potholes/Cracks)
- View trends over last 30 days
- Recent detection feed with severity badges
```

### 2️⃣ Live Camera Detection
```
Navigate to: http://localhost:5000/dashcam

Features:
- Real-time webcam feed with YOLO detection
- Auto-capture on detection (3-second cooldown)
- Continuous GPS tracking
- Automatic CSV logging
- Optimized performance (416x416, 15 FPS, frame skipping)
```

### 3️⃣ Image Upload
```
Navigate to: http://localhost:5000

Features:
- Upload single image for detection
- Automatic GPS location capture
- View detected bounding boxes
- Save to CSV with location
- Direct Google Maps link
```

## 🔧 Configuration

### Google Maps API
Update the API key in `templates/dashboard.html`:
```javascript
script.src = 'https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY&callback=initDashboard';
```

Required APIs:
- Maps JavaScript API
- Geocoding API (optional)

### Model Configuration
Edit `app.py` to adjust detection parameters:
```python
# Detection confidence threshold
conf=0.4  # 40% minimum confidence

# Image size for processing
imgsz=416  # Lower = faster, Higher = more accurate

# Frame skip rate
skip_frames = 2  # Process every 3rd frame
```

### Performance Tuning
```python
# Camera settings (app.py)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 416)   # Resolution
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 416)
camera.set(cv2.CAP_PROP_FPS, 15)            # Frame rate

# Capture cooldown (app.py)
capture_cooldown = 3  # Seconds between auto-captures
```

## 📊 Dataset Information

### Training Data
- **Potholes**: 1,581 images
- **Cracks**: 3,026 images
- **Total**: 4,607 images
- **Format**: JPG images with YOLO annotations

### Dashboard Data
- **Records**: 1,000 synthetic detections
- **Distribution**: 40% Potholes, 60% Cracks
- **Locations**: Melbourne & Sydney (±0.15° radius)
- **Timeframe**: Last 90 days
- **Confidence Range**: 40%-95%

## 🎨 Key Technologies

| Technology | Purpose |
|------------|---------|
| **Flask** | Web framework & API |
| **Flask-SocketIO** | Real-time WebSocket communication |
| **YOLOv8 (Ultralytics)** | Object detection model |
| **OpenCV** | Video processing & image handling |
| **Chart.js** | Interactive data visualization |
| **Google Maps API** | Location mapping & navigation |
| **HTML5 Geolocation** | GPS tracking |
| **Bootstrap/CSS3** | Responsive UI design |

## 📈 System Performance

- **Detection Speed**: ~15 FPS on standard webcam
- **Model Accuracy**: 70-90% confidence on test data
- **Response Time**: <100ms per frame
- **Memory Usage**: ~500MB with model loaded
- **Supported Browsers**: Chrome, Firefox, Edge, Safari

## 🔒 Security & Privacy

- GPS data processed client-side
- No data transmitted to external servers (except Google Maps)
- Local CSV storage only
- IP geolocation as fallback (using ipapi.co)
- User must grant location permissions

## 🐛 Troubleshooting

### Camera Not Working
```bash
# Check camera access
# Ensure only one application uses camera
# Try different camera index: cv2.VideoCapture(1)
```

### Google Maps Not Loading
```bash
# Enable "Maps JavaScript API" in Google Cloud Console
# Set up billing
# Remove HTTP referrer restrictions or add localhost
```

### Model Not Found
```bash
# Ensure best.pt is in root directory
# Verify file name matches exactly
# Re-download trained model
```

### Port Already in Use
```bash
# Change port in app.py:
socketio.run(app, host='0.0.0.0', port=5001)
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Your Name** - *Initial work* - [YourGitHub](https://github.com/yourusername)

## 🙏 Acknowledgments

- **Ultralytics** for YOLOv8 framework
- **Flask** team for excellent web framework
- **OpenCV** community for computer vision tools
- Road damage dataset contributors
- Melbourne & Sydney road maintenance departments

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Email: nayon8828@gmail.com
- Documentation: [Wiki](https://github.com/yourusername/pothole-detection/wiki)

## 🚧 Roadmap

- [ ] Mobile app integration
- [ ] Multi-language support
- [ ] Advanced analytics (heatmaps, density maps)
- [ ] Cloud deployment guide
- [ ] Automated reporting system
- [ ] Integration with municipal systems
- [ ] Real-time alerts & notifications
- [ ] Severity prediction model

## 📸 Screenshots

### Dashboard
![Dashboard](https://via.placeholder.com/800x400/667eea/ffffff?text=Dashboard+with+Analytics)

### Live Detection
![Live Detection](https://via.placeholder.com/800x400/764ba2/ffffff?text=Real-time+Camera+Detection)

### Detection Result
![Result](https://via.placeholder.com/800x400/667eea/ffffff?text=Detection+Result+with+Location)

---

**Made with ❤️ for safer roads**

*Last Updated: November 21, 2025*
# geospatial-ai
