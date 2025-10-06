import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
import { useGoogleLogin } from '@react-oauth/google';
import { useAuth } from '../utils/AuthContext';
import LogoImg from '../assets/logo.svg';
import LoginImg from '../assets/login.png';

type ApiErrorPayload = Record<string, string | string[]>;

const RegisterForm: React.FC = () => {
  const { register, googleLogin, loading: authLoading } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    email: '',
    username: '',
    name: '',
    password: '',
    password_confirm: '',
  });
  const [formErrors, setFormErrors] = useState<ApiErrorPayload>({});
  const [loading, setLoading] = useState(false);

  const isLoading = loading || authLoading;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const getErrorMessages = (field: string): string[] => {
    const value = formErrors?.[field];
    if (!value) return [];
    if (Array.isArray(value)) return value.map((item) => String(item));
    if (typeof value === 'string') return [value];
    return [];
  };

  const getFirstError = (field: string): string | null => {
    const messages = getErrorMessages(field);
    return messages.length > 0 ? messages[0] : null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormErrors({});

    try {
      setLoading(true);
      await register(
        formData.email,
        formData.username,
        formData.name,
        formData.password,
        formData.password_confirm
      );
      navigate('/');
    } catch (err: any) {
      const payload = err?.response?.data;
      if (payload && typeof payload === 'object') {
        setFormErrors(payload as ApiErrorPayload);
      } else {
        setFormErrors({ non_field_errors: 'Registration failed. Please try again.' });
      }
    } finally {
      setLoading(false);
    }
  };

  const googleAuth = useGoogleLogin({
    onSuccess: async (response) => {
      try {
        setLoading(true);
        setFormErrors({});

        if (response.access_token) {
          await googleLogin(response.access_token);
          navigate('/');
        }
      } catch (err: any) {
        const payload = err?.response?.data;
        if (payload && typeof payload === 'object') {
          setFormErrors(payload as ApiErrorPayload);
        } else {
          setFormErrors({
            non_field_errors: 'Google sign-up failed. Please try again.',
          });
        }
      } finally {
        setLoading(false);
      }
    },
    onError: () => {
      setFormErrors({
        non_field_errors: 'Google sign-up was unsuccessful. Please try again.',
      });
    },
    flow: 'implicit',
  });

  const nonFieldError = getFirstError('non_field_errors');

  const inputClassName = (hasError: boolean) =>
    `transition-all duration-200 h-12 rounded-xl w-full px-4 text-base border focus:outline-none focus:ring-2 ${hasError
      ? 'border-red-300 bg-red-50 focus:border-red-500 focus:ring-red-200'
      : 'border-gray-200 focus:border-blue-500 focus:ring-blue-200'
    }`;

  return (
    <div className="w-full flex flex-col items-center justify-center md:max-w-md">
      <form
        onSubmit={handleSubmit}
        className="space-y-4 w-full p-6 pb-6 pt-8 bg-white rounded-t-2xl shadow-lg md:rounded-2xl md:mx-4 md:px-6 md:py-8"
      >
        <div className="space-y-1 items-center text-center text-sm text-gray-600">
          <img src={LogoImg} alt="Logo" className="h-6 mx-auto mb-2" />
          <div className="text-lg font-semibold">Create Profile</div>
          <p className="text-gray-500 text-sm">Fill in your details to get started</p>
        </div>

        {nonFieldError && (
          <div className="flex items-center space-x-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-md p-3">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <span>{nonFieldError}</span>
          </div>
        )}

        <div className="space-y-1">
          <label htmlFor="name" className="text-sm font-medium text-gray-700">
            Full Name
          </label>
          <input
            id="name"
            name="name"
            type="text"
            value={formData.name}
            onChange={handleChange}
            required
            placeholder="Enter your full name"
            className={inputClassName(Boolean(getFirstError('name')))}
          />
          {getFirstError('name') && (
            <span className="text-xs text-red-600">{getFirstError('name')}</span>
          )}
        </div>

        <div className="space-y-1">
          <label htmlFor="username" className="text-sm font-medium text-gray-700">
            Username
          </label>
          <input
            id="username"
            name="username"
            type="text"
            value={formData.username}
            onChange={handleChange}
            required
            placeholder="Choose a username"
            className={inputClassName(Boolean(getFirstError('username')))}
          />
          {getFirstError('username') && (
            <span className="text-xs text-red-600">{getFirstError('username')}</span>
          )}
        </div>

        <div className="space-y-1">
          <label htmlFor="email" className="text-sm font-medium text-gray-700">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            value={formData.email}
            onChange={handleChange}
            required
            placeholder="Enter your email"
            className={inputClassName(Boolean(getFirstError('email')))}
          />
          {getFirstError('email') && (
            <span className="text-xs text-red-600">{getFirstError('email')}</span>
          )}
        </div>

        <div className="space-y-1">
          <label htmlFor="password" className="text-sm font-medium text-gray-700">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            value={formData.password}
            onChange={handleChange}
            required
            placeholder="Create a password"
            className={inputClassName(Boolean(getFirstError('password')))}
          />
          {getFirstError('password') && (
            <span className="text-xs text-red-600">{getFirstError('password')}</span>
          )}
        </div>

        <div className="space-y-1">
          <label htmlFor="password_confirm" className="text-sm font-medium text-gray-700">
            Confirm Password
          </label>
          <input
            id="password_confirm"
            name="password_confirm"
            type="password"
            value={formData.password_confirm}
            onChange={handleChange}
            required
            placeholder="Confirm your password"
            className={inputClassName(Boolean(getFirstError('password_confirm')))}
          />
          {getFirstError('password_confirm') && (
            <span className="text-xs text-red-600">{getFirstError('password_confirm')}</span>
          )}
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full rounded-xl h-12 bg-blue-600 text-white font-medium transition-transform duration-150 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Creating Profile...' : 'Create Profile'}
        </button>

        <div className="w-full">
          <div className="w-full text-center text-sm text-gray-500">or</div>
        </div>

        <div
          className={`w-full flex justify-center ${isLoading ? 'opacity-70 pointer-events-none' : ''
            }`}
        >
          <button
            type="button"
            onClick={() => googleAuth()}
            disabled={isLoading}
            className="w-full rounded-xl h-12 bg-white text-gray-700 font-medium border border-gray-300 hover:bg-gray-50 flex items-center justify-center gap-3"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            <span>Continue with Google</span>
          </button>
        </div>

        <p className="text-center text-sm text-gray-600">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 underline">
            Sign In
          </Link>
        </p>
      </form>
    </div>
  );
};

const RegisterPage: React.FC = () => {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) {
      navigate('/');
    }
  }, [loading, user, navigate]);

  return (
    <>
      <div
        className="min-h-screen w-full flex items-end justify-center relative overflow-hidden md:hidden"
        style={{
          backgroundImage: `url(${LoginImg})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      >
        <div className="w-full max-w-md mx-auto">
          <RegisterForm />
        </div>
      </div>

      <div className="hidden md:flex flex-col min-h-screen w-full relative">
        <div
          className="flex-1 w-full bg-cover bg-center"
          style={{ backgroundImage: `url(${LoginImg})` }}
        />
        <div className="flex-1 w-full bg-white" />

        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-30 w-full max-w-md px-4">
          <div className="mx-auto">
            <RegisterForm />
          </div>
        </div>
      </div>
    </>
  );
};

export default RegisterPage;