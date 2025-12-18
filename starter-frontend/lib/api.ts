/**
 * API Client
 * 
 * TODO: Candidates should complete this API client to:
 * 1. Handle authentication (JWT token storage)
 * 2. Add all necessary API methods
 * 3. Handle errors properly
 */

import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

// Create axios instance
const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    // TODO: Get JWT token from storage and add to headers
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // TODO: Handle 401 errors (logout user)
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: async (email: string, password: string, name?: string) => {
    const response = await apiClient.post('/auth/register', { email, password, name });
    return response.data;
  },
  
  login: async (email: string, password: string) => {
    const response = await apiClient.post('/auth/login', { email, password });
    // TODO: Store token in localStorage
    if (response.data.token && typeof window !== 'undefined') {
      localStorage.setItem('token', response.data.token);
    }
    return response.data;
  },
  
  logout: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
    }
  },
};

// Video API
export const videoAPI = {
  listVideos: async (userId: number, page?: number, perPage?: number) => {
    const params = new URLSearchParams();
    if (page) params.append('page', page.toString());
    if (perPage) params.append('per_page', perPage.toString());
    const query = params.toString();
    const url = `/users/${userId}/videos${query ? `?${query}` : ''}`;
    const response = await apiClient.get(url);
    return response.data;
  },
  
  getVideo: async (userId: number, videoId: number) => {
    const response = await apiClient.get(`/users/${userId}/videos/${videoId}`);
    return response.data;
  },
  
  createVideo: async (userId: number, data: { title: string; description?: string; duration?: number }) => {
    const response = await apiClient.post(`/users/${userId}/videos`, data);
    return response.data;
  },
  
  updateVideo: async (userId: number, videoId: number, data: Partial<{ title: string; description: string; duration: number }>) => {
    const response = await apiClient.put(`/users/${userId}/videos/${videoId}`, data);
    return response.data;
  },
  
  deleteVideo: async (userId: number, videoId: number) => {
    const response = await apiClient.delete(`/users/${userId}/videos/${videoId}`);
    return response.data;
  },
};

// Search API
export const searchAPI = {
  submitSearch: async (userId: number, query: string, videoIds?: number[]) => {
    const response = await apiClient.post(`/users/${userId}/search`, { query, video_ids: videoIds });
    return response.data;
  },
  
  getSearchResults: async (userId: number, jobId: string) => {
    const response = await apiClient.get(`/users/${userId}/search/${jobId}`);
    return response.data;
  },
};

// API Key API
export const apiKeyAPI = {
  createApiKey: async (name: string) => {
    const response = await apiClient.post('/auth/api-keys', { name });
    return response.data;
  },
  
  listApiKeys: async () => {
    const response = await apiClient.get('/auth/api-keys');
    return response.data;
  },
  
  deleteApiKey: async (keyId: string) => {
    const response = await apiClient.delete(`/auth/api-keys/${keyId}`);
    return response.data;
  },
};

export default apiClient;

