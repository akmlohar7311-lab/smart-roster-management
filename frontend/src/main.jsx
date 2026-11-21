
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import './index.css'
import AuthGate from './AuthGate'
import { AuthProvider } from './context/AuthContext'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <AuthGate />
    </AuthProvider>
  </StrictMode>,
)
