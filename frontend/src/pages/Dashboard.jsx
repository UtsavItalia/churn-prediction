import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getDashboardStats, getFeatureImportance,
  getChurnTrend, getCustomers, runBulkPredictions
} from '../services/api'
import StatCard from '../components/StatCard'
import FeatureImportanceChart from '../components/FeatureImportanceChart'
import ChurnTrendChart from '../components/ChurnTrendChart'
import RiskDistributionChart from '../components/RiskDistributionChart'
import CustomerTable from '../components/CustomerTable'

export default function Dashboard() {
  const navigate = useNavigate()
  const [retrainJob, setRetrainJob] = useState(null)
  const [retrainStatus, setRetrainStatus] = useState(null)
  const [stats, setStats] = useState(null)
  const [features, setFeatures] = useState([])
  const [trend, setTrend] = useState([])
  const [customers, setCustomers] = useState([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getDashboardStats(),
      getFeatureImportance(),
      getChurnTrend(),
      getCustomers({ limit: 50 }),
    ]).then(([s, f, t, c]) => {
      setStats(s.data)
      setFeatures(f.data)
      setTrend(t.data)
      setCustomers(c.data)
      setLoading(false)

      // Auto-run bulk predictions if none exist yet
      if (s.data.critical_risk_count === 0 && s.data.avg_churn_probability === 0) {
        runBulkPredictions().then(() => {
          Promise.all([
            getDashboardStats(),
            getCustomers({ limit: 50 })
          ]).then(([newStats, newCust]) => {
            setStats(newStats.data)
            setCustomers(newCust.data)
          })
        })
      }
    })
  }, [])

  const handleFilterChange = async (segment) => {
    console.log('Filter changed to:', segment)
    setFilter(segment)
    const params = segment ? { risk_segment: segment, limit: 50 } : { limit: 50 }
    const res = await getCustomers(params)
    console.log('Customers returned:', res.data.length)
    setCustomers(res.data)
  }

  if (loading) return (
    <div style={styles.loading}>
      <div style={styles.spinner} />
      <p>Loading dashboard...</p>
    </div>
  )
  const handleRetrain = async () => {
    const res = await fetch('http://localhost:8000/model/retrain', { method: 'POST' })
    const job = await res.json()
    setRetrainJob(job.job_id)
    setRetrainStatus('queued')
    // Poll every 3 seconds
    const interval = setInterval(async () => {
      const r = await fetch(`http://localhost:8000/model/retrain/status?job_id=${job.job_id}`)
      const data = await r.json()
      setRetrainStatus(data.status)
      if (data.status === 'complete' || data.status === 'failed') {
        clearInterval(interval)
      }
    }, 3000)
  }

  const handleReload = async () => {
    const job = await fetch(`http://localhost:8000/model/retrain/status?job_id=${retrainJob}`)
    const data = await job.json()
    await fetch(`http://localhost:8000/model/reload?version=${data.new_version}`, {
      method: 'POST'
    })
    setRetrainStatus('reloaded')
  }

  return (
    <div style={styles.page}>

      {/* Header */}
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>Churn Intelligence</h1>
          <p style={styles.subtitle}>
            {stats.total_customers} customers · Model accuracy 91% ROC-AUC
          </p>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <div style={styles.badge}>
            Avg risk: {(stats.avg_churn_probability * 100).toFixed(1)}%
          </div>
          <button
            onClick={() => navigate('/cohort')}
            style={styles.retrainBtn}
          >
            Cohort Analysis →
          </button>

          {/* Retrain controls */}
          {retrainStatus === 'complete' && (
            <button onClick={handleReload} style={styles.reloadBtn}>
              ✓ Retrain done — Reload Model
            </button>
          )}
          {retrainStatus === 'running' || retrainStatus === 'queued' ? (
            <button disabled style={styles.retrainBtnDisabled}>
              ⟳ Retraining...
            </button>
          ) : retrainStatus === 'reloaded' ? (
            <span style={{ color: 'var(--success)', fontSize: 13 }}>
              ✓ Model reloaded
            </span>
          ) : retrainStatus === 'failed' ? (
            <span style={{ color: 'var(--danger)', fontSize: 13 }}>
              ✗ Retrain failed
            </span>
          ) : (
            <button onClick={handleRetrain} style={styles.retrainBtn}>
              ↺ Retrain Model
            </button>
          )}
        </div>
      </header>

      {/* Stat Cards */}
      <div style={styles.grid4}>
        <StatCard
          label="Total Customers"
          value={stats.total_customers.toLocaleString()}
          color="var(--primary)"
        />
        <StatCard
          label="Churn Rate"
          value={`${(stats.churn_rate * 100).toFixed(1)}%`}
          color="var(--danger)"
        />
        <StatCard
          label="Critical Risk"
          value={stats.critical_risk_count.toLocaleString()}
          sub="need immediate action"
          color="var(--critical)"
        />
        <StatCard
          label="Active Customers"
          value={stats.active_customers.toLocaleString()}
          color="var(--success)"
        />
      </div>

      {/* Charts Row */}
      <div style={styles.grid2}>
        <div style={styles.card}>
          <h2 style={styles.cardTitle}>Churn Trend</h2>
          <ChurnTrendChart data={trend} />
        </div>
        <div style={styles.card}>
          <h2 style={styles.cardTitle}>Risk Distribution</h2>
          <RiskDistributionChart stats={stats} />
        </div>
      </div>

      {/* Feature Importance */}
      <div style={styles.card}>
        <h2 style={styles.cardTitle}>Top Churn Drivers</h2>
        <p style={styles.cardSub}>
          Features with highest predictive weight in the XGBoost model
        </p>
        <FeatureImportanceChart data={features} />
      </div>

      {/* Customer Table */}
      <div style={styles.card}>
        <div style={styles.tableHeader}>
          <div>
            <h2 style={styles.cardTitle}>Customer Risk List</h2>
            <p style={styles.cardSub}>Sorted by churn probability</p>
          </div>
          <div style={styles.filters}>
            {['', 'Critical', 'High', 'Medium', 'Low'].map(seg => (
              <button
                key={seg}
                onClick={() => handleFilterChange(seg)}
                style={{
                  ...styles.filterBtn,
                  background: filter === seg ? 'var(--primary)' : 'transparent',
                }}
              >
                {seg || 'All'}
              </button>
            ))}
          </div>
        </div>
        <CustomerTable
          customers={customers}
          onRowClick={(id) => navigate(`/customer/${id}`)}
        />
      </div>

    </div>
  )
}

const styles = {
  page: {
    maxWidth: 1200, margin: '0 auto', padding: '32px 24px',
    display: 'flex', flexDirection: 'column', gap: 24,
  },
  loading: {
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    justifyContent: 'center', height: '100vh', gap: 16, color: 'var(--muted)',
  },
  spinner: {
    width: 32, height: 32, border: '3px solid var(--border)',
    borderTop: '3px solid var(--primary)', borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  header: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
  },
  title: { fontSize: 24, fontWeight: 700, color: 'var(--text)' },
  subtitle: { color: 'var(--muted)', marginTop: 4 },
  badge: {
    background: 'var(--surface)', border: '1px solid var(--border)',
    padding: '8px 16px', borderRadius: 8, color: 'var(--warning)',
    fontWeight: 600,
  },
  grid4: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 },
  grid2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 },
  card: {
    background: 'var(--surface)', border: '1px solid var(--border)',
    borderRadius: 12, padding: 24,
  },
  cardTitle: { fontSize: 16, fontWeight: 600, marginBottom: 4 },
  cardSub: { color: 'var(--muted)', fontSize: 13, marginBottom: 16 },
  tableHeader: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'flex-start', marginBottom: 16,
  },
  filters: { display: 'flex', gap: 8 },
  filterBtn: {
    padding: '6px 14px', borderRadius: 6, border: '1px solid var(--border)',
    color: 'var(--text)', cursor: 'pointer', fontSize: 13,
  },
  retrainBtn: {
    background: 'transparent', border: '1px solid var(--primary)',
    color: 'var(--primary)', padding: '8px 16px', borderRadius: 8,
    cursor: 'pointer', fontSize: 13, fontWeight: 600,
  },
  retrainBtnDisabled: {
    background: 'transparent', border: '1px solid var(--border)',
    color: 'var(--muted)', padding: '8px 16px', borderRadius: 8,
    cursor: 'not-allowed', fontSize: 13,
  },
  reloadBtn: {
    background: 'var(--success)', border: 'none',
    color: '#fff', padding: '8px 16px', borderRadius: 8,
    cursor: 'pointer', fontSize: 13, fontWeight: 600,
  },
  cohortBtn: {
    background: 'transparent', border: '1px solid var(--border)',
    color: 'var(--muted)', padding: '8px 16px', borderRadius: 8,
    cursor: 'pointer', fontSize: 13, fontWeight: 500,
    letterSpacing: '0.01em',
  },
}
