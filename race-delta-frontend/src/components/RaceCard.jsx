import React from 'react';
import { Link } from 'react-router-dom';

export default function RaceCard({ race }) {
  return (
    <Link to={`/race/${race.season}/${race.round}`} className="block p-3 border rounded hover:shadow-sm">
      <div className="font-semibold">{race.name}</div>
      <div className="text-sm text-gray-500">{race.circuit}</div>
    </Link>
  );
}
