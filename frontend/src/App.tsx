// src/App.tsx
import React, { useState, useEffect } from 'react'
import {
  Container,
  Grid,
  Typography,
  Box,
  AppBar,
  Toolbar,
  CssBaseline,
  ThemeProvider,
  Alert,
  Button,
  Chip
} from '@mui/material'
import { LocalShipping, Psychology, Route as RouteIcon } from '@mui/icons-material'
import { DataUpload } from './components/DataUpload'
import { ProcessingStatus } from './components/ProcessingStatus'
import { RoutesList } from './components/RoutesList'
import { RouteMap } from './components/RouteMap'
import { useSupplyChainStore } from './store/useSupplyChainStore'
import { SupplyChainAPI } from './services/api'
import { theme } from './theme'


function App() {
  const { 
    routes, 
    setRoutes, 
    selectedRoute, 
    currentTask
  } = useSupplyChainStore()

  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const [appError, setAppError] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState<boolean | null>(null)

  useEffect(() => {
    const testConnection = async () => {
      try {
        await SupplyChainAPI.healthCheck()
        setIsConnected(true)
      } catch (error) {
        console.error('Backend connection failed:', error)
        setIsConnected(false)
        setAppError('Cannot connect to backend server. Please ensure the FastAPI server is running on port 8000.')
      }
    }

    testConnection()
  }, [])

  const handleUploadComplete = (taskId: string) => {
    setCurrentTaskId(taskId)
    setAppError(null)
  }

  const handleProcessingComplete = (generatedRoutes: any[]) => {
    setRoutes(generatedRoutes)
  }

  // j mock for now
  const handleRouteSelect = (route: any) => {
    console.log('Route selected:', route.id)
  }

  const handleTestAgents = async () => {
    try {
      setAppError(null)
      
      // Test Information Agent
      console.log('Testing Information Agent...')
      const infoResult = await SupplyChainAPI.testInfoAgent()
      console.log('Info Agent Result:', infoResult)
      
      // Test Route Planning Agent
      console.log('Testing Route Planning Agent...')
      const routeResult = await SupplyChainAPI.testRouteAgent()
      console.log('Route Agent Result:', routeResult)
      
      alert('Agents tested successfully! Check console for details.')
    } catch (error) {
      console.error('Agent test failed:', error)
      setAppError('Agent testing failed. Check console for details.')
    }
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      
      {/* App Bar */}
      <AppBar position="static" elevation={0}>
        <Toolbar>
          
          <Box
            component="img"
            src="https://boss.dell.com/images/logo.png"
            alt="Logo"
            sx={{ height: 48, width: 48, mr: 2 }}
          />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            D.E.L.L. – Distributed Experts for Logistics Layer
          </Typography>
          
          {/* Connection Status */}
          <Chip
            label={isConnected === null ? 'Connecting...' : isConnected ? 'Connected' : 'Disconnected'}
            color={isConnected === null ? 'default' : isConnected ? 'success' : 'error'}
            size="small"
            sx={{ mr: 2 }}
          />
          
          {/* Test Agents Button */}
          {isConnected && (
            <Button
              color="inherit"
              variant="outlined"
              size="small"
              onClick={handleTestAgents}
              startIcon={<Psychology />}
            >
              Test Agents
            </Button>
          )}
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Container maxWidth={1200} sx={{ py: 3, width: '100vw' }}>
        {/* Connection Error */}
        {!isConnected && isConnected !== null && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {appError}
          </Alert>
        )}

        {/* App Error */}
        {appError && isConnected && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            {appError}
          </Alert>
        )}

        {/* System Status Banner */}
        {currentTask && (
          <Alert 
            severity={currentTask.status === 'completed' ? 'success' : currentTask.status === 'failed' ? 'error' : 'info'}
            sx={{ mb: 3 }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {currentTask.status === 'processing' && <Psychology sx={{ animation: 'pulse 2s infinite' }} />}
              {currentTask.status === 'completed' && <RouteIcon />}
              
              <Typography variant="body2">
                {currentTask.status === 'processing' && `Multi-Agent Processing: ${currentTask.current_step.replace(/_/g, ' ')}`}
                {currentTask.status === 'completed' && `✅ Processing Complete! Generated ${routes.length} optimized routes.`}
                {currentTask.status === 'failed' && `❌ Processing Failed: ${currentTask.error}`}
              </Typography>
            </Box>
          </Alert>
        )}

        {/* Main Grid Layout */}
        <Grid container spacing={3}>
          {/* Left Sidebar */}
          <Grid item xs={12} md={4}>
            <Grid container spacing={3}>

              <Grid item xs={12}>
                <DataUpload onUploadComplete={handleUploadComplete} />
              </Grid>

              <Grid item xs={12}>
                <ProcessingStatus 
                  taskId={currentTaskId}
                  onComplete={handleProcessingComplete}
                />
              </Grid>

              <Grid item xs={12}>
                <RoutesList 
                  routes={routes}
                  onRouteSelect={handleRouteSelect}
                />
              </Grid>
            </Grid>
          </Grid>

          <Grid item xs={12} md={8}>
            <RouteMap selectedRoute={selectedRoute} />
          </Grid>
        </Grid>

        {/* Multi-Agent Architecture Section */}
        <Box sx={{ mt: 4, p: 3, bgcolor: 'background.paper', borderRadius: 2 }}>
          <Typography variant="h6" gutterBottom>
            🤖 Multi-Agent Architecture
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Psychology color="primary" />
                <Typography variant="subtitle2">Information Agent</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                • Searches domain knowledge base (Pinecone)<br/>
                • Monitors supply chain disruptions (Tavily)<br/>
                • Synthesizes risk assessments
              </Typography>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <RouteIcon color="primary" />
                <Typography variant="subtitle2">Route Planning Agent</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                • Generates candidate routes<br/>
                • Analyzes costs and risks<br/>
                • Optimizes route recommendations
              </Typography>
            </Grid>
          </Grid>
        </Box>
      </Container>

      <style>
        {`
          @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
          }
        `}
      </style>
    </ThemeProvider>
  )
}

export default App