import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './utils/AuthContext';
import PrivateRoute from './components/PrivateRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import Home from './pages/Home';
import ChatBot from './pages/ChatBot';
import BoostMe from './pages/BoostMe';
import TutoringChat from './pages/TutoringChat';
import './App.css';

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
  return (
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
  );
}

export default App;
