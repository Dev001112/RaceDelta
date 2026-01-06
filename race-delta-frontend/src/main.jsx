import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

import { SeasonProvider } from './context/SeasonContext'

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <SeasonProvider>
        <App />
      </SeasonProvider>
    </BrowserRouter>
  </React.StrictMode>
)
