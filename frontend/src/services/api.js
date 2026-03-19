import axios from 'axios'

const api = axios.create({
    baseURL: 'http://localhost:8000',
    timeout: 30000,
})

export const getDashboardStats = () => api.get('/analytics/dashboard-stats')
export const getFeatureImportance = () => api.get('/analytics/feature-importance')
export const getChurnTrend = () => api.get('/analytics/churn-trend')
export const getCustomers = (params) => api.get('/customers', { params })
export const getCustomer = (id) => api.get(`/customers/${id}`)
export const predictCustomer = (id) => api.post(`/predictions/${id}`)
export const runBulkPredictions = () => api.post('/predictions/bulk/run')
export const getPredictionHistory = (id) => api.get(`/predictions/${id}/history`)
export const getCohortAnalysis = () => api.get('/analytics/cohort-analysis')
