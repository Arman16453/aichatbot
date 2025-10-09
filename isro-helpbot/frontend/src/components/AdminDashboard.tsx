'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  Button,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  Tab,
  Tabs,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
  Snackbar
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Search as SearchIcon,
  Sync as SyncIcon,
  Analytics as AnalyticsIcon,
  Storage as StorageIcon,
  Timeline as TimelineIcon
} from '@mui/icons-material';
import { API_BASE_URL } from '@/config/api';

interface DashboardStats {
  content_stats: {
    total_content: number;
    content_by_type: Record<string, number>;
    recent_content: number;
    total_views: number;
    average_feedback: number;
  };
  sync_history: Array<{
    sync_id: string;
    status: string;
    started_at: string;
    completed_at?: string;
    duration_seconds?: number;
    pages_scraped?: number;
  }>;
  analytics: {
    most_viewed: Array<{
      content_id: string;
      title: string;
      view_count: number;
      content_type: string;
    }>;
    activity_by_type: Record<string, number>;
    daily_activity: Record<string, number>;
  };
  system_status: {
    database_connected: boolean;
    last_sync: string | null;
    uptime: string;
  };
}

interface SyncResult {
  sync_id: string;
  status: string;
  pages_scraped?: number;
  duration_seconds?: number;
  error?: string;
}

interface ContentSearchResult {
  results: Array<{
    id: string;
    title: string;
    content: string;
    url: string;
    content_type: string;
    view_count: number;
    feedback_score: number;
    indexed_at: string;
  }>;
  total_results: number;
}

function TabPanel({ children, value, index }: { children: React.ReactNode; value: number; index: number }) {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function AdminDashboard() {
  const [tabValue, setTabValue] = useState(0);
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncDialogOpen, setSyncDialogOpen] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<ContentSearchResult | null>(null);
  const [searching, setSearching] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/admin/dashboard/stats`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setDashboardStats(data);
      setError(null);
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      setError(error instanceof Error ? error.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async (force: boolean = false) => {
    try {
      setSyncing(true);
      const response = await fetch(`${API_BASE_URL}/admin/content/sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ force }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      setSyncResult(result);
      
      if (result.status === 'completed') {
        setSnackbarMessage(`Sync completed! ${result.pages_scraped || 0} pages scraped`);
        setSnackbarOpen(true);
        await fetchDashboardStats(); // Refresh stats
      }
    } catch (error) {
      console.error('Error triggering sync:', error);
      setError(error instanceof Error ? error.message : 'Sync failed');
    } finally {
      setSyncing(false);
      setSyncDialogOpen(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    
    try {
      setSearching(true);
      const response = await fetch(
        `${API_BASE_URL}/admin/content/search?query=${encodeURIComponent(searchQuery)}&limit=20`
      );
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setSearchResults(data);
    } catch (error) {
      console.error('Error searching content:', error);
      setError(error instanceof Error ? error.message : 'Search failed');
    } finally {
      setSearching(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'running':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
        <Typography variant="h6" sx={{ ml: 2 }}>
          Loading dashboard...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error" action={
          <Button color="inherit" size="small" onClick={fetchDashboardStats}>
            Retry
          </Button>
        }>
          Error loading dashboard: {error}
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        ISRO HelpBot Admin Dashboard
      </Typography>

      <Tabs value={tabValue} onChange={handleTabChange} sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tab label="Overview" />
        <Tab label="Content Management" />
        <Tab label="Sync Management" />
        <Tab label="Analytics" />
      </Tabs>

      {/* Overview Tab */}
      <TabPanel value={tabValue} index={0}>
        <Box display="grid" gridTemplateColumns="repeat(auto-fit, minmax(250px, 1fr))" gap={3}>
          {/* System Status */}
          <Box>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  System Status
                </Typography>
                <Typography variant="h5" component="div">
                  {dashboardStats?.system_status.database_connected ? 'Healthy' : 'Degraded'}
                </Typography>
                <Chip
                  label={dashboardStats?.system_status.database_connected ? 'DB Connected' : 'DB Disconnected'}
                  color={dashboardStats?.system_status.database_connected ? 'success' : 'error'}
                  size="small"
                />
              </CardContent>
            </Card>
          </Box>

          {/* Total Content */}
          <Box>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Content
                </Typography>
                <Typography variant="h5" component="div">
                  {dashboardStats?.content_stats.total_content || 0}
                </Typography>
                <Typography variant="body2">
                  {dashboardStats?.content_stats.recent_content || 0} added this week
                </Typography>
              </CardContent>
            </Card>
          </Box>

          {/* Total Views */}
          <Box>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Views
                </Typography>
                <Typography variant="h5" component="div">
                  {dashboardStats?.content_stats.total_views || 0}
                </Typography>
                <Typography variant="body2">
                  Avg Rating: {(dashboardStats?.content_stats.average_feedback || 0).toFixed(1)}/5
                </Typography>
              </CardContent>
            </Card>
          </Box>

          {/* Quick Actions */}
          <Box>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Quick Actions
                </Typography>
                <Box display="flex" flexDirection="column" gap={1}>
                  <Button
                    variant="outlined"
                    startIcon={<RefreshIcon />}
                    onClick={fetchDashboardStats}
                    size="small"
                  >
                    Refresh
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<SyncIcon />}
                    onClick={() => setSyncDialogOpen(true)}
                    size="small"
                  >
                    Sync Content
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Box>
        </Box>

        <Box display="grid" gridTemplateColumns="repeat(auto-fit, minmax(350px, 1fr))" gap={3} mt={3}>
          {/* Content by Type */}
          <Box>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Content by Type
              </Typography>
              <Box>
                {Object.entries(dashboardStats?.content_stats.content_by_type || {}).map(([type, count]) => (
                  <Box key={type} display="flex" justifyContent="space-between" mb={1}>
                    <Typography>{type}</Typography>
                    <Chip label={count} size="small" />
                  </Box>
                ))}
              </Box>
            </Paper>
          </Box>

          {/* Recent Sync History */}
          <Box>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Recent Sync History
              </Typography>
              <Box>
                {dashboardStats?.sync_history.slice(0, 5).map((sync) => (
                  <Box key={sync.sync_id} display="flex" justifyContent="space-between" mb={1}>
                    <Typography variant="body2">
                      {formatDate(sync.started_at)}
                    </Typography>
                    <Chip
                      label={sync.status}
                      color={getStatusColor(sync.status)}
                      size="small"
                    />
                  </Box>
                ))}
              </Box>
            </Paper>
          </Box>
        </Box>
      </TabPanel>

      {/* Content Management Tab */}
      <TabPanel value={tabValue} index={1}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Content Search
          </Typography>
          
          <Box display="flex" gap={2} mb={3}>
            <TextField
              fullWidth
              label="Search content..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <Button
              variant="contained"
              startIcon={<SearchIcon />}
              onClick={handleSearch}
              disabled={searching}
            >
              {searching ? <CircularProgress size={20} /> : 'Search'}
            </Button>
          </Box>

          {searchResults && (
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Title</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Views</TableCell>
                    <TableCell>Rating</TableCell>
                    <TableCell>Indexed</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {searchResults.results.map((content) => (
                    <TableRow key={content.id}>
                      <TableCell>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                          {content.title}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip label={content.content_type} size="small" />
                      </TableCell>
                      <TableCell>{content.view_count}</TableCell>
                      <TableCell>{content.feedback_score.toFixed(1)}</TableCell>
                      <TableCell>{formatDate(content.indexed_at)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      </TabPanel>

      {/* Sync Management Tab */}
      <TabPanel value={tabValue} index={2}>
        <Paper sx={{ p: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
            <Typography variant="h6">
              Synchronization Management
            </Typography>
            <Button
              variant="contained"
              startIcon={<SyncIcon />}
              onClick={() => setSyncDialogOpen(true)}
              disabled={syncing}
            >
              {syncing ? <CircularProgress size={20} /> : 'Start Sync'}
            </Button>
          </Box>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Sync ID</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Started</TableCell>
                  <TableCell>Duration</TableCell>
                  <TableCell>Pages Scraped</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {dashboardStats?.sync_history.map((sync) => (
                  <TableRow key={sync.sync_id}>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {sync.sync_id.substring(0, 8)}...
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={sync.status}
                        color={getStatusColor(sync.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{formatDate(sync.started_at)}</TableCell>
                    <TableCell>
                      {sync.duration_seconds ? `${sync.duration_seconds.toFixed(1)}s` : '-'}
                    </TableCell>
                    <TableCell>{sync.pages_scraped || '-'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      </TabPanel>

      {/* Analytics Tab */}
      <TabPanel value={tabValue} index={3}>
        <Box display="grid" gridTemplateColumns="repeat(auto-fit, minmax(400px, 1fr))" gap={3}>
          <Box>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Most Viewed Content
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Title</TableCell>
                      <TableCell>Views</TableCell>
                      <TableCell>Type</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {dashboardStats?.analytics.most_viewed?.map((content) => (
                      <TableRow key={content.content_id}>
                        <TableCell>
                          <Typography variant="body2" noWrap sx={{ maxWidth: 150 }}>
                            {content.title}
                          </Typography>
                        </TableCell>
                        <TableCell>{content.view_count}</TableCell>
                        <TableCell>
                          <Chip label={content.content_type} size="small" />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Box>

          <Box>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Activity by Type
              </Typography>
              <Box>
                {Object.entries(dashboardStats?.analytics.activity_by_type || {}).map(([type, count]) => (
                  <Box key={type} display="flex" justifyContent="space-between" mb={1}>
                    <Typography>{type}</Typography>
                    <Chip label={count} size="small" />
                  </Box>
                ))}
              </Box>
            </Paper>
          </Box>
        </Box>
      </TabPanel>

      {/* Sync Dialog */}
      <Dialog open={syncDialogOpen} onClose={() => setSyncDialogOpen(false)}>
        <DialogTitle>Start Content Synchronization</DialogTitle>
        <DialogContent>
          <Typography>
            This will scrape content from the MOSDAC website and update the database.
            This process may take several minutes.
          </Typography>
          {syncing && (
            <Box mt={2}>
              <LinearProgress />
              <Typography variant="body2" mt={1}>
                Synchronizing content...
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSyncDialogOpen(false)} disabled={syncing}>
            Cancel
          </Button>
          <Button onClick={() => handleSync(true)} disabled={syncing} variant="contained">
            Force Sync
          </Button>
          <Button onClick={() => handleSync(false)} disabled={syncing} variant="contained">
            Sync if Needed
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={() => setSnackbarOpen(false)}
        message={snackbarMessage}
      />
    </Box>
  );
}