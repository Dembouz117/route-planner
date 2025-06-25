// src/components/RoutesList.tsx
import React from 'react'
import {
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  Button,
  Divider,
  Tooltip
} from '@mui/material'
import {
  Route,
  AttachMoney,
  Speed,
  Warning,
  CheckCircle,
  Flight,
  DirectionsBoat,
  DirectionsCar,
  Star,
  Schedule
} from '@mui/icons-material'
import { useSupplyChainStore, OptimizedRoute } from '../store/useSupplyChainStore'
import { SupplyChainAPI } from '../services/api'

interface RoutesListProps {
  routes: OptimizedRoute[]
  onRouteSelect: (route: OptimizedRoute) => void
}

export const RoutesList: React.FC<RoutesListProps> = ({ routes, onRouteSelect }) => {
  const { selectedRoute, setSelectedRoute } = useSupplyChainStore()

  const getTransportIcon = (mode: string) => {
    switch (mode) {
      case 'air': return <Flight />
      case 'sea': return <DirectionsBoat />
      case 'land': return <DirectionsCar />
      default: return <Route />
    }
  }

  const getRiskColor = (score: number) => {
    if (score <= 0.3) return 'success'
    if (score <= 0.6) return 'warning'
    return 'error'
  }

  const handleRouteSelect = (route: OptimizedRoute) => {
    setSelectedRoute(route)
    onRouteSelect(route)
  }

  const handleApproveRoute = async (routeId: string, event: React.MouseEvent) => {
    event.stopPropagation()
    try {
      await SupplyChainAPI.approveRoute(routeId)
      console.log(`Route ${routeId} approved`)
    } catch (error) {
      console.error('Failed to approve route:', error)
    }
  }

  if (!routes.length) {
    return (
      <Paper elevation={3} sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Route />
          Generated Routes
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
          No routes generated yet
        </Typography>
      </Paper>
    )
  }

  return (
    <Paper elevation={3} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Route />
        Generated Routes ({routes.length})
      </Typography>

      <Box sx={{ maxHeight: 600, overflowY: 'auto' }}>
        {routes.map((route, index) => (
          <Card
            key={route.id}
            onClick={() => handleRouteSelect(route)}
            sx={{
              mb: 2,
              cursor: 'pointer',
              border: selectedRoute?.id === route.id ? 2 : 1,
              borderColor: selectedRoute?.id === route.id ? 'primary.main' : 'grey.300',
              bgcolor: selectedRoute?.id === route.id ? 'primary.50' : 'white',
              transition: 'all 0.3s ease',
              '&:hover': {
                bgcolor: selectedRoute?.id === route.id ? 'primary.100' : 'grey.50',
                transform: 'translateY(-2px)'
              }
            }}
          >
            <CardContent>
              {/* Route Header */}
              <Box sx={{ display: 'flex', justifyContent: 'between', alignItems: 'center', mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {getTransportIcon(route.transport_mode)}
                  <Typography variant="subtitle1" fontWeight="bold">
                    Route #{index + 1}
                  </Typography>
                  {route.recommended && (
                    <Chip
                      label="Recommended"
                      color="primary"
                      size="small"
                      icon={<Star />}
                    />
                  )}
                </Box>
                
                <Chip
                  label={route.transport_mode.toUpperCase()}
                  variant="outlined"
                  size="small"
                />
              </Box>

              {/* Route Metrics */}
              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <AttachMoney color="primary" />
                    <Typography variant="h6" color="primary">
                      ${route.total_cost}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Total Cost
                    </Typography>
                  </Box>
                </Grid>
                
                <Grid item xs={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Speed color="info" />
                    <Typography variant="h6" color="info.main">
                      {route.total_distance}km
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Distance
                    </Typography>
                  </Box>
                </Grid>
                
                <Grid item xs={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Warning color={getRiskColor(route.risk_score) as any} />
                    <Typography variant="h6" color={`${getRiskColor(route.risk_score)}.main`}>
                      {(route.risk_score * 100).toFixed(0)}%
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Risk Score
                    </Typography>
                  </Box>
                </Grid>
                
                <Grid item xs={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Schedule />
                    <Typography variant="h6">
                      {route.estimated_duration}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Duration
                    </Typography>
                  </Box>
                </Grid>
              </Grid>

              {/* Route Points */}
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Route Points:
                </Typography>
                {route.points.map((point, idx) => (
                  <Typography key={idx} variant="body2" color="text.secondary">
                    {point.order}. {point.location.name} ({point.location.type})
                  </Typography>
                ))}
              </Box>

              <Divider sx={{ my: 1 }} />

              {/* Actions */}
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={() => handleRouteSelect(route)}
                >
                  View on Map
                </Button>
                
                <Button
                  size="small"
                  variant="contained"
                  color="success"
                  startIcon={<CheckCircle />}
                  onClick={(e) => handleApproveRoute(route.id, e)}
                >
                  Approve
                </Button>
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>
    </Paper>
  )
}