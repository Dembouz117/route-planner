// src/components/ProcessingStatus.tsx
import React, { useEffect } from 'react'
import {
  Paper,
  Typography,
  Box,
  LinearProgress,
  Chip,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Collapse
} from '@mui/material'
import {
  Info,
  CheckCircle,
  Error,
  Schedule,
  Psychology,
  Route,
  Assessment,
  TrendingUp
} from '@mui/icons-material'

import { useSupplyChainStore, TaskStatus } from '../store/useSupplyChainStore'
import { SupplyChainAPI } from '../services/api'

interface ProcessingStatusProps {
  taskId: string | null
  onComplete: (routes: any[]) => void
}

export const ProcessingStatus: React.FC<ProcessingStatusProps> = ({ taskId, onComplete }) => {
  const { currentTask, setCurrentTask, updateTaskStatus } = useSupplyChainStore()

  useEffect(() => {
    if (!taskId) return

    const pollStatus = async () => {
      try {
        const status = await SupplyChainAPI.getTaskStatus(taskId)
        setCurrentTask(status)
        console.log('Polling status:', status)
        if (status.status === 'completed' && status.result) {
          console.log('Task completed:', status)
          const finalRoutes = status.result.route_optimization.optimized_routes
          onComplete(finalRoutes)
        }
      } catch (error) {
        console.error('Error polling status:', error)
        updateTaskStatus(taskId, { 
          status: 'failed', 
          error: 'Failed to get status updates' 
        })
      }
    }

    // Poll every 2 seconds while processing
    const interval = setInterval(pollStatus, 2000)
    if (currentTask?.status === 'completed' || currentTask?.status === 'failed') {
      clearInterval(interval)
    }
    
    // Initial poll
    pollStatus()

    return () => clearInterval(interval)
  }, [taskId])

  if (!currentTask && !taskId) {
    return (
      <Paper elevation={3} sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Info />
          Processing Status
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
          No active tasks
        </Typography>
      </Paper>
    )
  }

  if (!currentTask) {
    return (
      <Paper elevation={3} sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Loading task status...
        </Typography>
        <LinearProgress />
      </Paper>
    )
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success'
      case 'failed': return 'error'
      case 'processing': return 'warning'
      default: return 'default'
    }
  }

  const getStepIcon = (step: string) => {
    if (step.includes('info_agent')) return <Psychology />
    if (step.includes('route_agent')) return <Route />
    if (step.includes('analysis')) return <Assessment />
    if (step.includes('optimization')) return <TrendingUp />
    return <Schedule />
  }

  const getStepDescription = (step: string) => {
    const stepMap: Record<string, string> = {
      'information_analysis': 'Starting Information Agent...',
      'info_agent_knowledge_search_complete': 'Searching domain knowledge',
      'info_agent_disruption_search_complete': 'Analyzing supply chain disruptions',
      'info_agent_analysis_complete': 'Synthesizing risk assessment',
      'route_optimization': 'Starting Route Planning Agent...',
      'route_agent_routes_generated': 'Generating candidate routes',
      'route_agent_costs_analyzed': 'Analyzing route costs',
      'route_agent_risks_assessed': 'Assessing route risks',
      'route_agent_optimization_complete': 'Optimizing route selection'
    }
    
    return stepMap[step] || step.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  return (
    <Paper elevation={3} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Info />
        Processing Status
      </Typography>

      {/* Status Chip */}
      <Box sx={{ mb: 2 }}>
        <Chip
          label={currentTask.status.toUpperCase()}
          color={getStatusColor(currentTask.status) as any}
          variant="filled"
          icon={
            currentTask.status.includes('complete') ? <CheckCircle /> :
            currentTask.status.includes('fail') ? <Error /> :
            <Schedule />
          }
        />
      </Box>

      {/* Progress Bar */}
      {currentTask.status === 'processing' && (
        <Box sx={{ mb: 2 }}>
          <LinearProgress variant="indeterminate" sx={{ height: 8, borderRadius: 4 }} />
        </Box>
      )}

      {/* Current Step */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          Current Step:
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {getStepIcon(currentTask.current_step)}
          <Typography variant="body2">
            {getStepDescription(currentTask.current_step)}
          </Typography>
        </Box>
      </Box>

      {/* Error Display */}
      {currentTask.status === 'failed' && currentTask.error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {currentTask.error}
        </Alert>
      )}

      {/* Information Analysis Results */}
      <Collapse in={!!currentTask.info_analysis}>
        <Box sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            🧠 Information Agent Results:
          </Typography>
          
          {currentTask.info_analysis && (
            <List dense>
              <ListItem sx={{ py: 0.5 }}>
                <ListItemIcon sx={{ minWidth: 30 }}>
                  📚
                </ListItemIcon>
                <ListItemText 
                  primary={`${currentTask.info_analysis.domain_knowledge?.length || 0} domain knowledge entries`}
                  primaryTypographyProps={{ variant: 'body2' }}
                />
              </ListItem>
              
              <ListItem sx={{ py: 0.5 }}>
                <ListItemIcon sx={{ minWidth: 30 }}>
                  ⚠️
                </ListItemIcon>
                <ListItemText 
                  primary={`${currentTask.info_analysis.disruption_data?.length || 0} disruption alerts`}
                  primaryTypographyProps={{ variant: 'body2' }}
                />
              </ListItem>
              
              {currentTask.info_analysis.risk_assessment && (
                <ListItem sx={{ py: 0.5 }}>
                  <ListItemIcon sx={{ minWidth: 30 }}>
                    🎯
                  </ListItemIcon>
                  <ListItemText 
                    primary={`Risk Level: ${currentTask.info_analysis.risk_assessment.overall_risk || 'Unknown'}`}
                    primaryTypographyProps={{ variant: 'body2' }}
                  />
                </ListItem>
              )}
            </List>
          )}
        </Box>
      </Collapse>

      {/* Completion Summary */}
      {currentTask.routes && (
        <Alert severity="success" sx={{ mb: 2 }}>
          <Typography variant="body2">
            ✅ Processing completed! Generated {currentTask.routes.length} optimized routes.
          </Typography>
        </Alert>
      )}

      {/* Task Timing */}
      {currentTask.completed_at && (
        <Typography variant="caption" color="text.secondary">
          Completed at: {new Date(currentTask.completed_at).toLocaleString()}
        </Typography>
      )}
    </Paper>
  )
}