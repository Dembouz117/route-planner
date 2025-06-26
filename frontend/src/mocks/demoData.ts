import { DeviceForecast } from '../store/useSupplyChainStore';

export const demoData: DeviceForecast[] = [
  {
    model: 'Dell Latitude 7440',
    quantity: 2000,
    destination: 'Tel Aviv',  // This will trigger the airport scenario
    priority: 'high',
    delivery_window: '2025-07-01 to 2025-07-31'
  },
  {
    model: 'Dell OptiPlex 7010',
    quantity: 1500,
    destination: 'Singapore',
    priority: 'medium',
    delivery_window: '2025-08-01 to 2025-08-31'
  },
  {
    model: 'Dell Inspiron 15',
    quantity: 800,
    destination: 'Tokyo',
    priority: 'low',
    delivery_window: '2025-09-01 to 2025-09-30'
  }
];