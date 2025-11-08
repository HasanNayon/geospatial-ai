import React, { useState, useEffect, useRef } from 'react';
import { Upload, MapPin, TrendingUp, Layers, X, Navigation } from 'lucide-react';
import * as THREE from 'three';

const API_URL = 'http://localhost:8000/api';

function App() {
  const [loading, setLoading] = useState(true); // Start loading
  const [pointCloud, setPointCloud] = useState(null);
  const [stats, setStats] = useState(null);
  const [defects, setDefects] = useState([]);
  const [floodRisk, setFloodRisk] = useState([]);
  const [vegetation, setVegetation] = useState([]);
  const [viewMode, setViewMode] = useState('3d');
  const [selectedMarker, setSelectedMarker] = useState(null);
  const [mapCenter] = useState({ lat: -37.8136, lng: 144.9631 });
  
  const mountRef = useRef(null);
  const mapRef = useRef(null);
  const googleMapRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const pointsRef = useRef(null);
  const markersRef = useRef([]);

  // Auto-load sample dataset and initialize Google Maps
  useEffect(() => {
    if (!window.google) {
      const script = document.createElement('script');
      script.src = 'https://maps.googleapis.com/maps/api/js?key=AIzaSyDxpHz3SOcD19gzEcOyYkDDgWQT9A9XwNw';
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }

    // Load sample dataset on startup
    loadSample();
  }, []);

  // Initialize Three.js scene
  useEffect(() => {
    if (!mountRef.current || viewMode !== '3d') return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a0a);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(
      60,
      mountRef.current.clientWidth / mountRef.current.clientHeight,
      0.1,
      5000
    );
    camera.position.set(100, 80, 100);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    mountRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.6);
    directionalLight.position.set(50, 100, 50);
    scene.add(directionalLight);

    const gridHelper = new THREE.GridHelper(200, 40, 0x333333, 0x1a1a1a);
    scene.add(gridHelper);

    let animationId;
    const animate = () => {
      animationId = requestAnimationFrame(animate);
      if (pointsRef.current) {
        pointsRef.current.rotation.y += 0.002;
      }
      renderer.render(scene, camera);
    };
    animate();

    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };

    const onMouseDown = (e) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseMove = (e) => {
      if (!isDragging) return;
      const deltaX = e.clientX - previousMousePosition.x;
      const deltaY = e.clientY - previousMousePosition.y;
      if (pointsRef.current) {
        pointsRef.current.rotation.y += deltaX * 0.01;
        pointsRef.current.rotation.x += deltaY * 0.01;
      }
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const onWheel = (e) => {
      e.preventDefault();
      const zoomSpeed = e.deltaY * 0.05;
      camera.position.z += zoomSpeed;
      camera.position.z = Math.max(20, Math.min(300, camera.position.z));
    };

    renderer.domElement.addEventListener('mousedown', onMouseDown);
    renderer.domElement.addEventListener('mousemove', onMouseMove);
    renderer.domElement.addEventListener('mouseup', onMouseUp);
    renderer.domElement.addEventListener('wheel', onWheel);

    const handleResize = () => {
      if (!mountRef.current) return;
      camera.aspect = mountRef.current.clientWidth / mountRef.current.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationId);
      renderer.domElement.removeEventListener('mousedown', onMouseDown);
      renderer.domElement.removeEventListener('mousemove', onMouseMove);
      renderer.domElement.removeEventListener('mouseup', onMouseUp);
      renderer.domElement.removeEventListener('wheel', onWheel);
      window.removeEventListener('resize', handleResize);
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [viewMode]);

  useEffect(() => {
    if (!pointCloud || !sceneRef.current || viewMode !== '3d') return;

    if (pointsRef.current) {
      sceneRef.current.remove(pointsRef.current);
      pointsRef.current.geometry.dispose();
      pointsRef.current.material.dispose();
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pointCloud.positions), 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(pointCloud.colors), 3));

    const material = new THREE.PointsMaterial({
      size: 0.4,
      vertexColors: true,
      sizeAttenuation: true
    });

    const points = new THREE.Points(geometry, material);
    pointsRef.current = points;
    sceneRef.current.add(points);

    geometry.computeBoundingBox();
    const center = new THREE.Vector3();
    geometry.boundingBox.getCenter(center);
    points.position.sub(center);

    const size = geometry.boundingBox.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    cameraRef.current.position.set(maxDim * 0.8, maxDim * 0.6, maxDim * 0.8);
    cameraRef.current.lookAt(0, 0, 0);
  }, [pointCloud, viewMode]);

  // Initialize Google Map
  useEffect(() => {
    if (!mapRef.current || viewMode !== 'googlemap' || !window.google) return;

    const map = new window.google.maps.Map(mapRef.current, {
      center: mapCenter,
      zoom: 13,
      mapTypeId: 'roadmap',
      styles: [
        { elementType: 'geometry', stylers: [{ color: '#242f3e' }] },
        { elementType: 'labels.text.stroke', stylers: [{ color: '#242f3e' }] },
        { elementType: 'labels.text.fill', stylers: [{ color: '#746855' }] },
        {
          featureType: 'administrative.locality',
          elementType: 'labels.text.fill',
          stylers: [{ color: '#d59563' }]
        },
        {
          featureType: 'road',
          elementType: 'geometry',
          stylers: [{ color: '#38414e' }]
        },
        {
          featureType: 'road',
          elementType: 'geometry.stroke',
          stylers: [{ color: '#212a37' }]
        }
      ]
    });

    googleMapRef.current = map;

    markersRef.current.forEach(marker => marker.setMap(null));
    markersRef.current = [];

    const allMarkers = [
      ...defects.map(d => ({ ...d, category: 'defect' })),
      ...floodRisk.map(f => ({ ...f, category: 'flood' })),
      ...vegetation.map(v => ({ ...v, category: 'vegetation' }))
    ];

    allMarkers.forEach((item) => {
      const marker = new window.google.maps.Marker({
        position: { lat: item.lat, lng: item.lng },
        map: map,
        title: item.type || 'Flood Risk',
        icon: {
          path: window.google.maps.SymbolPath.CIRCLE,
          fillColor: item.category === 'defect' 
            ? (item.severity === 'High' ? '#ef4444' : '#f59e0b') 
            : item.category === 'flood' ? '#8b5cf6' : '#22c55e',
          fillOpacity: 0.8,
          strokeColor: '#ffffff',
          strokeWeight: 2,
          scale: item.severity === 'High' || item.priority === 'High' ? 10 : 8
        }
      });

      marker.addListener('click', () => {
        setSelectedMarker(item);
        map.panTo({ lat: item.lat, lng: item.lng });
      });

      markersRef.current.push(marker);
    });
  }, [viewMode, defects, floodRisk, vegetation, mapCenter]);

  const loadSample = async () => {
    setLoading(true);

    try {
      console.log('Loading sample dataset...');
      const response = await fetch(`${API_URL}/load-sample`);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Upload failed' }));
        throw new Error(errorData.error || `Upload failed: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();

      setPointCloud({
        positions: data.positions,
        colors: data.colors,
        elevations: data.elevations
      });

      setDefects(data.defects || []);
      setFloodRisk(data.floodZones || []);
      setVegetation(data.vegetation || []);

      setStats({
        ...data.stats,
        roadLength: '12.5 km',
        defectCount: (data.defects || []).length,
        highPriorityDefects: (data.defects || []).filter(d => d.severity === 'High').length,
        floodZones: (data.floodZones || []).length,
        vegetationIssues: (data.vegetation || []).length
      });

    } catch (err) {
      console.error('Upload error:', err);
      console.error('Error details:', {
        name: err.name,
        message: err.message,
        stack: err.stack
      });
      const errorMessage = err.message || 'Unknown error occurred during upload';
      alert(`Error uploading file: ${errorMessage}\n\nPlease check:\n1. Backend server is running on http://localhost:5000\n2. File is a valid .laz or .las file\n3. File size is not too large (< 500MB)`);
    } finally {
      setLoading(false);
    }
  };



  const getPriorityColor = (severity) => {
    if (severity === 'High') return 'text-red-400 bg-red-900/20';
    if (severity === 'Medium') return 'text-yellow-400 bg-yellow-900/20';
    return 'text-gray-400 bg-gray-900/20';
  };

  const getMarkerColor = (type, severity) => {
    if (type === 'Pothole' || type === 'Crack') {
      return severity === 'High' ? '#ef4444' : '#f59e0b';
    }
    if (type === 'Tree Overhang') return '#22c55e';
    return '#8b5cf6';
  };

  const DiagramView = () => {
    const allMarkers = [
      ...defects.map(d => ({ ...d, category: 'defect' })),
      ...floodRisk.map(f => ({ ...f, category: 'flood' })),
      ...vegetation.map(v => ({ ...v, category: 'vegetation' }))
    ];

    return (
      <div className="relative w-full h-full bg-gradient-to-br from-gray-900 to-gray-800">
        <svg className="w-full h-full" viewBox="-100 -100 200 200">
          <defs>
            <pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse">
              <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#374151" strokeWidth="0.3"/>
            </pattern>
          </defs>
          <rect x="-100" y="-100" width="200" height="200" fill="url(#grid)" />
          
          <g opacity="0.4">
            <path d="M -75,-60 Q -60,-50 -50,-40 T -30,-20 T -10,0 T 10,20 T 30,40 T 50,60 T 75,80" stroke="#4b5563" strokeWidth="6" fill="none" />
          </g>

          {allMarkers.map((marker, idx) => {
            const scale = 150 / 200;
            const x = marker.mapX * scale;
            const z = marker.mapZ * scale;
            const color = marker.category === 'defect' 
              ? getMarkerColor(marker.type, marker.severity) 
              : marker.category === 'flood' ? '#8b5cf6' : '#22c55e';
            const isSelected = selectedMarker?.id === marker.id && selectedMarker?.category === marker.category;

            return (
              <g
                key={`${marker.category}-${idx}`}
                transform={`translate(${x}, ${z})`}
                onClick={() => setSelectedMarker(marker)}
                style={{ cursor: 'pointer' }}
              >
                {isSelected && (
                  <circle r="4" fill="none" stroke={color} strokeWidth="0.5" opacity="0.5">
                    <animate attributeName="r" from="4" to="8" dur="1.5s" repeatCount="indefinite" />
                    <animate attributeName="opacity" from="0.5" to="0" dur="1.5s" repeatCount="indefinite" />
                  </circle>
                )}
                <circle r="2" fill={color} stroke="white" strokeWidth="0.3" opacity={isSelected ? 1 : 0.8} />
                {marker.severity === 'High' && <circle r="2.5" fill="none" stroke={color} strokeWidth="0.2" opacity="0.6" />}
              </g>
            );
          })}

          <g transform="translate(-90, 70)">
            <rect x="0" y="0" width="35" height="25" fill="#000" opacity="0.7" rx="2"/>
            <circle cx="5" cy="6" r="1.5" fill="#ef4444"/>
            <text x="8" y="7.5" fontSize="3" fill="#fff">Defects</text>
            <circle cx="5" cy="12" r="1.5" fill="#8b5cf6"/>
            <text x="8" y="13.5" fontSize="3" fill="#fff">Flood</text>
            <circle cx="5" cy="18" r="1.5" fill="#22c55e"/>
            <text x="8" y="19.5" fontSize="3" fill="#fff">Vegetation</text>
          </g>
        </svg>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-gray-900 text-white">
      <div className="max-w-[1800px] mx-auto p-6">
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          <div className="col-span-full mb-6">
            <h1 className="text-4xl font-bold mb-2 flex items-center gap-3">
              <Layers className="w-10 h-10 text-blue-400" />
              Smart Council Asset Monitoring Platform
            </h1>
            <p className="text-gray-300">AI-Powered LiDAR Analysis with Google Maps Integration</p>
          </div>
          <div className="xl:col-span-3 space-y-4">
            <div>
              <div className="bg-gray-800/50 backdrop-blur rounded-xl p-5 border border-gray-700">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <Upload className="w-5 h-5 text-blue-400" />
                  LiDAR Dataset
                </h2>
                <div className="text-center text-gray-300">
                  <p>Analyzing dataset:</p>
                  <p className="text-sm font-mono mt-1">dataset/global_xyz_rgb_icgu__5018_0_3614.laz</p>
                </div>
              </div>
              <button onClick={loadSample} className="mt-4 w-full bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded text-sm font-medium">
                Load Sample Dataset
              </button>
            </div>

          {pointCloud && (
            <div className="bg-gray-800/50 backdrop-blur rounded-xl p-5 border border-gray-700">
              <h2 className="text-lg font-semibold mb-4">View Mode</h2>
              <div className="grid grid-cols-1 gap-2">
                <button onClick={() => setViewMode('3d')} className={`px-4 py-3 rounded-lg font-medium transition ${viewMode === '3d' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}>
                  <Layers className="w-4 h-4 inline mr-2" />
                  3D Point Cloud
                </button>
                <button onClick={() => setViewMode('diagram')} className={`px-4 py-3 rounded-lg font-medium transition ${viewMode === 'diagram' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}>
                  <Navigation className="w-4 h-4 inline mr-2" />
                  Diagram View
                </button>
                <button onClick={() => setViewMode('googlemap')} className={`px-4 py-3 rounded-lg font-medium transition ${viewMode === 'googlemap' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}>
                  <MapPin className="w-4 h-4 inline mr-2" />
                  Google Maps
                </button>
              </div>
            </div>
          )}

          {stats && (
              <div className="bg-gray-800/50 backdrop-blur rounded-xl p-5 border border-gray-700">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-blue-400" />
                  Key Metrics
                </h2>
                <div className="space-y-3">
                  <div className="bg-gradient-to-r from-blue-900/40 to-transparent p-3 rounded-lg">
                    <p className="text-xs text-gray-400">Total Points</p>
                    <p className="text-2xl font-bold text-blue-400">{stats.pointCount.toLocaleString()}</p>
                  </div>
                  <div className="bg-gradient-to-r from-red-900/40 to-transparent p-3 rounded-lg">
                    <p className="text-xs text-gray-400">Road Defects</p>
                    <p className="text-2xl font-bold text-red-400">{stats.defectCount}</p>
                  </div>
                  <div className="bg-gradient-to-r from-yellow-900/40 to-transparent p-3 rounded-lg">
                    <p className="text-xs text-gray-400">High Priority</p>
                    <p className="text-2xl font-bold text-yellow-400">{stats.highPriorityDefects}</p>
                  </div>
                  <div className="bg-gradient-to-r from-purple-900/40 to-transparent p-3 rounded-lg">
                    <p className="text-xs text-gray-400">Flood Zones</p>
                    <p className="text-2xl font-bold text-purple-400">{stats.floodZones}</p>
                  </div>
                  <div className="bg-gradient-to-r from-green-900/40 to-transparent p-3 rounded-lg">
                    <p className="text-xs text-gray-400">Vegetation Issues</p>
                    <p className="text-2xl font-bold text-green-400">{stats.vegetationIssues}</p>
                  </div>
                </div>
              </div>
            )}

            {selectedMarker && (
              <div className="bg-gray-800/50 backdrop-blur rounded-xl p-5 border border-gray-700">
                <div className="flex justify-between items-start mb-3">
                  <h3 className="font-semibold">Selected Location</h3>
                  <button onClick={() => setSelectedMarker(null)} className="text-gray-400 hover:text-white">
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="space-y-2 text-sm">
                  <div>
                    <p className="text-gray-400 text-xs">Type</p>
                    <p className="font-medium">{selectedMarker.type || 'Flood Zone'}</p>
                  </div>
                  {selectedMarker.severity && (
                    <div>
                      <p className="text-gray-400 text-xs">Severity</p>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${getPriorityColor(selectedMarker.severity)}`}>
                        {selectedMarker.severity}
                      </span>
                    </div>
                  )}
                  <div>
                    <p className="text-gray-400 text-xs">Coordinates</p>
                    <p className="font-mono text-xs">{selectedMarker.lat?.toFixed(6)}, {selectedMarker.lng?.toFixed(6)}</p>
                  </div>
                  {selectedMarker.address && (
                    <div>
                      <p className="text-gray-400 text-xs">Address</p>
                      <p className="text-xs">{selectedMarker.address}</p>
                    </div>
                  )}
                  <button 
                    onClick={() => window.open(`https://www.google.com/maps/search/?api=1&query=${selectedMarker.lat},${selectedMarker.lng}`, '_blank')}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded text-sm font-medium mt-2"
                  >
                    Open in Google Maps
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="xl:col-span-9">
            <div className="bg-gray-800/50 backdrop-blur rounded-xl overflow-hidden border border-gray-700">
              <div className="h-[700px] relative">
                {loading ? (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-500 mx-auto mb-4"></div>
                      <p className="text-xl text-gray-300">Processing LiDAR data...</p>
                      <p className="text-sm text-gray-500 mt-2">Analyzing terrain and detecting features</p>
                    </div>
                  </div>
                ) : !pointCloud ? (
                  <div className="h-full flex items-center justify-center">
                    <div className="text-center">
                      <Layers className="w-24 h-24 mx-auto mb-4 opacity-30 text-gray-600" />
                      <p className="text-xl text-gray-400">Upload LiDAR data to begin</p>
                      <p className="text-sm text-gray-500 mt-2">Supports .laz and .las formats</p>
                    </div>
                  </div>
                ) : viewMode === '3d' ? (
                  <div ref={mountRef} className="w-full h-full" />
                ) : viewMode === 'diagram' ? (
                  <DiagramView />
                ) : (
                  <div className="relative w-full h-full">
                    <div ref={mapRef} className="w-full h-full" />
                    {!window.google && (
                      <div className="absolute inset-0 flex items-center justify-center bg-gray-900/80">
                        <div className="text-center p-8 bg-gray-800 rounded-lg max-w-md">
                          <MapPin className="w-16 h-16 mx-auto mb-4 text-yellow-500" />
                          <h3 className="text-xl font-bold mb-2">Loading Google Maps...</h3>
                          <p className="text-gray-300 text-sm">Please wait while the map loads.</p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {pointCloud && selectedMarker && (
              <div className="mt-4 bg-gray-800/50 backdrop-blur rounded-xl p-5 border border-gray-700">
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <MapPin className="w-5 h-5 text-blue-400" />
                  Location Details
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gray-900/50 p-3 rounded-lg">
                    <p className="text-xs text-gray-400">Issue ID</p>
                    <p className="text-lg font-bold text-blue-400">#{selectedMarker.id}</p>
                  </div>
                  <div className="bg-gray-900/50 p-3 rounded-lg">
                    <p className="text-xs text-gray-400">Type</p>
                    <p className="text-lg font-semibold">{selectedMarker.type || 'Flood Zone'}</p>
                  </div>
                  {selectedMarker.severity && (
                    <div className="bg-gray-900/50 p-3 rounded-lg">
                      <p className="text-xs text-gray-400">Severity</p>
                      <p className={`text-lg font-semibold ${selectedMarker.severity === 'High' ? 'text-red-400' : 'text-yellow-400'}`}>
                        {selectedMarker.severity}
                      </p>
                    </div>
                  )}
                  {selectedMarker.depth && (
                    <div className="bg-gray-900/50 p-3 rounded-lg">
                      <p className="text-xs text-gray-400">Depth</p>
                      <p className="text-lg font-semibold text-orange-400">{selectedMarker.depth}m</p>
                    </div>
                  )}
                </div>
                {selectedMarker.description && (
                  <div className="mt-4 p-4 bg-blue-900/20 border border-blue-800/30 rounded-lg">
                    <p className="text-sm text-gray-300">{selectedMarker.description}</p>
                  </div>
                )}
                <div className="mt-4 flex gap-3">
                  <button className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg font-medium transition">
                    Create Work Order
                  </button>
                  <button className="flex-1 bg-green-600 hover:bg-green-700 text-white px-4 py-3 rounded-lg font-medium transition">
                    Schedule Inspection
                  </button>
                  <button className="flex-1 bg-gray-700 hover:bg-gray-600 text-white px-4 py-3 rounded-lg font-medium transition">
                    Export Report
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;