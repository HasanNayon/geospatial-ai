import React from 'react';
import MapView from './MapView';
import DiagramView from './DiagramView';
import ThreeDView from './ThreeDView';

export default function Dashboard() {
  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">LiDAR Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MapView />
        <DiagramView />
        <ThreeDView />
      </div>
    </div>
  );
}
