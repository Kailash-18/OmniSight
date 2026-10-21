import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './styles/base.css'
// Seeded OmniSight defects. Must load after base.css. Remove this import to see the repaired layout.
import './styles/defects.css'

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
