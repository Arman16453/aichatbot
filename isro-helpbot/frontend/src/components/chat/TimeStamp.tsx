'use client';

import React, { useState, useEffect } from 'react';
import { Typography } from '@mui/material';

interface TimeStampProps {
  date: Date;
}

const TimeStamp: React.FC<TimeStampProps> = ({ date }) => {
  const [formattedTime, setFormattedTime] = useState<string>('');

  useEffect(() => {
    // Only format the date on the client side
    const formatter = new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
    setFormattedTime(formatter.format(date));
  }, [date]);

  // Return empty string during SSR, and formatted time on client
  return (
    <Typography 
      variant="caption" 
      sx={{ 
        display: 'block', 
        mt: 0.5, 
        opacity: 0.7 
      }}
    >
      {formattedTime}
    </Typography>
  );
};

export default TimeStamp;