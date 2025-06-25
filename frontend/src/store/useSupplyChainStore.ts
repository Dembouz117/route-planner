// src/store/useSupplyChainStore.ts
import { create } from 'zustand'

export interface LocationPoint {
  id: string
  name: string
  lat: number
  lng: number
  type: 'warehouse' | 'port' | 'airport'
  capacity?: number
  status: string
}

export interface DeviceForecast {
  model: string
  quantity: number
  destination: string
  priority: string
  delivery_window: string
}

export interface UploadData {
  region: string
  forecast_date: string
  device_forecasts: DeviceForecast[]
  constraints: Record<string, any>
}

export interface RoutePoint {
  location: LocationPoint
  order: number
  estimated_arrival?: string
}

export interface OptimizedRoute {
  id: string
  points: RoutePoint[]
  total_cost: number
  total_distance: number
  risk_score: number
  transport_mode: string
  estimated_duration: string
  optimization_rank?: number
  recommended?: boolean
}

export interface TaskStatus {
  id: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  current_step: string
  info_analysis?: any
  routes?: OptimizedRoute[]
  error?: string
  completed_at?: string
}

interface SupplyChainState {
  // Data
  locations: Record<string, LocationPoint[]>
  routes: OptimizedRoute[]
  currentTask: TaskStatus | null
  selectedRoute: OptimizedRoute | null
  uploadData: UploadData | null
  
  // UI State
  isUploading: boolean
  isProcessing: boolean
  
  // Actions
  setLocations: (locations: Record<string, LocationPoint[]>) => void
  setRoutes: (routes: OptimizedRoute[]) => void
  setCurrentTask: (task: TaskStatus | null) => void
  setSelectedRoute: (route: OptimizedRoute | null) => void
  setUploadData: (data: UploadData | null) => void
  setIsUploading: (uploading: boolean) => void
  setIsProcessing: (processing: boolean) => void
  updateTaskStatus: (taskId: string, status: Partial<TaskStatus>) => void
}

export const useSupplyChainStore = create<SupplyChainState>((set, get) => ({
  // Initial state
  locations: {},
  routes: [],
  currentTask: null,
  selectedRoute: null,
  uploadData: null,
  isUploading: false,
  isProcessing: false,
  
  // Actions
  setLocations: (locations) => set({ locations }),
  setRoutes: (routes) => set({ routes }),
  setCurrentTask: (currentTask) => set({ currentTask }),
  setSelectedRoute: (selectedRoute) => set({ selectedRoute }),
  setUploadData: (uploadData) => set({ uploadData }),
  setIsUploading: (isUploading) => set({ isUploading }),
  setIsProcessing: (isProcessing) => set({ isProcessing }),
  
  updateTaskStatus: (taskId, status) => {
    const currentTask = get().currentTask
    if (currentTask && currentTask.id === taskId) {
      set({ currentTask: { ...currentTask, ...status } })
    }
  }
}))