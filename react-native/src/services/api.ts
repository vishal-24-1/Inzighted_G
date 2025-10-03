import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// API Configuration
const DEFAULT_PROD_API = 'https://server.inzighted.com/api';
const DEFAULT_DEV_API = 'http://10.0.2.2:8000/api'; // Android emulator localhost
export const PRODUCT_URL = __DEV__ 
  ? 'http://10.0.2.2:3000' 
  : 'https://app.inzighted.com';

const API_BASE_URL = __DEV__ ? DEFAULT_DEV_API : DEFAULT_PROD_API;

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Refresh flow helpers - prevent concurrent refresh calls
let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;
const subscribers: Array<(token: string | null) => void> = [];

function subscribeTokenRefresh(cb: (token: string | null) => void) {
  subscribers.push(cb);
}

function onRefreshed(token: string | null) {
  subscribers.forEach(cb => cb(token));
  subscribers.length = 0;
}

async function getAccessToken(): Promise<string | null> {
  try {
    return await AsyncStorage.getItem('access_token');
  } catch (error) {
    console.error('Error getting access token:', error);
    return null;
  }
}

async function getRefreshToken(): Promise<string | null> {
  try {
    return await AsyncStorage.getItem('refresh_token');
  } catch (error) {
    console.error('Error getting refresh token:', error);
    return null;
  }
}

async function setTokens(access: string, refresh?: string | null): Promise<void> {
  try {
    await AsyncStorage.setItem('access_token', access);
    if (refresh) {
      await AsyncStorage.setItem('refresh_token', refresh);
    }
  } catch (error) {
    console.error('Error setting tokens:', error);
  }
}

async function clearTokens(): Promise<void> {
  try {
    await AsyncStorage.removeItem('access_token');
    await AsyncStorage.removeItem('refresh_token');
  } catch (error) {
    console.error('Error clearing tokens:', error);
  }
}

// Request interceptor: attach access token
api.interceptors.request.use(async (config: any) => {
  const token = await getAccessToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401 with refresh queue
api.interceptors.response.use(
  response => response,
  async (error) => {
    const originalRequest = error.config;
    if (!originalRequest) return Promise.reject(error);

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (!isRefreshing) {
        isRefreshing = true;
        refreshPromise = (async () => {
          const refreshToken = await getRefreshToken();
          if (!refreshToken) {
            await clearTokens();
            return null;
          }
          try {
            const resp = await axios.post(`${API_BASE_URL}/auth/refresh/`, { 
              refresh: refreshToken 
            });
            const access = resp.data.access;
            await setTokens(access);
            onRefreshed(access);
            return access;
          } catch (err) {
            await clearTokens();
            onRefreshed(null);
            return null;
          } finally {
            isRefreshing = false;
            refreshPromise = null;
          }
        })();
      }

      return refreshPromise!.then((newAccessToken) => {
        if (!newAccessToken) {
          // Auth failed - will be handled by AuthContext
          return Promise.reject(error);
        }

        // Update header and retry original request
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
        }
        return api(originalRequest);
      });
    }

    return Promise.reject(error);
  }
);

// API Endpoints
export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/auth/login/', { email, password }),
  
  register: (email: string, username: string, name: string, password: string, password_confirm: string) =>
    api.post('/auth/register/', { email, username, name, password, password_confirm }),
  
  getProfile: () => api.get('/auth/profile/'),
  
  updateProfile: (data: any) => api.put('/auth/profile/', data),
};

export const documentsAPI = {
  list: () => api.get('/documents/'),
  
  upload: (formData: FormData) => {
    return api.post('/ingest/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 120000, // 2 minutes for file upload
    });
  },
  
  query: (query: string) => api.post('/query/', { query }),
};

export const chatAPI = {
  sendMessage: (message: string, sessionId?: string) => 
    api.post('/chat/', { message, session_id: sessionId }),
  
  getSessions: () => api.get('/chat/sessions/'),
  
  getSessionDetail: (sessionId: string) => 
    api.get(`/chat/sessions/${sessionId}/`),
  
  deleteSession: (sessionId: string) => 
    api.delete(`/chat/sessions/${sessionId}/`),
};

export const tutoringAPI = {
  startSession: (documentId?: string) => 
    api.post('/tutoring/start/', { document_id: documentId }),
  
  submitAnswer: (sessionId: string, text: string) =>
    api.post(`/tutoring/${sessionId}/answer/`, { text }),
  
  endSession: (sessionId: string) =>
    api.post(`/tutoring/${sessionId}/end/`),
  
  getSessionDetail: (sessionId: string) =>
    api.get(`/tutoring/${sessionId}/`),
};

export const insightsAPI = {
  getUserSessions: () => api.get('/sessions/'),
  
  getSessionInsights: (sessionId: string) =>
    api.get(`/sessions/${sessionId}/insights/`),
};

// Token management utilities
export const tokenUtils = {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
};

export default api;