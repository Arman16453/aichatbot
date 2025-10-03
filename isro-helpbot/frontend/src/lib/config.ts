'use client';

// Type definitions
interface Config {
    API_URL: string;
    WS_URL: string;
    TIMEOUT: number;
    RETRY: {
        MAX_ATTEMPTS: number;
        INITIAL_DELAY: number;
        MAX_DELAY: number;
    };
}

// API Configuration
export const config: Config = {
    API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001',
    WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8001',
    TIMEOUT: 30000,       // Increased timeout to 30 seconds
    RETRY: {
        MAX_ATTEMPTS: 3,  // Reduced attempts but with longer timeouts
        INITIAL_DELAY: 1000,  // Start with 1 second delay
        MAX_DELAY: 30000     // Allow up to 30 second delay
    }
};

// API Endpoints type
type EndpointConfig = {
    CREATE_SESSION: string;
    GET_MESSAGES: (sessionId: string) => string;
    WEBSOCKET: (sessionId: string) => string;
};

// API Endpoints
export const ENDPOINTS: EndpointConfig = {
    CREATE_SESSION: '/api/sessions/create',
    GET_MESSAGES: (sessionId: string) => `/api/messages/${sessionId}`,
    WEBSOCKET: (sessionId: string) => `/ws/${sessionId}`
} as const;

// URL Helpers with type safety
export function getApiUrl(endpoint: string): string {
    return `${config.API_URL}${endpoint}`;
}

export function getWsUrl(endpoint: string): string {
    return `${config.WS_URL}${endpoint}`;
}

// Export config types for use in other files
export type { Config, EndpointConfig };