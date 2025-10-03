import { config, ENDPOINTS, getApiUrl } from '@/lib/config';

// API Types
export const retryWithBackoff = async <T>(
  operation: () => Promise<T>,
  maxAttempts = config.RETRY.MAX_ATTEMPTS,
  initialDelay = config.RETRY.INITIAL_DELAY,
  maxDelay = config.RETRY.MAX_DELAY
): Promise<T> => {
  let lastError: Error | null = null;
  let attempt = 1; // Start at 1 for better logging

  while (attempt <= maxAttempts) {
    try {
      // Add attempt number to error context
      console.log(`Operation attempt ${attempt}/${maxAttempts}`);
      return await operation();
    } catch (error: unknown) {
      const currentError = error instanceof Error ? error : new Error('Unknown error occurred');
      lastError = currentError;
      
      // Log the error with attempt context
      console.log(`Attempt ${attempt}/${maxAttempts} failed:`, currentError.message);
      
      // If this was the last attempt, throw the error
      if (attempt === maxAttempts) {
        console.log(`All ${maxAttempts} attempts failed`);
        break;
      }
      
      // Calculate delay with exponential backoff and jitter
      const jitter = Math.random() * 500; // Add up to 500ms of random jitter
      const delay = Math.min(initialDelay * Math.pow(2, attempt - 1) + jitter, maxDelay);
      
      console.log(`Waiting ${delay}ms before next attempt`);
      await sleep(delay);
      
      attempt++;
    }
  }

  throw lastError || new Error('Operation failed after all attempts');
}

export interface SessionResponse {
    session_id: string;
    created_at: string;
}

// API Types
export interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot' | 'system';
  timestamp: string;
  status?: 'sent' | 'received' | 'processing' | 'completed' | 'error';
  error?: string;
}

export class NetworkError extends Error {
  constructor(public status?: number, message?: string) {
    super(message || 'Network error occurred');
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends Error {
  constructor(message?: string) {
    super(message || 'Request timed out');
    this.name = 'TimeoutError';
  }
}

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

const fetchWithTimeout = async (
  url: string, 
  options: RequestInit = {}, 
  timeout = config.TIMEOUT,
  attempt = 1
) => {
  const controller = new AbortController();
  const adjustedTimeout = Math.min(timeout * Math.pow(1.5, attempt - 1), config.RETRY.MAX_DELAY);
  const timeoutId = setTimeout(() => controller.abort(), adjustedTimeout);

  try {
    // Add a small delay before retries to allow systems to recover
    if (attempt > 1) {
      const delay = Math.min(1000 * Math.pow(2, attempt - 2), 5000); // Start with 1s, max 5s
      console.log(`Waiting ${delay}ms before retry attempt ${attempt}`);
      await sleep(delay);
    }

    console.log(`Attempting fetch (attempt ${attempt}, timeout: ${adjustedTimeout}ms): ${url}`);
    
    // Add retry-specific headers to help with debugging
    const headers = new Headers(options.headers);
    headers.append('X-Retry-Attempt', attempt.toString());
    
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
      keepalive: true // Keep connection alive for slower responses
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response;
  } catch (error: unknown) {
    clearTimeout(timeoutId);
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        console.log(`Request timed out after ${adjustedTimeout}ms (attempt ${attempt})`);
        throw new TimeoutError(`Request timed out after ${adjustedTimeout}ms (attempt ${attempt})`);
      }
      console.log(`Fetch error (attempt ${attempt}):`, error.message);
    }
    throw error;
  }
};


export const api = {
  async createSession(): Promise<SessionResponse> {
    return retryWithBackoff(async () => {
      try {
        const response = await fetchWithTimeout(
          getApiUrl(ENDPOINTS.CREATE_SESSION),
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
          }
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => null) as { detail?: string } | null;
          throw new NetworkError(
            response.status,
            errorData?.detail || `Server error (${response.status})`
          );
        }

        const data = await response.json() as SessionResponse;
        return data;
      } catch (error: unknown) {
        if (error instanceof NetworkError || error instanceof TimeoutError) {
          throw error;
        }
        
        // Check if the error is due to server not running
        if (error instanceof Error && error.message.includes('Failed to fetch')) {
          throw new NetworkError(
            undefined,
            'Unable to connect to the server. Please ensure the server is running.'
          );
        }

        throw new NetworkError(
          undefined, 
          error instanceof Error ? error.message : 'An unknown error occurred'
        );
      }
    });
  },

  async getMessages(sessionId: string): Promise<Message[]> {
    return retryWithBackoff(async () => {
      const response = await fetchWithTimeout(
        getApiUrl(ENDPOINTS.GET_MESSAGES(sessionId))
      );
      if (!response.ok) {
        throw new NetworkError(response.status, 'Failed to fetch messages');
      }
      return response.json() as Promise<Message[]>;
    });
  }
};