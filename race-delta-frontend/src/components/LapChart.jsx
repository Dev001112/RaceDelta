import React from 'react';
import Plot from 'react-plotly.js';

export default function LapChart({ data = [] , layout = {} }) {
  // Expects data as array of traces: [{ x:[], y:[], name: 'Driver' }]
  const defaultLayout = {
    autosize: true,
    margin: { t: 20, l: 40, r: 20, b: 40 },
    legend: { orientation: 'h' },
    xaxis: { title: 'Lap' },
    yaxis: { title: 'Lap time (s)' },
    ...layout
  };

  return (
    <div className="border rounded p-2">
      <Plot
        data={data}
        layout={defaultLayout}
        style={{ width: '100%', height: '360px' }}
        config={{ responsive: true, displayModeBar: false }}
      />
    </div>
  );
}
