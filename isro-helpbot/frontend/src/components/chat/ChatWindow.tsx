'use client';
import React, { useState, useEffect, useRef } from 'react';
import { Box, Paper, Typography, CircularProgress, Button } from '@mui/material';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import ContextPanel from './ContextPanel';
import { ErrorBoundary, FallbackProps } from 'react-error-boundary';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
  context?: Record<string, any>;
}

interface Session {
  id: string;
  context: Record<string, any>;
  lastActive: Date;
}

const ErrorFallback: React.FC<FallbackProps> = ({ error, resetErrorBoundary }) => {
  return (
    <Paper sx={{ p: 3, textAlign: 'center' }}>
      <Typography variant="h6" color="error">Something went wrong</Typography>
      <Typography variant="body2" sx={{ mt: 1, mb: 2 }}>{error.message}</Typography>
      <Button onClick={resetErrorBoundary} variant="outlined">Try again</Button>
    </Paper>
  );
};

export default function ChatWindow() {
  const [session, setSession] = useState<Session>({
    id: '',
    context: {},
    lastActive: new Date()
  });

  const [messages, setMessages] = useState<Message[]>([{
    id: '1',
    text: 'Hello! I\'m your MOSDAC AI Assistant. How can I help you?',
    sender: 'bot',
    timestamp: new Date(Date.now())
  }]);
  
  const [contextData, setContextData] = useState({
    currentTopic: '',
    relevantDocs: [],
    relatedQuestions: []
  });
  
  const [isConnecting, setIsConnecting] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionAttempts, setConnectionAttempts] = useState(0);
  const wsRef = useRef<WebSocket | null>(null);
  const MAX_RECONNECT_ATTEMPTS = 5;

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
    if (session.id) {
      localStorage.setItem('chat_session', JSON.stringify(session));
    }
  }, [session]);

  useEffect(() => {
    function connect() {
      try {
        setIsConnecting(true);
        const ws = new WebSocket('ws://localhost:8000/ws');
        
        ws.onopen = () => {
          console.log('Connected to WebSocket server');
          setIsConnecting(false);
          setError(null);
          setConnectionAttempts(0);
        };

        ws.onclose = () => {
          console.log('WebSocket connection closed');
          setError('Connection lost. Attempting to reconnect...');
          // Try to reconnect after 3 seconds
          setTimeout(connect, 3000);
        };

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          
          // Update messages
          setMessages(prev => [...prev, {
            id: data.id || Date.now().toString(),
            text: data.text,
            sender: data.sender || 'bot',
            timestamp: new Date(data.timestamp || Date.now()),
            context: data.context
          }]);

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

            // Update suggestions and relevant docs in the UI
            if (data.context.suggestedQuestions) {
              setContextData(prev => ({
                ...prev,
                currentTopic: data.context.topic || prev.currentTopic,
                relevantDocs: data.context.relevantDocs || prev.relevantDocs,
                relatedQuestions: data.context.suggestedQuestions
              }));
            }
          }
          
          setIsProcessing(false);
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setIsConnecting(false);
          setConnectionAttempts(prev => prev + 1);
          
          if (connectionAttempts < MAX_RECONNECT_ATTEMPTS) {
            const delay = Math.min(1000 * Math.pow(2, connectionAttempts), 10000);
            setError(`Connection failed. Retrying in ${delay/1000} seconds... (Attempt ${connectionAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`);
            setTimeout(connect, delay);
          } else {
            setError('Connection failed. Please check if the server is running on port 8000 and refresh the page to try again.');
          }
        };

        wsRef.current = ws;
      } catch (err) {
        setError('Failed to connect');
        setIsConnecting(false);
      }
    }

    connect();
    return () => wsRef.current?.close();
  }, []);

  const sendMessage = async (text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected');
      return;
    }

    try {
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        text,
        sender: 'user',
        timestamp: new Date()
      }]);
      
      setIsProcessing(true);
      setError(null);

      wsRef.current.send(JSON.stringify({ 
        text,
        timestamp: new Date().toISOString(),
        context: session.context
      }));
    } catch (err) {
      console.error('Failed to send message:', err);
      setError('Failed to send message. Please try again.');
      setIsProcessing(false);
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