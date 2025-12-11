# Utility functions for the Pothole Detection System

import math
import requests
from datetime import datetime

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # Earth's radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def nearest_neighbor_path(points, start_idx=0):
    """Find shortest path using nearest neighbor algorithm"""
    if not points:
        return [], 0
    
    n = len(points)
    visited = [False] * n
    path = [start_idx]
    visited[start_idx] = True
    total_distance = 0
    
    current = start_idx
    for _ in range(n - 1):
        nearest = None
        min_dist = float('inf')
        
        for j in range(n):
            if not visited[j]:
                dist = calculate_distance(
                    points[current]['lat'], points[current]['lng'],
                    points[j]['lat'], points[j]['lng']
                )
                if dist < min_dist:
                    min_dist = dist
                    nearest = j
        
        if nearest is not None:
            visited[nearest] = True
            path.append(nearest)
            total_distance += min_dist
            current = nearest
    
    return path, total_distance

def get_automatic_location():
    """Get location from IP geolocation services"""
    try:
        services = [
            'https://ipapi.co/json/',
            'http://ip-api.com/json/',
            'https://geolocation-db.com/json/'
        ]
        
        for service in services:
            try:
                response = requests.get(service, timeout=3)
                data = response.json()
                
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
