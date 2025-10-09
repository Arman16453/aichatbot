'use client';
import React, { useState, useEffect, useRef } from 'react';
import { Box, Paper, Typography, CircularProgress } from '@mui/material';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { api, NetworkError, TimeoutError } from '@/services/api';
import { getWsUrl } from '@/lib/config';

interface ChatSession {
  session_id: string;
  context: Record<string, unknown>;
  lastActive: Date;
  created_at: Date;
}

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot' | 'system';
  timestamp: Date;
  status?: 'sent' | 'received' | 'processing' | 'completed' | 'error';
  error?: string;
  context?: Record<string, unknown>;
  in_response_to?: string;
}


export default function ChatWindow() {
  const [session, setSession] = useState<ChatSession>({
    session_id: '',
    context: {},
    lastActive: new Date(),
    created_at: new Date()
  });

  const [messages, setMessages] = useState<Message[]>([{
    id: '1',
    text: 'Hello! I\'m your MOSDAC AI Assistant. How can I help you?',
    sender: 'bot',
    timestamp: new Date(Date.now())
  }]);
  
  
  const [isConnecting, setIsConnecting] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<number | null>(null);
  const isUnmounted = useRef(false);
  const outgoingQueue = useRef<Array<string>>([]);

  // Load session from localStorage
  useEffect(() => {
    const savedSession = localStorage.getItem('chat_session');
    if (savedSession) {
      const parsed = JSON.parse(savedSession);
      setSession({
        ...parsed,
        lastActive: new Date(parsed.lastActive)
      });
    }
  }, []);

  // Save session to localStorage
  useEffect(() => {
    if (session.session_id) {
      localStorage.setItem('chat_session', JSON.stringify(session));
    }
  }, [session]);

  // Create or load session
  useEffect(() => {
    let mounted = true;
    
    async function initSession() {
      if (!mounted) return;
      
      setIsConnecting(true);
      setError(null);
      
      try {
        // First try to load from localStorage
        const savedSession = localStorage.getItem('chat_session');
        if (savedSession) {
          try {
            const parsed = JSON.parse(savedSession);
            if (parsed.session_id) {
              // Validate session with backend
              try {
                await api.getMessages(parsed.session_id);
                if (mounted) {
                  setSession({
                    ...parsed,
                    lastActive: new Date(parsed.lastActive),
                    created_at: new Date(parsed.created_at)
                  });
                  setIsConnecting(false);
                  return;
                }
              } catch (e) {
                console.warn('Invalid session, creating new one:', e);
                localStorage.removeItem('chat_session');
              }
            }
          } catch (e) {
            console.warn('Invalid session in localStorage:', e);
            localStorage.removeItem('chat_session');
          }
        }

        // If no valid session in localStorage, create a new one
        const sessionData = await api.createSession();
        
        if (sessionData?.session_id) {
          const newSession = {
            session_id: sessionData.session_id,
            context: {},
            lastActive: new Date(),
            created_at: new Date(sessionData.created_at)
          };
          setSession(newSession);
          localStorage.setItem('chat_session', JSON.stringify(newSession));
        } else {
          throw new Error('Invalid session data received');
        }
      } catch (error) {
        console.error('Failed to create session:', error);
        
        if (mounted) {
          if (error instanceof NetworkError) {
            setError(
              error.status === 503
                ? 'Chat service is temporarily unavailable. Please try again later.'
                : error.message
            );
          } else if (error instanceof TimeoutError) {
            setError('Connection timed out. Please check your internet connection.');
          } else {
            setError('Unable to connect to chat server. Please try again later.');
          }
          
          // Clear any existing session data if we hit an error
          localStorage.removeItem('chat_session');
        }
      } finally {
        if (mounted) {
          setIsConnecting(false);
        }
      }
    }

    initSession();

    // Cleanup function
    return () => {
      mounted = false;
      setError(null);
    };
  }, []);

  useEffect(() => {
    // Connect with guard to avoid duplicate sockets
    function scheduleReconnect(delayMs: number) {
      if (isUnmounted.current) return;
      if (reconnectTimer.current) window.clearTimeout(reconnectTimer.current as number);
      reconnectTimer.current = window.setTimeout(() => {
        reconnectTimer.current = null;
        connect();
      }, delayMs);
    }

    async function connect() {
      if (!session.session_id) return;

      // If a socket already exists and is open or connecting, do not create a new one
      if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
        return;
      }

      try {
        setIsConnecting(true);
        const url = getWsUrl(`/ws/${session.session_id}`);
        const ws = new WebSocket(url);

        ws.onopen = () => {
          console.log('Connected to WebSocket server', url);
          reconnectAttempts.current = 0;
          setIsConnecting(false);
          setError(null);
          // Flush any queued messages
          try {
            while (outgoingQueue.current.length > 0 && ws.readyState === WebSocket.OPEN) {
              const msg = outgoingQueue.current.shift();
              if (msg) ws.send(msg);
            }
          } catch (e) {
            console.warn('Error flushing outgoing queue:', e);
          }
        };

        ws.onclose = (event) => {
          console.log('WebSocket connection closed:', event.code, event.reason);
          wsRef.current = null;
          // Only attempt reconnect for abnormal closures
          if (!isUnmounted.current && event.code !== 1000) {
            reconnectAttempts.current = (reconnectAttempts.current || 0) + 1;
            const delay = Math.min(3000 * Math.pow(2, reconnectAttempts.current - 1), 30000);
            console.warn(`Socket closed unexpectedly (code=${event.code}). Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`);
            setError('Connection lost. Attempting to reconnect...');
            scheduleReconnect(delay);
          }
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            // Handle message updates
            setMessages(prev => {
              const msgIndex = prev.findIndex(msg => msg.id === data.id);

              if (msgIndex >= 0) {
                // Update existing message
                const updatedMessages = [...prev];
                updatedMessages[msgIndex] = {
                  ...updatedMessages[msgIndex],
                  ...data,
                  timestamp: new Date(data.timestamp)
                };
                return updatedMessages;
              } else {
                // Add new message
                return [...prev, {
                  ...data,
                  timestamp: new Date(data.timestamp)
                }];
              }
            });

            // Update processing state based on message status
            if (data.status === 'processing') {
              setIsProcessing(true);
            } else if (['completed', 'error'].includes(data.status)) {
              setIsProcessing(false);
            }

            // Update session context if provided
            if (data.context) {
              setSession(prev => ({
                ...prev,
                context: {
                  ...prev.context,
                  ...data.context
                },
                lastActive: new Date()
              }));

            }

            setIsProcessing(false);
          } catch (error) {
            console.error('Error handling WebSocket message:', error, 'Raw data:', event.data);
          }
        };

        ws.onerror = (event) => {
          // The native Event object can be opaque in some browsers/environments.
          // Avoid trying to JSON-serialize it. Instead log a small, safe summary.
          try {
            const state = ws?.readyState;
            const evType = (event && (event as Event).type) ? (event as Event).type : 'error';
            // Log a safe, human-readable message rather than passing an object which
            // some error collectors render as `{}`. This avoids confusing logs.
            console.error(`WebSocket encountered an error: type=${evType} state=${state}`);
            // Some environments attach a message field
            try {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              const maybeMsg = (event as any)?.message;
              if (maybeMsg) console.error('WebSocket error message:', maybeMsg);
            } catch {}
          } catch (e) {
            console.error('WebSocket error (logging failed):', e);
          }

          // Provide a user-facing error depending on socket state.
          if (ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) {
            setError('Connection failed. Please check if the server is running and try again.');
          } else {
            setError('WebSocket connection error. Attempting to reconnect...');
          }

          // Close socket to ensure the onclose handler runs and schedules reconnect
          try {
            ws.close();
          } catch (e) {
            console.warn('Error closing websocket after error:', e);
          }
          wsRef.current = null;
        };

        wsRef.current = ws;
      } catch (err) {
        console.error('Failed to create WebSocket:', err);
        setError('Failed to connect');
        setIsConnecting(false);
        // schedule reconnect
        reconnectAttempts.current = (reconnectAttempts.current || 0) + 1;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current - 1), 30000);
        scheduleReconnect(delay);
      }
    }

    connect();

    return () => {
      isUnmounted.current = true;
      if (reconnectTimer.current) {
        window.clearTimeout(reconnectTimer.current as number);
        reconnectTimer.current = null;
      }
      try {
        wsRef.current?.close();
      } catch (e) {
        // ignore
      }
      wsRef.current = null;
    };
  }, [session.session_id]);

  const sendMessage = async (text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      // Queue the message so it's sent when connection is restored
      setError('Not connected to server. Your message will be sent when reconnected.');
      const messageId = crypto.randomUUID();
      const newMessage: Message = {
        id: messageId,
        text,
        sender: 'user',
        timestamp: new Date(),
        status: 'sent'
      };

      // Add message to UI immediately
      setMessages(prev => [...prev, newMessage]);

      // Queue send payload
      const payload = JSON.stringify({ id: messageId, text, timestamp: new Date().toISOString() });
      outgoingQueue.current.push(payload);
      return;
    }

    const messageId = crypto.randomUUID();
    const newMessage: Message = {
      id: messageId,
      text,
      sender: 'user',
      timestamp: new Date(),
      status: 'sent'
    };

    try {
      // Add message to UI immediately with 'sent' status
      setMessages(prev => [...prev, newMessage]);

      // Send message through WebSocket
      const payload = JSON.stringify({ id: messageId, text, timestamp: new Date().toISOString() });
      try {
        wsRef.current.send(payload);
      } catch (e) {
        console.warn('WebSocket send failed, queueing message:', e);
        outgoingQueue.current.push(payload);
        setError('Message queued; will be sent when reconnected.');
      }

      // Update session's last active timestamp
      setSession(prev => ({
        ...prev,
        lastActive: new Date()
      }));

    } catch (error) {
      console.error('Failed to send message:', error);

      // Update message status to error
      setMessages(prev => prev.map(msg =>
        msg.id === messageId
          ? { ...msg, status: 'error', error: 'Failed to send message' }
          : msg
      ));

      setError('Failed to send message. Please try again.');
    }
  };

  return (
    <Paper elevation={3} sx={{
      height: 'calc(100vh - 200px)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden'
    }}>
      <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
        <MessageList messages={messages} />
      </Box>
      
      {error && (
        <Typography color="error" sx={{ p: 1, textAlign: 'center' }}>
          {error}
        </Typography>
      )}

      {isConnecting && (
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'center' }}>
          <CircularProgress size={20} /> 
          <Typography sx={{ ml: 1 }}>Connecting...</Typography>
        </Box>
      )}

      <Box sx={{ p: 2, borderTop: 1, borderColor: 'divider' }}>
        <MessageInput 
          onSend={sendMessage}
          isProcessing={isProcessing}
          error={error}
          suggestions={[]}
        />
      </Box>
    </Paper>
  );
}