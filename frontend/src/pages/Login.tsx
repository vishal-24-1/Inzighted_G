import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../utils/AuthContext';
import { useGoogleLogin } from '@react-oauth/google';
import { Eye, EyeOff, AlertCircle } from 'lucide-react';
import LogoImg from '../assets/logo.svg';
import LoginImg from '../assets/login.png';

// Small reusable LoginForm component so it can be embedded elsewhere
function LoginForm() {
  const { login, googleLogin, user, loading: authLoading } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  // derive combined loading state
  const isLoading = loading || authLoading;

  // Get client ID from environment variables
  const googleClientId = process.env.REACT_APP_GOOGLE_CLIENT_ID;

  // Google Login hook
  const googleAuth = useGoogleLogin({
    onSuccess: async (response) => {
      try {
        setLoading(true);
        if (response.access_token) {
          await googleLogin(response.access_token);
          navigate('/');
        }
      } catch (err: any) {
        const message = err?.response?.data?.detail || err?.message || 'Google login failed';
        setFormError(message);
      } finally {
        setLoading(false);
      }
    },
    onError: () => {
      setFormError('Google sign-in was unsuccessful. Please try again.');
    },
  flow: 'implicit',
  });

  // Clean error messages for UX
  const getCleanErrorMessage = () => {
    if (formError) return formError;
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    // basic validation
    if (!username || !password) {
      setFormError('Username and password are required');
      return;
    }

    try {
      setLoading(true);
      // AuthContext.login expects (email, password)
      await login(username, password);
      navigate('/');
    } catch (err: any) {
      // auth API errors may include response messages, try to extract
      const message = err?.response?.data?.detail || err?.message || 'Login failed';
      setFormError(message);
    } finally {
      setLoading(false);
    }
  };

  const hasAuthError = Boolean(getCleanErrorMessage());

  return (
    <div className="w-full flex flex-col items-center justify-center md:max-w-md">
      <form
        onSubmit={handleSubmit}
        className="space-y-4 w-full p-6 pb-6 pt-8 bg-white rounded-t-2xl shadow-lg md:rounded-2xl md:mx-4 md:px-6 md:py-8"
      >
        <div className="space-y-1 items-center text-center text-sm text-gray-600">
          <img src={LogoImg} alt="Logo" className="h-6 mx-auto mb-2" />
          <div className="text-lg font-semibold">Login</div>
        </div>

        <div className="space-y-1">
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            className={`transition-all duration-200 text-base h-12 rounded-xl w-full px-4 border ${hasAuthError ? 'border-red-300 bg-red-50 focus:border-red-500' : 'border-gray-200 focus:border-blue-500'}`}
            aria-invalid={hasAuthError}
            aria-describedby={hasAuthError ? 'login-error' : undefined}
          />
        </div>

        <div className="space-y-1 relative">
          <input
            type={showPassword ? 'text' : 'password'}
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className={`transition-all duration-200 pr-10 text-base h-12 rounded-xl w-full px-4 border ${hasAuthError ? 'border-red-300 bg-red-50 focus:border-red-500' : 'border-gray-200 focus:border-blue-500'}`}
            aria-invalid={hasAuthError}
            aria-describedby={hasAuthError ? 'login-error' : undefined}
          />

          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700 focus:outline-none"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>

        {getCleanErrorMessage() && (
          <div id="login-error" role="alert" className="flex items-center space-x-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-md p-3">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{getCleanErrorMessage()}</span>
          </div>
        )}

        <div className="flex flex-col w-full gap-3">
          <button type="submit" disabled={isLoading} className="w-full rounded-xl h-12 bg-blue-600 text-white font-medium">
            {isLoading ? (
              <div className="flex items-center justify-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                <span>Logging in...</span>
              </div>
            ) : (
              'Login'
            )}
          </button>

          <div className="w-full">
            <div className="w-full text-center text-sm text-gray-500">or</div>
          </div>

          <div className="w-full flex flex-col gap-3">
            <button
              type="button"
              onClick={() => googleAuth()}
              disabled={isLoading}
              className="w-full rounded-xl h-12 bg-white text-gray-700 font-medium border border-gray-300 hover:bg-gray-50 flex items-center justify-center gap-3"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <span>Continue with Google</span>
            </button>

            <Link to="/register" className="w-full block text-center text-sm text-blue-600 underline">Create Profile</Link>
          </div>
        </div>
      </form>
    </div>
  );
}

// ... rest of your code remains the same
export default function LoginPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) {
      navigate('/');
    }
  }, [loading, user, navigate]);

  return (
    <>
      {/* Mobile / small screens */}
      <div className="min-h-screen w-full flex items-end justify-center relative overflow-hidden md:hidden" style={{ backgroundImage: `url(${LoginImg})`, backgroundSize: 'cover', backgroundPosition: 'center' }}>
        <div className="w-full max-w-md mx-auto">
          <LoginForm />
        </div>
      </div>

      {/* Desktop: split layout */}
      <div className="hidden md:flex flex-col min-h-screen w-full relative">
        <div className="flex-1 w-full bg-cover bg-center" style={{ backgroundImage: `url(${LoginImg})` }} />
        <div className="flex-1 w-full bg-white" />

        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-30 w-full max-w-md px-4">
          <div className="mx-auto">
            <LoginForm />
          </div>
        </div>
      </div>
    </>
  );
}

export { LoginForm };