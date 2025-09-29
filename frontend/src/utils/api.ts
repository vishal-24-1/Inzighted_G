import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
            refresh: refreshToken,
          });
          
          const { access } = response.data;
          localStorage.setItem('access_token', access);
          
          return api(originalRequest);
        } catch (refreshError) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    
    return Promise.reject(error);
  }
);

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
  
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/ingest/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  query: (query: string) => api.post('/query/', { query }),
};

export default api;