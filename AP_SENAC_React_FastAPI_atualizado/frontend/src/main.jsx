import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './styles.css'

// Ponto de entrada: o React monta a aplicação dentro da div #root do index.html.
createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)
