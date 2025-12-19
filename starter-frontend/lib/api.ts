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
// Analytics API (for Developer Dashboard)
export const analyticsAPI = {
  getOverview: async () => {
    const response = await apiClient.get('/analytics/overview');
    return response.data;
  },

  getTimeline: async (days: number = 7) => {
    const response = await apiClient.get(`/analytics/timeline?days=${days}`);
    return response.data;
  },

  getApiKeyUsage: async () => {
    const response = await apiClient.get('/analytics/api-keys');
    return response.data;
  },
};

// Search Jobs API (for Developer Dashboard)
export const searchJobsAPI = {
  listJobs: async (params?: { status?: string; page?: number; per_page?: number }) => {
    const response = await apiClient.get('/search/jobs', { params });
    return response.data;
  },

  getJobDetails: async (jobId: string) => {
    const response = await apiClient.get(`/search/jobs/${jobId}`);
    return response.data;
  },
};
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
  listVideos: async (page?: number, perPage?: number) => {
    const params: any = {};
    if (page) params.page = page;
    if (perPage) params.per_page = perPage;
    const response = await apiClient.get('/videos', { params });
    return response.data;
  },

  getVideo: async (videoId: number) => {
    const response = await apiClient.get(`/videos/${videoId}`);
    return response.data;
  },

  createVideo: async (data: { title: string; description?: string; duration?: number }) => {
    const response = await apiClient.post('/videos', data);
    return response.data;
  },

  updateVideo: async (videoId: number, data: Partial<{ title: string; description: string; duration: number }>) => {
    const response = await apiClient.put(`/videos/${videoId}`, data);
    return response.data;
  },

  deleteVideo: async (videoId: number) => {
    const response = await apiClient.delete(`/videos/${videoId}`);
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

