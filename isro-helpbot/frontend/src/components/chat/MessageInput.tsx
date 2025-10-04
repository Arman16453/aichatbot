'use client';

import React, { useState, useRef, useEffect } from 'react';
import { 
  TextField, 
  IconButton, 
  Box, 
  CircularProgress, 
  Paper,
  Typography,
  Chip
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';

interface MessageInputProps {
  onSend: (message: string) => void;
  isProcessing?: boolean;
  error?: string | null;
  suggestions?: string[];
}

const MAX_MESSAGE_LENGTH = 1000;

const MessageInput: React.FC<MessageInputProps> = ({ 
  onSend, 
  isProcessing = false, 
  error = null,
  suggestions = []
}) => {
  const [message, setMessage] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const validateMessage = (text: string): boolean => {
    if (text.trim().length < 2) {
      setValidationError('Message must be at least 2 characters long');
      return false;
    }
    if (text.length > MAX_MESSAGE_LENGTH) {
      setValidationError(`Message must not exceed ${MAX_MESSAGE_LENGTH} characters`);
      return false;
    }
    setValidationError(null);
    return true;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validateMessage(message)) {
      onSend(message);
      setMessage('');
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setMessage(suggestion);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      {suggestions.length > 0 && (
        <Paper 
          elevation={0} 
          sx={{ 
            p: 2, 
            mb: 2, 
            backgroundColor: 'rgba(255, 255, 255, 0.8)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <Typography variant="subtitle2" color="primary" sx={{ mb: 1 }}>
            Suggested questions
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {suggestions.map((suggestion, index) => (
              <Chip
                key={index}
                label={suggestion}
                variant="outlined"
                onClick={() => handleSuggestionClick(suggestion)}
                sx={{ borderRadius: '4px' }}
              />
            ))}
          </Box>
        </Paper>
      )}

      <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          value={message}
          onChange={(e) => {
            setMessage(e.target.value);
            validateMessage(e.target.value);
          }}
          placeholder="Type your message..."
          variant="outlined"
          size="small"
          error={Boolean(validationError || error)}
          helperText={validationError || error}
          disabled={isProcessing}
          inputRef={inputRef}
          InputProps={{
            sx: {
              borderRadius: '20px',
              backgroundColor: 'background.paper',
            }
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              '& fieldset': {
                borderColor: 'rgba(0, 0, 0, 0.12)'
              }
            }
          }}
        />
        <IconButton 
          type="submit" 
          color="primary" 
          disabled={!message.trim() || isProcessing}
          sx={{
            backgroundColor: 'primary.main',
            color: 'white',
            '&:hover': {
              backgroundColor: 'primary.dark',
            },
            '&.Mui-disabled': {
              backgroundColor: 'action.disabledBackground',
            }
          }}
        >
          {isProcessing ? (
            <CircularProgress size={24} color="inherit" />
          ) : (
            <SendIcon />
          )}
        </IconButton>
      </Box>
    </Box>
  );
};

export default MessageInput;