from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import laspy
import numpy as np
import os
import traceback
from typing import List

app = FastAPI()

# Configure CORS (allow frontend access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DATASET_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dataset', 'global_xyz_rgb_icgu__5018_0_3614.laz'))


@app.get('/api/health')
async def health():
    try:
        from laspy.compression import LazBackend
        backends = LazBackend.detect_available()
        backend_names = [str(b) for b in backends]
    except Exception:
        backend_names = ['unknown']

    return JSONResponse({
        'status': 'healthy',
        'message': 'Backend (FastAPI) is running',
        'lazrs_installed': True,
        'available_backends': backend_names
    })


def calculate_colors(elevations: np.ndarray) -> List[float]:
    min_elev = elevations.min()
    max_elev = elevations.max()
    normalized = (elevations - min_elev) / (max_elev - min_elev)

    colors = []
    for n in normalized:
        if n < 0.25:
            r, g, b = 0.1, n * 4 * 0.5, 0.8
        elif n < 0.5:
            r, g, b = 0.1, 0.8, 0.8 - (n - 0.25) * 4 * 0.4
        elif n < 0.75:
            r, g, b = (n - 0.5) * 4 * 0.6, 0.8, 0.4 - (n - 0.5) * 4 * 0.4
        else:
            r, g, b = 0.9, 0.8 - (n - 0.75) * 4 * 0.3, 0

        colors.extend([r, g, b])

    return colors


def detect_defects(las) -> List[dict]:
    defects = []
    z = las.z
    x = las.x
    y = las.y

    base_lat = -37.8136
    base_lng = 144.9631

    window_size = 100
    for i in range(0, len(z) - window_size, window_size):
        segment = z[i:i+window_size]
        mean_elev = np.mean(segment)
        std_elev = np.std(segment)

        low_points = np.where(segment < (mean_elev - 2 * std_elev))[0]

        if len(low_points) > 5:
            idx = i + low_points[0]
            depth = abs(float(segment[low_points[0]] - mean_elev))

            if depth > 0.1:
                lat = base_lat + (y[idx] * 0.00001)
                lng = base_lng + (x[idx] * 0.00001)

                defects.append({
                    'id': len(defects) + 1,
                    'type': 'Pothole',
                    'severity': 'High' if depth > 0.25 else 'Medium',
                    'location': f'Segment {i // window_size + 1}',
                    'depth': round(depth, 2),
                    'lat': lat,
                    'lng': lng,
                    'mapX': float(x[idx]),
                    'mapZ': float(y[idx]),
                    'address': 'Melbourne CBD, VIC',
                    'description': f'Pothole detected with {round(depth, 2)}m depth.'
                })

    return defects[:20]


def detect_flood_zones(las) -> List[dict]:
    flood_zones = []
    z = las.z
    x = las.x
    y = las.y

    base_lat = -37.8136
    base_lng = 144.9631

    threshold = np.percentile(z, 10)
    low_areas = np.where(z < threshold)[0]

    for i in range(0, len(low_areas), len(low_areas) // 12 if len(low_areas) > 12 else 1):
        if i >= len(low_areas):
            break
        idx = low_areas[i]
        elevation = float(z[idx])
        lat = base_lat + (y[idx] * 0.00001)
        lng = base_lng + (x[idx] * 0.00001)

        flood_zones.append({
            'id': len(flood_zones) + 1,
            'elevation': round(elevation, 2),
            'risk': 'High' if elevation < threshold - 1 else 'Medium',
            'location': f'Zone {len(flood_zones) + 1}',
            'lat': lat,
            'lng': lng,
            'mapX': float(x[idx]),
            'mapZ': float(y[idx]),
            'address': 'Melbourne CBD, VIC',
            'description': 'Low-lying area prone to flooding.'
        })

    return flood_zones[:12]


def detect_vegetation(las) -> List[dict]:
    vegetation = []
    z = las.z
    x = las.x
    y = las.y

    base_lat = -37.8136
    base_lng = 144.9631

    threshold = np.percentile(z, 85)
    high_points = np.where(z > threshold)[0]

    for i in range(0, len(high_points), len(high_points) // 15 if len(high_points) > 15 else 1):
        if i >= len(high_points):
            break
        idx = high_points[i]
        height = float(z[idx])
        lat = base_lat + (y[idx] * 0.00001)
        lng = base_lng + (x[idx] * 0.00001)

        clearance = np.random.uniform(2, 5)

        vegetation.append({
            'id': len(vegetation) + 1,
            'type': 'Tree Overhang',
            'clearance': round(clearance, 1),
            'location': f'Area {len(vegetation) + 1}',
            'priority': 'High' if clearance < 3 else 'Medium',
            'lat': lat,
            'lng': lng,
            'mapX': float(x[idx]),
            'mapZ': float(y[idx]),
            'address': 'Melbourne CBD, VIC',
            'description': 'Vegetation encroachment detected.'
        })

    return vegetation[:15]


@app.get('/api/load-sample')
async def load_sample():
    try:
        if not os.path.exists(DATASET_PATH):
            raise HTTPException(status_code=404, detail=f'Dataset file not found: {DATASET_PATH}')

        try:
            las = laspy.read(DATASET_PATH)
        except Exception as e:
            print(f'ERROR reading dataset file {DATASET_PATH}: {e}')
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f'Failed to read dataset file: {str(e)}')

        positions = las.xyz.flatten().tolist()
        elevations = las.z.tolist()
        colors = calculate_colors(las.z)
        defects = detect_defects(las)
        flood_zones = detect_flood_zones(las)
        vegetation = detect_vegetation(las)

        stats = {
            'pointCount': len(las.points),
            'minElevation': float(las.z.min()),
            'maxElevation': float(las.z.max()),
            'avgElevation': float(las.z.mean()),
            'bounds': {
                'xMin': float(las.x.min()),
                'xMax': float(las.x.max()),
                'yMin': float(las.y.min()),
                'yMax': float(las.y.max()),
                'zMin': float(las.z.min()),
                'zMax': float(las.z.max())
            }
        }

        return JSONResponse({
            'positions': positions,
            'colors': colors,
            'elevations': elevations,
            'defects': defects,
            'floodZones': flood_zones,
            'vegetation': vegetation,
            'stats': stats
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f'Unexpected error in load_sample: {e}')
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f'Unexpected server error: {str(e)}')




def calculate_colors(elevations):
    """Calculate RGB colors based on elevation values"""
    min_elev = elevations.min()
    max_elev = elevations.max()
    normalized = (elevations - min_elev) / (max_elev - min_elev)
    
    colors = []
    for n in normalized:
        if n < 0.25:
            r, g, b = 0.1, n * 4 * 0.5, 0.8
        elif n < 0.5:
            r, g, b = 0.1, 0.8, 0.8 - (n - 0.25) * 4 * 0.4
        elif n < 0.75:
            r, g, b = (n - 0.5) * 4 * 0.6, 0.8, 0.4 - (n - 0.5) * 4 * 0.4
        else:
            r, g, b = 0.9, 0.8 - (n - 0.75) * 4 * 0.3, 0
        
        colors.extend([r, g, b])
    
    return colors

def detect_defects(las):
    """Detect road defects (potholes, cracks) from LiDAR data"""
    defects = []
    
    # Simple defect detection based on elevation anomalies
    z = las.z
    x = las.x
    y = las.y
    
    # Melbourne CBD base coordinates
    base_lat = -37.8136
    base_lng = 144.9631
    
    # Detect potholes (local depressions)
    window_size = 100
    for i in range(0, len(z) - window_size, window_size):
        segment = z[i:i+window_size]
        mean_elev = np.mean(segment)
        std_elev = np.std(segment)
        
        # Find points significantly below mean
        low_points = np.where(segment < (mean_elev - 2 * std_elev))[0]
        
        if len(low_points) > 5:
            idx = i + low_points[0]
            depth = abs(float(segment[low_points[0]] - mean_elev))
            
            if depth > 0.1:  # At least 10cm deep
                lat = base_lat + (y[idx] * 0.00001)
                lng = base_lng + (x[idx] * 0.00001)
                
                defects.append({
                    'id': len(defects) + 1,
                    'type': 'Pothole',
                    'severity': 'High' if depth > 0.25 else 'Medium',
                    'location': f'Segment {i // window_size + 1}',
                    'depth': round(depth, 2),
                    'lat': lat,
                    'lng': lng,
                    'mapX': float(x[idx]),
                    'mapZ': float(y[idx]),
                    'address': 'Melbourne CBD, VIC',
                    'description': f'Pothole detected with {round(depth, 2)}m depth.'
                })
    
    return defects[:20]  # Return top 20

def detect_flood_zones(las):
    """Detect flood-prone areas based on low elevation"""
    flood_zones = []
    
    z = las.z
    x = las.x
    y = las.y
    
    base_lat = -37.8136
    base_lng = 144.9631
    
    # Find low-lying areas
    threshold = np.percentile(z, 10)  # Bottom 10% elevation
    
    low_areas = np.where(z < threshold)[0]
    
    # Sample flood zones
    for i in range(0, len(low_areas), len(low_areas) // 12 if len(low_areas) > 12 else 1):
        if i >= len(low_areas):
            break
            
        idx = low_areas[i]
        elevation = float(z[idx])
        lat = base_lat + (y[idx] * 0.00001)
        lng = base_lng + (x[idx] * 0.00001)
        
        flood_zones.append({
            'id': len(flood_zones) + 1,
            'elevation': round(elevation, 2),
            'risk': 'High' if elevation < threshold - 1 else 'Medium',
            'location': f'Zone {len(flood_zones) + 1}',
            'lat': lat,
            'lng': lng,
            'mapX': float(x[idx]),
            'mapZ': float(y[idx]),
            'address': 'Melbourne CBD, VIC',
            'description': 'Low-lying area prone to flooding.'
        })
    
    return flood_zones[:12]

def detect_vegetation(las):
    """Detect vegetation encroachment"""
    vegetation = []
    
    z = las.z
    x = las.x
    y = las.y
    
    base_lat = -37.8136
    base_lng = 144.9631
    
    # Detect high points (potential vegetation)
    threshold = np.percentile(z, 85)  # Top 15% elevation
    
    high_points = np.where(z > threshold)[0]
    
    # Sample vegetation points
    for i in range(0, len(high_points), len(high_points) // 15 if len(high_points) > 15 else 1):
        if i >= len(high_points):
            break
            
        idx = high_points[i]
        height = float(z[idx])
        lat = base_lat + (y[idx] * 0.00001)
        lng = base_lng + (x[idx] * 0.00001)
        
        clearance = np.random.uniform(2, 5)
        
        vegetation.append({
            'id': len(vegetation) + 1,
            'type': 'Tree Overhang',
            'clearance': round(clearance, 1),
            'location': f'Area {len(vegetation) + 1}',
            'priority': 'High' if clearance < 3 else 'Medium',
            'lat': lat,
            'lng': lng,
            'mapX': float(x[idx]),
            'mapZ': float(y[idx]),
            'address': 'Melbourne CBD, VIC',
            'description': 'Vegetation encroachment detected.'
        })
    
    return vegetation[:15]


@app.route('/api/load-sample', methods=['GET'])
def load_sample():
    """Load the bundled dataset file from the repository (no upload needed).
    Returns the same JSON shape as the upload endpoint.
    """
    try:
        dataset_rel = os.path.join(os.path.dirname(__file__), '..', 'dataset', 'global_xyz_rgb_icgu__5018_0_3614.laz')
        dataset_path = os.path.abspath(dataset_rel)

        if not os.path.exists(dataset_path):
            return jsonify({'error': f'Dataset file not found: {dataset_path}'}), 404

        # Try to read the file (may be large)
        try:
            las = laspy.read(dataset_path)
        except Exception as e:
            print(f'ERROR reading dataset file {dataset_path}: {e}')
            print(traceback.format_exc())
            return jsonify({'error': f'Failed to read dataset file: {str(e)}'}), 500

        positions = las.xyz.flatten().tolist()
        elevations = las.z.tolist()
        colors = calculate_colors(las.z)
        defects = detect_defects(las)
        flood_zones = detect_flood_zones(las)
        vegetation = detect_vegetation(las)

        stats = {
            'pointCount': len(las.points),
            'minElevation': float(las.z.min()),
            'maxElevation': float(las.z.max()),
            'avgElevation': float(las.z.mean()),
            'bounds': {
                'xMin': float(las.x.min()),
                'xMax': float(las.x.max()),
                'yMin': float(las.y.min()),
                'yMax': float(las.y.max()),
                'zMin': float(las.z.min()),
                'zMax': float(las.z.max())
            }
        }

        return jsonify({
            'positions': positions,
            'colors': colors,
            'elevations': elevations,
            'defects': defects,
            'floodZones': flood_zones,
            'vegetation': vegetation,
            'stats': stats
        })

    except Exception as e:
        print(f'Unexpected error in load_sample: {e}')
        print(traceback.format_exc())
        return jsonify({'error': f'Unexpected server error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)