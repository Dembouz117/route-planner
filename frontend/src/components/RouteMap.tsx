// src/components/RouteMap.tsx
import React, { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet'
import { Paper, Typography, Box, Chip, Alert } from '@mui/material'
import { Map as MapIcon } from '@mui/icons-material'
import L from 'leaflet'
import { useSupplyChainStore, LocationPoint, OptimizedRoute } from '../store/useSupplyChainStore'
import { SupplyChainAPI } from '../services/api'

// Fix for default markers in react-leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
})

// Custom icons for different location types
const createCustomIcon = (color: string, type: string) => {
  return L.divIcon({
    html: `
      <div style="
        background-color: ${color};
        width: 20px;
        height: 20px;
        border-radius: 50%;
        border: 2px solid white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        color: white;
        font-weight: bold;
      ">
        ${type === 'warehouse' ? '🏭' : type === 'port' ? '🚢' : '✈️'}
      </div>
    `,
    className: 'custom-marker',
    iconSize: [20, 20],
    iconAnchor: [10, 10]
  })
}

const warehouseIcon = createCustomIcon('#3498db', 'warehouse')
const portIcon = createCustomIcon('#e74c3c', 'port')
const airportIcon = createCustomIcon('#f39c12', 'airport')

interface RouteMapProps {
  selectedRoute: OptimizedRoute | null
}

export const RouteMap: React.FC<RouteMapProps> = ({ selectedRoute }) => {
  const { locations, setLocations } = useSupplyChainStore()
  const [mapError, setMapError] = useState<string | null>(null)

  useEffect(() => {
    const loadLocations = async () => {
      try {
        const locationsData = await SupplyChainAPI.getLocations()
        setLocations(locationsData)
      } catch (error) {
        console.error('Failed to load locations:', error)
        setMapError('Failed to load location data')
      }
    }

    if (Object.keys(locations).length === 0) {
      loadLocations()
    }
  }, [locations, setLocations])

  const getAllLocations = (): LocationPoint[] => {
    const allLocs: LocationPoint[] = []
    Object.values(locations).forEach(locationArray => {
      allLocs.push(...locationArray)
    })
    return allLocs
  }

  const getIcon = (locationType: string) => {
    switch (locationType) {
      case 'warehouse': return warehouseIcon
      case 'port': return portIcon
      case 'airport': return airportIcon
      default: return warehouseIcon
    }
  }

  const getRouteColor = (transportMode: string) => {
    switch (transportMode) {
      case 'air': return '#f39c12'
      case 'sea': return '#3498db'
      case 'land': return '#27ae60'
      default: return '#9b59b6'
    }
  }

  const generateRouteCoordinates = (route: OptimizedRoute): [number, number][] => {
    return route.points
      .sort((a, b) => a.order - b.order)
      .map(point => [point.location.lat, point.location.lng])
  }

  const allLocations = getAllLocations()
  
  // Default center (Singapore)
  const mapCenter: [number, number] = [1.3521, 103.8198]
  const mapZoom = 3

  if (mapError) {
    return (
      <Paper elevation={3} sx={{ p: 3 }}>
        <Alert severity="error">{mapError}</Alert>
      </Paper>
    )
  }

  return (
    <Paper elevation={3} sx={{ p: 3, height: '100%' }}>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <MapIcon />
        Supply Chain Route Map
      </Typography>

      {/* Legend */}
      <Box sx={{ mb: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        <Chip 
          label="🏭 Warehouses" 
          size="small" 
          sx={{ bgcolor: '#3498db', color: 'white' }}
        />
        <Chip 
          label="🚢 Ports" 
          size="small" 
          sx={{ bgcolor: '#e74c3c', color: 'white' }}
        />
        <Chip 
          label="✈️ Airports" 
          size="small" 
          sx={{ bgcolor: '#f39c12', color: 'white' }}
        />
        {selectedRoute && (
          <Chip 
            label={`${selectedRoute.transport_mode.toUpperCase()} Route`}
            color="primary"
            size="small"
          />
        )}
      </Box>

      {/* Map Container */}
      <Box sx={{ height: 500, borderRadius: 2, overflow: 'hidden' }}>
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://tile.openstreetmap.de/{z}/{x}/{y}.png"
          />

          {/* Location Markers */}
          {allLocations.map((location) => (
            <Marker
              key={location.id}
              position={[location.lat, location.lng]}
              icon={getIcon(location.type)}
            >
              <Popup>
                <Box>
                  <Typography variant="subtitle2" fontWeight="bold">
                    {location.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Type: {location.type}
                  </Typography>
                  {location.capacity && (
                    <Typography variant="body2" color="text.secondary">
                      Capacity: {location.capacity.toLocaleString()} units
                    </Typography>
                  )}
                  <Typography variant="body2" color="text.secondary">
                    Status: {location.status}
                  </Typography>
                </Box>
              </Popup>
            </Marker>
          ))}

          {/* Selected Route Polyline */}
          {selectedRoute && (
            <Polyline
              positions={generateRouteCoordinates(selectedRoute)}
              color={getRouteColor(selectedRoute.transport_mode)}
              weight={4}
              opacity={0.8}
              dashArray={selectedRoute.transport_mode === 'air' ? '10, 10' : undefined}
            />
          )}
        </MapContainer>
      </Box>

      {/* Selected Route Info */}
      {selectedRoute && (
        <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            Selected Route Details:
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Chip 
              label={`${selectedRoute.transport_mode.toUpperCase()}`}
              color="primary"
              size="small"
            />
            <Chip 
              label={`$${selectedRoute.total_cost}`}
              variant="outlined"
              size="small"
            />
            <Chip 
              label={`${selectedRoute.total_distance}km`}
              variant="outlined"
              size="small"
            />
            <Chip 
              label={`Risk: ${(selectedRoute.risk_score * 100).toFixed(0)}%`}
              color={selectedRoute.risk_score > 0.6 ? 'error' : selectedRoute.risk_score > 0.3 ? 'warning' : 'success'}
              size="small"
            />
            <Chip 
              label={selectedRoute.estimated_duration}
              variant="outlined"
              size="small"
            />
          </Box>

          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Route: {selectedRoute.points
              .sort((a, b) => a.order - b.order)
              .map(p => p.location.name)
              .join(' → ')
            }
          </Typography>
        </Box>
      )}

      {!selectedRoute && allLocations.length > 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2, textAlign: 'center' }}>
          Select a route from the sidebar to view it on the map
        </Typography>
      )}
    </Paper>
  )
}