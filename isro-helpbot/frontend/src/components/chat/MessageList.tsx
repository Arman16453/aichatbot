'use client';

import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import TimeStamp from './TimeStamp';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
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
              bgcolor: message.sender === 'user' ? 'primary.main' : '#f8f9fa',
              color: message.sender === 'user' ? 'white' : 'text.primary',
              borderRadius: message.sender === 'user' ? '20px 20px 5px 20px' : '20px 20px 20px 5px',
              boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
            }}
          >
            <Typography variant="body1">{message.text}</Typography>
            <TimeStamp date={message.timestamp} />
          </Paper>
        </Box>
      ))}
    </Box>
  );
};

export default MessageList;