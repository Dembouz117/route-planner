// src/components/DataUpload.tsx
import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  Paper,
  Typography,
  Box,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress
} from '@mui/material'
import { CloudUpload, SmartToy } from '@mui/icons-material'
import { useSupplyChainStore, DeviceForecast, UploadData } from '../store/useSupplyChainStore'
import { SupplyChainAPI } from '../services/api'
import { demoData } from '../mocks/demoData'

interface DataUploadProps {
  onUploadComplete: (taskId: string) => void
}

export const DataUpload: React.FC<DataUploadProps> = ({ onUploadComplete }) => {
  const { setUploadData, setIsUploading, isUploading } = useSupplyChainStore()
  
  const [region, setRegion] = useState('APAC')
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [parsedData, setParsedData] = useState<DeviceForecast[] | null>(null)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (file) {
      setUploadedFile(file)
      setError(null)
      
      // Parse CSV/JSON file
      const reader = new FileReader()
      reader.onload = (e) => {
        try {
          const content = e.target?.result as string
          
          if (file.name.endsWith('.json')) {
            const jsonData = JSON.parse(content)
            setParsedData(jsonData.device_forecasts || [])
          } else if (file.name.endsWith('.csv')) {
            // Simple CSV parsing for demo
            const lines = content.split('\n').filter(line => line.trim())
            const headers = lines[0].split(',').map(h => h.trim())
            
            const forecasts: DeviceForecast[] = lines.slice(1).map(line => {
              const values = line.split(',').map(v => v.trim())
              return {
                model: values[0] || 'Unknown Model',
                quantity: parseInt(values[1]) || 1000,
                destination: values[2] || 'Singapore',
                priority: values[3] || 'medium',
                delivery_window: values[4] || '2025-07-01 to 2025-07-31'
              }
            })
            
            setParsedData(forecasts)
          }
        } catch (err) {
          setError('Failed to parse file. Please check the format.')
        }
      }
      
      reader.readAsText(file)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/json': ['.json']
    },
    maxFiles: 1
  })

  const handleProcess = async () => {
    if (!parsedData?.length) {
      setError('Please upload a valid file first')
      return
    }

    setIsUploading(true)
    setError(null)

    try {
      const uploadData: UploadData = {
        region,
        forecast_date: '2025-Q2',
        device_forecasts: parsedData,
        constraints: {
          max_cost_per_unit: 50,
          preferred_transport: ['air', 'sea']
        }
      }

      setUploadData(uploadData)
      const response = await SupplyChainAPI.uploadData(uploadData)
      
      if (response.task_id) {
        onUploadComplete(response.task_id)
      } else {
        setError('Failed to start processing')
      }
    } catch (err) {
      setError('Failed to upload data. Please try again.')
      console.error('Upload error:', err)
    } finally {
      setIsUploading(false)
    }
  }

  const handleUseDemo = () => {

    setParsedData(demoData)
    setUploadedFile(null)
  }

  return (
    <Paper elevation={3} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <CloudUpload />
        Data Upload
      </Typography>

      {/* File Upload Area */}
      <Box
        {...getRootProps()}
        sx={{
          border: 2,
          borderStyle: 'dashed',
          borderColor: isDragActive ? 'primary.main' : 'grey.400',
          borderRadius: 2,
          p: 4,
          textAlign: 'center',
          cursor: 'pointer',
          bgcolor: isDragActive ? 'action.hover' : 'grey.50',
          mb: 2,
          transition: 'all 0.3s ease'
        }}
      >
        <input {...getInputProps()} />
        <CloudUpload sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
        
        {uploadedFile ? (
          <Typography variant="body1" color="primary">
            📄 {uploadedFile.name}
          </Typography>
        ) : (
          <>
            <Typography variant="body1" fontWeight="bold">
              Drop CSV/JSON file here or click to browse
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Supported formats: .csv, .json
            </Typography>
          </>
        )}
      </Box>

      <Box sx={{ mb: 2 }}>
        <Button 
          variant="outlined" 
          size="small" 
          onClick={handleUseDemo}
          disabled={isUploading}
        >
          Use Demo Data
        </Button>
      </Box>

      {/* Region Selection */}
      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel>Region</InputLabel>
        <Select
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          label="Region"
          disabled={isUploading}
        >
          <MenuItem value="APAC">Asia Pacific</MenuItem>
          <MenuItem value="EMEA">Europe, Middle East & Africa</MenuItem>
          <MenuItem value="Americas">Americas</MenuItem>
        </Select>
      </FormControl>

      {/* Parsed Data Preview */}
      {parsedData && (
        <Box sx={{ mb: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            📊 Parsed Data ({parsedData.length} forecasts)
          </Typography>
          {parsedData.slice(0, 2).map((forecast, idx) => (
            <Typography key={idx} variant="body2" color="text.secondary">
              • {forecast.model}: {forecast.quantity} units to {forecast.destination}
            </Typography>
          ))}
          {parsedData.length > 2 && (
            <Typography variant="body2" color="text.secondary">
              ... and {parsedData.length - 2} more
            </Typography>
          )}
        </Box>
      )}

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Process Button */}
      <Button
        variant="contained"
        fullWidth
        onClick={handleProcess}
        disabled={!parsedData?.length || isUploading}
        startIcon={isUploading ? <CircularProgress size={20} /> : <SmartToy />}
        sx={{ py: 1.5 }}
      >
        {isUploading ? 'Processing with AI Agents...' : 'Process with AI Agents'}
      </Button>
    </Paper>
  )
}