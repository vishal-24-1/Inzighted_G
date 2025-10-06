import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider, useAuth } from './utils/AuthContext';
import PrivateRoute from './components/PrivateRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import Home from './pages/Home';
import ChatBot from './pages/ChatBot';
import BoostMe from './pages/BoostMe';
import TutoringChat from './pages/TutoringChat';
import './App.css';

// Resolve Google Client ID from multiple sources:
// 1. CRA env var: process.env.REACT_APP_GOOGLE_CLIENT_ID
// 2. Runtime global: window.__GOOGLE_CLIENT_ID (useful for injecting at runtime)
// 3. Meta tag in public/index.html: <meta name="google-client-id" content="..." />
const resolveGoogleClientId = () => {
  const fromEnv = process.env.REACT_APP_GOOGLE_CLIENT_ID;
  if (fromEnv) return fromEnv;

  // @ts-ignore
  const fromWindow = (typeof window !== 'undefined' && (window as any).__GOOGLE_CLIENT_ID) || '';
  if (fromWindow) return fromWindow;

  try {
    const meta = typeof document !== 'undefined' ? document.querySelector('meta[name="google-client-id"]') as HTMLMetaElement | null : null;
    if (meta && meta.content) return meta.content;
  } catch (e) {
    // ignore (server-side or test environments)
  }

  return '';
};

const GOOGLE_CLIENT_ID = resolveGoogleClientId();

// Component to handle route redirects based on auth state
const AuthRedirect: React.FC = () => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }
  
  return user ? <Navigate to="/" /> : <Navigate to="/login" />;
};

function App() {
  // If the client ID is missing, avoid initializing the Google provider to prevent
  // the GSI library from throwing a runtime error. Show a developer-friendly overlay.
  if (!GOOGLE_CLIENT_ID) {
    return (
      <div style={{position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', color: '#fff', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24}}>
        <div style={{maxWidth: 760, background: '#111827', padding: 24, borderRadius: 8}}>
          <h2 style={{marginTop:0}}>Google Client ID missing</h2>
          <p>The Google OAuth client ID is not available to the app. The Google library requires a valid <code>client_id</code>.</p>
          <p>Options to fix this during development:</p>
          <ul>
            <li>Add <code>REACT_APP_GOOGLE_CLIENT_ID=YOUR_CLIENT_ID</code> to <code>frontend/.env</code> and restart the dev server.</li>
            <li>Or add a meta tag in <code>public/index.html</code>: <code>&lt;meta name="google-client-id" content="YOUR_CLIENT_ID" /&gt;</code></li>
            <li>Or set <code>window.__GOOGLE_CLIENT_ID = 'YOUR_CLIENT_ID'</code> from a script before the app loads.</li>
          </ul>
          <p>After providing the client ID, restart the dev server so the value is embedded.</p>
        </div>
      </div>
    );
  }

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <Router>
          <div className="App">
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route 
                path="/" 
                element={
                  <PrivateRoute>
                    <Home />
                  </PrivateRoute>
                } 
              />
              <Route 
                path="/chat" 
                element={
                  <PrivateRoute>
                    <ChatBot />
                  </PrivateRoute>
                } 
              />
              <Route 
                path="/boost" 
                element={
                  <PrivateRoute>
                    <BoostMe />
                  </PrivateRoute>
                } 
              />
              <Route 
                path="/tutoring/new" 
                element={
                  <PrivateRoute>
                    <TutoringChat />
                  </PrivateRoute>
                } 
              />
              <Route 
                path="/tutoring/:sessionId" 
                element={
                  <PrivateRoute>
                    <TutoringChat />
                  </PrivateRoute>
                } 
              />
              <Route path="*" element={<AuthRedirect />} />
            </Routes>
          </div>
        </Router>
      </AuthProvider>
    </GoogleOAuthProvider>
  );
}

export default App;
