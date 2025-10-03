'use client';

import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import TimeStamp from './TimeStamp';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot' | 'system';
  timestamp: Date;
  status: 'sent' | 'received' | 'processing' | 'completed' | 'error';
  error?: string;
  context?: Record<string, any>;
  in_response_to?: string;
  session_id: string;
}

interface MessageListProps {
  messages: Message[];
}

const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {messages.map((message) => (
        <Box
          key={message.id}
          sx={{
            display: 'flex',
            justifyContent: message.sender === 'user' ? 'flex-end' : 'flex-start',
            opacity: 1,
            transform: 'translateY(0)',
            transition: 'opacity 0.3s ease, transform 0.3s ease',
            '&:new': {
              opacity: 0,
              transform: 'translateY(20px)'
            }
          }}
        >
          <Paper
            elevation={0}
            sx={{
              p: 2,
              maxWidth: '70%',
              bgcolor: message.sender === 'user' ? 'primary.main' : 
                      message.sender === 'system' ? '#e3f2fd' : '#f8f9fa',
              color: message.sender === 'user' ? 'white' : 'text.primary',
              borderRadius: message.sender === 'user' ? '20px 20px 5px 20px' : '20px 20px 20px 5px',
              boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
              opacity: message.status === 'error' ? 0.7 : 1,
              position: 'relative'
            }}
          >
            <Typography variant="body1">{message.text}</Typography>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              mt: 1 
            }}>
              <TimeStamp date={message.timestamp} />
              {message.status && message.status !== 'completed' && (
                <Typography 
                  variant="caption" 
                  sx={{ 
                    ml: 1,
                    color: message.status === 'error' ? 'error.main' : 
                           message.sender === 'user' ? 'white' : 'text.secondary'
                  }}
                >
                  {message.status === 'error' ? 'Error sending message' :
                   message.status === 'processing' ? 'Processing...' :
                   message.status === 'sent' ? 'Sent' :
                   message.status === 'received' ? 'Received' : ''}
                </Typography>
              )}
            </Box>
            {message.error && (
              <Typography 
                variant="caption" 
                sx={{ 
                  color: 'error.main',
                  display: 'block',
                  mt: 1
                }}
              >
                {message.error}
              </Typography>
            )}
          </Paper>
        </Box>
      ))}
    </Box>
  );
};

export default MessageList;