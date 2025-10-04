'use client';

import React from 'react';
import { Box, Paper, Typography, List, ListItem, Link, Chip } from '@mui/material';
import { Info as InfoIcon } from '@mui/icons-material';

interface ContextPanelProps {
  currentTopic: string;
  relevantDocs: Array<{
    title: string;
    url: string;
    confidence: number;
  }>;
  relatedQuestions: string[];
}

const ContextPanel: React.FC<ContextPanelProps> = ({
  currentTopic,
  relevantDocs,
  relatedQuestions
}) => {
  return (
    <Paper 
      elevation={0}
      sx={{ 
        width: '300px',
        p: 2,
        height: '100%',
        backgroundColor: 'rgba(255, 255, 255, 0.8)',
        backdropFilter: 'blur(10px)',
        borderLeft: '1px solid rgba(0, 0, 0, 0.12)'
      }}
    >
      <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <InfoIcon fontSize="small" />
        Context
      </Typography>

      {currentTopic && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle2" color="primary">
            Current Topic
          </Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            {currentTopic}
          </Typography>
        </Box>
      )}

      {relevantDocs.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle2" color="primary">
            Related Documents
          </Typography>
          <List dense sx={{ mt: 1 }}>
            {relevantDocs.map((doc, index) => (
              <ListItem key={index} sx={{ px: 0 }}>
                <Link 
                  href={doc.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{ 
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    textDecoration: 'none',
                    '&:hover': { textDecoration: 'underline' }
                  }}
                >
                  <Typography variant="body2" noWrap>{doc.title}</Typography>
                  <Chip 
                    label={`${Math.round(doc.confidence * 100)}%`}
                    size="small"
                    sx={{ height: '20px' }}
                  />
                </Link>
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {relatedQuestions.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle2" color="primary">
            You might also ask
          </Typography>
          <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {relatedQuestions.map((question, index) => (
              <Chip
                key={index}
                label={question}
                size="small"
                variant="outlined"
                sx={{ 
                  borderRadius: '4px',
                  cursor: 'pointer',
                  '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.04)' }
                }}
              />
            ))}
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default ContextPanel;