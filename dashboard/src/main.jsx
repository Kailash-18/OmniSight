import React from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/inter'
import '@fontsource/jetbrains-mono/400.css'
import '@fontsource/jetbrains-mono/600.css'
import './styles.css'
import { readTheme, applyTheme } from './theme.js'
import App from './App.jsx'

applyTheme(readTheme()) // before first paint, so there is no light/dark flash
createRoot(document.getElementById('app')).render(<React.StrictMode><App /></React.StrictMode>)
