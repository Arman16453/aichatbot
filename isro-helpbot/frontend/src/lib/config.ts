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
    // If the app is running in the browser, ensure the WS protocol matches the page protocol
    try {
        if (typeof window !== 'undefined') {
            const pageIsSecure = window.location.protocol === 'https:';
            // If WS_URL is provided explicitly, adapt its protocol when page is secure
            if (config.WS_URL) {
                try {
                    const u = new URL(config.WS_URL);
                    if (pageIsSecure && u.protocol === 'ws:') u.protocol = 'wss:';
                    if (!pageIsSecure && u.protocol === 'wss:') u.protocol = 'ws:';
                    return `${u.origin}${endpoint}`;
                } catch {
                    // fallback to using the string directly
                    if (pageIsSecure && config.WS_URL.startsWith('ws://')) {
                        return config.WS_URL.replace('ws://', 'wss:') + endpoint;
                    }
                    if (!pageIsSecure && config.WS_URL.startsWith('wss://')) {
                        return config.WS_URL.replace('wss://', 'ws://') + endpoint;
                    }
                    return `${config.WS_URL}${endpoint}`;
                }
            }
        }
    } catch (e) {
        // If anything goes wrong, fall back to the configured WS_URL
        console.warn('getWsUrl fallback:', e);
    }

    return `${config.WS_URL}${endpoint}`;
}

// Export config types for use in other files
export type { Config, EndpointConfig };