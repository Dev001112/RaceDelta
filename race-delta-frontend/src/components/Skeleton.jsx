import React from 'react';

export default function Skeleton({ rows = 4 }) {
  return (
    <div className="space-y-3">
      {Array.from({length: rows}).map((_,i) => (
        <div key={i} className="h-12 bg-gray-100 rounded animate-pulse" />
      ))}
    </div>
  );
}
