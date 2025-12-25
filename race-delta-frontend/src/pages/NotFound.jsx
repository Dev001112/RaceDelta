import React from 'react';
import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="text-center py-20">
      <h1 className="text-3xl font-semibold mb-2">404 — Not Found</h1>
      <p className="text-gray-600 mb-6">We couldn’t find that page.</p>
      <Link to="/" className="px-4 py-2 border rounded">Go home</Link>
    </div>
  );
}
