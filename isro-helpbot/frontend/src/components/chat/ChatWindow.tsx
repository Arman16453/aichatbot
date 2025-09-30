'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Box, Paper, Typography, CircularProgress } from '@mui/material';
import MessageList from './MessageList';
import MessageInput from './MessageInput';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

const ChatWindow: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      text: 'Hello! I\'m the MOSDAC AI Assistant. I can help you with information about satellite data, services, and other MOSDAC resources. What would you like to know?',
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const handleSendMessage = (text: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      text,
      sender: 'user',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newMessage]);

    // Simulate bot response
    setTimeout(() => {
      const botResponse: Message = {
        id: (Date.now() + 1).toString(),
        text: 'I understand your query. Let me help you with that.',
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botResponse]);
    }, 1000);
  };

  return (
    <Paper 
      elevation={3} 
      sx={{ 
        height: '600px', 
        display: 'flex', 
        flexDirection: 'column',
        overflow: 'hidden',
        borderRadius: 2
      }}
    >
      <Box sx={{ 
        p: 2, 
        backgroundColor: 'primary.main', 
        color: 'white'
      }}>
        <Typography variant="h6">MOSDAC Help Bot</Typography>
      </Box>
      <Box sx={{ 
        flexGrow: 1, 
        overflow: 'auto', 
        p: 2,
        backgroundColor: '#f5f5f5'
      }}>
        <MessageList messages={messages} />
      </Box>
      <Box sx={{ p: 2, backgroundColor: 'background.paper' }}>
        <MessageInput onSendMessage={handleSendMessage} />
      </Box>
    </Paper>
  );
};

export default ChatWindow;