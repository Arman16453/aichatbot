'use client';

import React, { useState, useMemo } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Tabs,
  Tab
} from '@mui/material';
import {
  Search as SearchIcon,
  ExpandMore as ExpandMoreIcon,
  Link as LinkIcon,
  Schedule as ScheduleIcon,
  FilterList as FilterIcon
} from '@mui/icons-material';

interface SearchResult {
  id: string;
  title: string;
  content: string;
  url: string;
  content_type: string;
  indexed_at: string;
  relevance_score: number;
  word_count: number;
}

interface SearchFilters {
  content_type?: string;
  date_from?: string;
  date_to?: string;
  min_words?: number;
  max_words?: number;
}

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
      id={`search-tabpanel-${index}`}
      aria-labelledby={`search-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

export default function SearchInterface() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalResults, setTotalResults] = useState(0);
  const [tabValue, setTabValue] = useState(0);

  // Filters
  const [filters, setFilters] = useState<SearchFilters>({});
  const [showFilters, setShowFilters] = useState(false);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8001/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          filters: Object.keys(filters).length > 0 ? filters : null,
          limit: 20,
          offset: 0
        }),
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data = await response.json();
      setResults(data.results || []);
      setTotalResults(data.total || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setResults([]);
      setTotalResults(0);
    } finally {
      setLoading(false);
    }
  };

  const handleIndexContent = async () => {
    setIndexing(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8001/api/search/index', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Indexing failed: ${response.statusText}`);
      }

      const data = await response.json();
      alert(`Content indexed successfully! ${data.word_count} words processed.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Indexing failed');
    } finally {
      setIndexing(false);
    }
  };

  const handleFilterChange = (key: keyof SearchFilters, value: string | number | undefined) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const clearFilters = () => {
    setFilters({});
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <Box sx={{ width: '100%', maxWidth: 1200, mx: 'auto', p: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom align="center">
        MOSDAC Content Search
      </Typography>

      <Tabs value={tabValue} onChange={handleTabChange} aria-label="search tabs">
        <Tab label="Search Content" />
        <Tab label="Index Management" />
      </Tabs>

      <TabPanel value={tabValue} index={0}>
        {/* Search Interface */}
        <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <TextField
              fullWidth
              label="Search MOSDAC content"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Enter keywords, phrases, or questions..."
            />
            <Button
              variant="contained"
              onClick={handleSearch}
              disabled={loading || !query.trim()}
              startIcon={loading ? <CircularProgress size={20} /> : <SearchIcon />}
              sx={{ minWidth: 120 }}
            >
              {loading ? 'Searching...' : 'Search'}
            </Button>
          </Box>

          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <Button
              variant="outlined"
              onClick={() => setShowFilters(!showFilters)}
              startIcon={<FilterIcon />}
            >
              Filters {Object.keys(filters).length > 0 && `(${Object.keys(filters).length})`}
            </Button>
            {Object.keys(filters).length > 0 && (
              <Button variant="text" onClick={clearFilters} size="small">
                Clear Filters
              </Button>
            )}
          </Box>

          {/* Advanced Filters */}
          {showFilters && (
            <Accordion expanded={showFilters} onChange={() => setShowFilters(!showFilters)}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography>Advanced Filters</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                  <FormControl sx={{ minWidth: 120 }}>
                    <InputLabel>Content Type</InputLabel>
                    <Select
                      value={filters.content_type || ''}
                      label="Content Type"
                      onChange={(e) => handleFilterChange('content_type', e.target.value)}
                    >
                      <MenuItem value="">All Types</MenuItem>
                      <MenuItem value="webpage">Web Page</MenuItem>
                      <MenuItem value="document">Document</MenuItem>
                      <MenuItem value="faq">FAQ</MenuItem>
                    </Select>
                  </FormControl>

                  <TextField
                    label="From Date"
                    type="date"
                    value={filters.date_from || ''}
                    onChange={(e) => handleFilterChange('date_from', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />

                  <TextField
                    label="To Date"
                    type="date"
                    value={filters.date_to || ''}
                    onChange={(e) => handleFilterChange('date_to', e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />

                  <TextField
                    label="Min Words"
                    type="number"
                    value={filters.min_words || ''}
                    onChange={(e) => handleFilterChange('min_words', parseInt(e.target.value) || undefined)}
                  />

                  <TextField
                    label="Max Words"
                    type="number"
                    value={filters.max_words || ''}
                    onChange={(e) => handleFilterChange('max_words', parseInt(e.target.value) || undefined)}
                  />
                </Box>
              </AccordionDetails>
            </Accordion>
          )}
        </Paper>

        {/* Error Display */}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Results Summary */}
        {totalResults > 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Found {totalResults} result{totalResults !== 1 ? 's' : ''} for &quot;{query}&quot;
          </Typography>
        )}

        {/* Search Results */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {results.map((result) => (
            <Card key={result.id} elevation={2}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                  <Typography variant="h6" component="h2">
                    {result.title}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <Chip
                      label={`Score: ${result.relevance_score.toFixed(2)}`}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                    <Chip
                      label={result.content_type}
                      size="small"
                      variant="outlined"
                    />
                  </Box>
                </Box>

                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {highlightTerms(createExcerpt(result.content, query), query)}
                </Typography>

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <LinkIcon fontSize="small" />
                    <Typography variant="body2" component="a" href={result.url} target="_blank" sx={{ textDecoration: 'none', color: 'primary.main' }}>
                      {result.url}
                    </Typography>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <ScheduleIcon fontSize="small" />
                    <Typography variant="body2" color="text.secondary">
                      {formatDate(result.indexed_at)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {result.word_count} words
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>

        {results.length === 0 && !loading && query && !error && (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary">
              No results found for &quot;{query}&quot;
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Try different keywords or check if content has been indexed.
            </Typography>
          </Paper>
        )}
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        {/* Index Management */}
        <Paper elevation={3} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Content Indexing Management
          </Typography>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Index web content from MOSDAC to enable search functionality. This process scans the website and stores content for fast searching.
          </Typography>

          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <Button
              variant="contained"
              onClick={handleIndexContent}
              disabled={indexing}
              startIcon={indexing ? <CircularProgress size={20} /> : <SearchIcon />}
            >
              {indexing ? 'Indexing...' : 'Index Content'}
            </Button>

            {indexing && (
              <Typography variant="body2" color="text.secondary">
                Scanning MOSDAC website and processing content...
              </Typography>
            )}
          </Box>

          <Alert severity="info" sx={{ mt: 3 }}>
            <Typography variant="body2">
              <strong>Note:</strong> Content indexing may take a few moments depending on the website size and your internet connection.
            </Typography>
          </Alert>
        </Paper>
      </TabPanel>
    </Box>
  );
}

// Utility: strip HTML tags and normalize whitespace
function stripHtml(html: string): string {
  if (!html) return '';
  try {
    return html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  } catch (e) {
    return html;
  }
}

// Utility: escape regex special chars
function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Create a short excerpt around the first occurrence of any query term
function createExcerpt(content: string, query: string, maxLen = 300): string {
  if (!content) return '';
  const plain = stripHtml(content);
  if (!query) return plain.length > maxLen ? plain.slice(0, maxLen).trim() + '...' : plain;

  const terms = query
    .split(/\s+/)
    .map(t => t.trim())
    .filter(Boolean)
    .slice(0, 6)
    .map(escapeRegex);

  if (terms.length === 0) return plain.length > maxLen ? plain.slice(0, maxLen).trim() + '...' : plain;

  const regex = new RegExp(terms.join('|'), 'i');
  const match = plain.match(regex);
  if (!match) return plain.length > maxLen ? plain.slice(0, maxLen).trim() + '...' : plain;

  const idx = match.index || 0;
  const half = Math.floor(maxLen / 2);
  let start = Math.max(0, idx - Math.floor(half / 2));
  let end = Math.min(plain.length, start + maxLen);
  if (end - start < maxLen) {
    start = Math.max(0, end - maxLen);
  }

  let excerpt = plain.slice(start, end).trim();
  if (start > 0) excerpt = '...' + excerpt;
  if (end < plain.length) excerpt = excerpt + '...';
  return excerpt;
}

// Highlight query terms by returning an array of React nodes
function highlightTerms(text: string, query: string): React.ReactNode[] {
  if (!query) return [text];
  const terms = query
    .split(/\s+/)
    .map(t => t.trim())
    .filter(Boolean)
    .slice(0, 8)
    .map(escapeRegex);

  if (terms.length === 0) return [text];

  const re = new RegExp(`(${terms.join('|')})`, 'ig');
  const parts = text.split(re);
  return parts.map((part, i) => {
    if (re.test(part)) {
      // reset lastIndex in case test is stateful (shouldn't be for non-global)
      return (
        <mark key={i} style={{ backgroundColor: '#fff59d', padding: '0 2px' }}>
          {part}
        </mark>
      );
    }
    return <span key={i}>{part}</span>;
  });
}