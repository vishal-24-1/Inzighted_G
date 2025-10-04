import React, { useState } from 'react';
import { useAuth } from '../utils/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { GoogleLogin, CredentialResponse } from '@react-oauth/google';
import './Auth.css';

const Register: React.FC = () => {
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    name: '',
    password: '',
    password_confirm: '',
  });
  const [errors, setErrors] = useState<any>({});
  const [loading, setLoading] = useState(false);
  
  const { register, googleLogin } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrors({});

    try {
      await register(
        formData.email,
        formData.username,
        formData.name,
        formData.password,
        formData.password_confirm
      );
      navigate('/');
    } catch (err: any) {
      setErrors(err.response?.data || { non_field_errors: ['Registration failed'] });
    } finally {
      setLoading(false);
    }
  };

  // Handle Google Registration Success
  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    try {
      setLoading(true);
      setErrors({});
      
      if (credentialResponse.credential) {
        await googleLogin(credentialResponse.credential);
        navigate('/');
      }
    } catch (err: any) {
      console.error('Google registration error:', err);
      setErrors({
        non_field_errors: [
          err.response?.data?.error || 
          err.response?.data?.detail || 
          'Google sign-up failed. Please try again.'
        ]
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle Google Registration Error
  const handleGoogleError = () => {
    setErrors({
      non_field_errors: ['Google sign-up was unsuccessful. Please try again.']
    });
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>Create Profile</h2>
        <p>Fill in your details to get started</p>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="name">Full Name</label>
            <input
              id="name"
              name="name"
              type="text"
              value={formData.name}
              onChange={handleChange}
              required
              placeholder="Enter your full name"
            />
            {errors.name && <span className="field-error">{errors.name[0]}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              name="username"
              type="text"
              value={formData.username}
              onChange={handleChange}
              required
              placeholder="Choose a username"
            />
            {errors.username && <span className="field-error">{errors.username[0]}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              required
              placeholder="Enter your email"
            />
            {errors.email && <span className="field-error">{errors.email[0]}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              required
              placeholder="Create a password"
            />
            {errors.password && <span className="field-error">{errors.password[0]}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="password_confirm">Confirm Password</label>
            <input
              id="password_confirm"
              name="password_confirm"
              type="password"
              value={formData.password_confirm}
              onChange={handleChange}
              required
              placeholder="Confirm your password"
            />
            {errors.password_confirm && <span className="field-error">{errors.password_confirm[0]}</span>}
          </div>

          {errors.non_field_errors && (
            <div className="error-message">{errors.non_field_errors[0]}</div>
          )}

          <button type="submit" disabled={loading} className="auth-button">
            {loading ? 'Creating Profile...' : 'Create Profile'}
          </button>
        </form>

        <div className="divider">
          <span>OR</span>
        </div>

        <div className="google-login-container">
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={handleGoogleError}
            useOneTap={false}
            size="large"
            width="100%"
            text="signup_with"
            shape="rectangular"
          />
        </div>

        <p className="auth-link">
          Already have an account? <Link to="/login">Sign In</Link>
        </p>
      </div>
    </div>
  );
};

export default Register;