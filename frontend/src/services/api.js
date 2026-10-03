import axios from 'axios';

// Resolve backend API URL with production-safe fallback
// Production Backend: https://breakfast-management.onrender.com
// Development Backend: http://localhost:5000
const getBaseURL = () => {
  const isDev = import.meta.env.DEV;
  const envUrl = import.meta.env.VITE_API_URL;

  let targetUrl = '';
  if (envUrl && typeof envUrl === 'string' && envUrl.trim() !== '') {
    targetUrl = envUrl.trim();
  } else if (isDev || (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'))) {
    // Local development fallback
    targetUrl = 'http://localhost:5001';
  } else {
    // Production safe fallback: NEVER make requests to Vercel origin /api
    targetUrl = 'https://breakfast-management.onrender.com';
  }

  const cleanUrl = targetUrl.replace(/\/+$/, '');
  return cleanUrl.endsWith('/api') ? cleanUrl : `${cleanUrl}/api`;
};

const API = axios.create({
  baseURL: getBaseURL(),
  timeout: 30000
});

// Attach JWT bearer token and role headers
API.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  const activeRole = localStorage.getItem('activeRole');

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  if (activeRole) {
    config.headers['X-Role-Used'] = activeRole;
  }

  return config;
}, (error) => {
  return Promise.reject(error);
});

// Intercept 401 unauthenticated errors
API.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default API;
