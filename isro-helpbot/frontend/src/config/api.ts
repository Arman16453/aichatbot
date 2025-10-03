// API configuration
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

// API endpoints
export const ENDPOINTS = {
  CREATE_SESSION: '/api/sessions/create',
  GET_MESSAGES: (sessionId: string) => `/api/messages/${sessionId}`,
  WEBSOCKET: (sessionId: string) => `/ws/${sessionId}`
};

// API request timeouts (in milliseconds)
export const REQUEST_TIMEOUT = 5000;

// Connection retry settings
export const RETRY_CONFIG = {
  maxAttempts: 3,
  initialDelay: 1000, // 1 second
  maxDelay: 5000,     // 5 seconds
};

// WebSocket reconnect settings
export const WS_RECONNECT_CONFIG = {
  maxAttempts: 5,
  initialDelay: 1000,
  maxDelay: 10000,
};

// Function to get full API URL
export const getApiUrl = (endpoint: string): string => {
  return `${API_BASE_URL}${endpoint}`;
};

// Function to get WebSocket URL
export const getWsUrl = (endpoint: string): string => {
  return `${WS_BASE_URL}${endpoint}`;
};