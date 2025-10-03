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
    async function connect() {
      if (!session.session_id) return;
      
      try {
        setIsConnecting(true);
        const ws = new WebSocket(getWsUrl(`/ws/${session.session_id}`));
        
        ws.onopen = () => {
          console.log('Connected to WebSocket server');
          setIsConnecting(false);
          setError(null);
        };

        ws.onclose = (event) => {
          console.log('WebSocket connection closed:', event.code, event.reason);
          if (event.code !== 1000) { // Not a normal closure
            setError('Connection lost. Attempting to reconnect...');
            // Try to reconnect after 3 seconds
            setTimeout(connect, 3000);
          }
        };

        ws.onmessage = (event) => {
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
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setIsConnecting(false);
          setError('Connection failed. Please check if the server is running and try again.');
          wsRef.current = null;
        };

        wsRef.current = ws;
      } catch {
        setError('Failed to connect');
        setIsConnecting(false);
      }
    }

    connect();
    return () => wsRef.current?.close();
  }, [session.session_id]);

  const sendMessage = async (text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected to server. Please wait while we reconnect...');
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
      wsRef.current.send(JSON.stringify({
        id: messageId,
        text,
        timestamp: new Date().toISOString()
      }));
      
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