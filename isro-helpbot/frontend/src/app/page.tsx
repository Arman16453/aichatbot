'use client';

import { Inter } from "next/font/google";
import { useState } from "react";
import { Tabs, Tab, Box, Paper } from "@mui/material";
import ChatWindow from "@/components/chat/ChatWindow";
import SearchInterface from "@/components/SearchInterface";
import AdminDashboard from "@/components/AdminDashboard";

const inter = Inter({ subsets: ["latin"] });

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`main-tabpanel-${index}`}
      aria-labelledby={`main-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 1 }}>{children}</Box>}
    </div>
  );
}

export default function Home() {
  const [tabValue, setTabValue] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <main
      className={`flex min-h-screen flex-col items-center p-8 ${inter.className}`}
      style={{ background: '#f0f2f5' }}
    >
      <div className="w-full max-w-6xl">
        <div className="mb-6">
          <h1 className="text-4xl font-bold text-center text-gray-800">
            MOSDAC AI Assistant
          </h1>
          <p className="text-center text-gray-600 mt-2">
            Intelligent satellite data assistance powered by ISRO
          </p>
        </div>

        <Paper elevation={3} style={{ borderRadius: '12px', overflow: 'hidden' }}>
          <Tabs
            value={tabValue}
            onChange={handleTabChange}
            indicatorColor="primary"
            textColor="primary"
            variant="fullWidth"
            sx={{
              backgroundColor: '#1976d2',
              '& .MuiTab-root': {
                color: 'white',
                fontWeight: 'bold',
              },
              '& .Mui-selected': {
                color: 'white !important',
              },
              '& .MuiTabs-indicator': {
                backgroundColor: 'white',
                height: '3px',
              },
            }}
          >
            <Tab label="🤖 Chat Assistant" />
            <Tab label="🔍 Search Portal" />
            <Tab label="⚙️ Admin Dashboard" />
          </Tabs>

          <TabPanel value={tabValue} index={0}>
            <ChatWindow />
          </TabPanel>
          
          <TabPanel value={tabValue} index={1}>
            <SearchInterface />
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <AdminDashboard />
          </TabPanel>
        </Paper>
      </div>
    </main>
  );
}