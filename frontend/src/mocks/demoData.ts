import { DeviceForecast } from '../store/useSupplyChainStore';

export const demoData: DeviceForecast[] = [
      {
        model: 'Dell Latitude 7440',
        quantity: 5000,
        destination: 'Singapore',
        priority: 'high',
        delivery_window: '2025-07-01 to 2025-07-31'
      },
      {
        model: 'Dell OptiPlex 7010',
        quantity: 3000,
        destination: 'Tokyo',
        priority: 'medium',
        delivery_window: '2025-08-01 to 2025-08-31'
      }
    ]
    