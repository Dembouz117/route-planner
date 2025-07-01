import axios from 'axios'
import { UploadData, LocationPoint, OptimizedRoute, TaskStatus } from '../store/useSupplyChainStore'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api/v1",
  timeout: 30000
})

export class SupplyChainAPI {
  // Health check
  static async healthCheck() {
    const response = await api.get('/')
    return response.data
  }

  // Upload data and start processing
static async uploadData(data: UploadData, scenarioEnabled: boolean = false) {
  const response = await api.post(`/data/upload?enable_scenario=${scenarioEnabled}`, data)
  return response.data
}
  // Get task status
  static async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await api.get(`/agents/status/${taskId}`)
    return response.data
  }

  // Get all locations
  static async getLocations(): Promise<Record<string, LocationPoint[]>> {
   console.log(api); 
   const response = await api.get('/locations')
    return response.data
  }

  // Get all routes
  static async getRoutes(): Promise<{ routes: OptimizedRoute[], total: number }> {
    const response = await api.get('/routes')
    return response.data
  }

  // Get specific route
  static async getRoute(routeId: string): Promise<OptimizedRoute> {
    const response = await api.get(`/routes/${routeId}`)
    return response.data
  }

  // Approve route
  static async approveRoute(routeId: string) {
    const response = await api.post(`/routes/${routeId}/approve`)
    return response.data
  }

  // Test endpoints
  static async testInfoAgent(query: string = 'supply chain APAC', region: string = 'APAC') {
    const response = await api.post(`/agents/test/info?query=${encodeURIComponent(query)}&region=${region}`)
    return response.data
  }

  static async testRouteAgent() {
    const response = await api.post('/agents/test/route')
    return response.data
  }

  // Get workflow definitions
  static async getInfoWorkflow() {
    const response = await api.get('/agents/workflows/info')
    return response.data
  }

  static async getRouteWorkflow() {
    const response = await api.get('/agents/workflows/route')
    return response.data
  }
}
