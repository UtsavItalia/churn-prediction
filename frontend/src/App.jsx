import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import CustomerDetail from './pages/CustomerDetail'
import CohortAnalysis from './pages/CohortAnalysis'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/customer/:id" element={<CustomerDetail />} />
      <Route path="/cohort" element={<CohortAnalysis />} />
    </Routes>
  )
}
