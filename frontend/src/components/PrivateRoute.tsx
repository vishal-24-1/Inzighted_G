import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../utils/AuthContext';

interface PrivateRouteProps {
  children: React.ReactNode;
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  return user ? <>{children}</> : <Navigate to="/login" />;
};

export default PrivateRoute;