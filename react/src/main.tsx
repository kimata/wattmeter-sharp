import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Bulma and FontAwesome are loaded via CDN in index.html
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
