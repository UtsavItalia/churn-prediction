import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCohortAnalysis } from '../services/api'
import CohortChart from '../components/CohortChart'

const TABS = [
    { key: 'industry', label: 'Industry' },
    { key: 'plan_tier', label: 'Plan Tier' },
    { key: 'contract_type', label: 'Contract Type' },
    { key: 'company_size', label: 'Company Size' },
    { key: 'acquisition_channel', label: 'Acquisition Channel' },
]

export default function CohortAnalysis() {
    const navigate = useNavigate()
    const [data, setData] = useState(null)
    const [tab, setTab] = useState('industry')
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        getCohortAnalysis().then(res => {
            setData(res.data)
            setLoading(false)
        })
    }, [])

    if (loading) return (
        <div style={styles.loading}>Loading cohort analysis...</div>
    )

    const activeData = data[tab] || []

    // Key insight — highest and lowest churn segment
    const sorted = [...activeData].sort((a, b) => b.churn_rate_pct - a.churn_rate_pct)
    const highest = sorted[0]
    const lowest = sorted[sorted.length - 1]

    return (
        <div style={styles.page}>

            {/* Header */}
            <div style={styles.headerRow}>
                <div>
                    <button onClick={() => navigate('/')} style={styles.back}>
                        ← Back to Dashboard
                    </button>
                    <h1 style={styles.title}>Cohort Analysis</h1>
                    <p style={styles.subtitle}>
                        Churn rate and predicted risk broken down by customer segment
                    </p>
                </div>
            </div>

            {/* Insight cards */}
            {highest && lowest && (
                <div style={styles.insightRow}>
                    <div style={{ ...styles.insightCard, borderColor: 'var(--danger)' }}>
                        <p style={styles.insightLabel}>Highest churn segment</p>
                        <p style={styles.insightValue}>{highest.segment}</p>
                        <p style={{ color: 'var(--danger)', fontWeight: 600 }}>
                            {highest.churn_rate_pct}% churn rate
                        </p>
                    </div>
                    <div style={{ ...styles.insightCard, borderColor: 'var(--success)' }}>
                        <p style={styles.insightLabel}>Lowest churn segment</p>
                        <p style={styles.insightValue}>{lowest.segment}</p>
                        <p style={{ color: 'var(--success)', fontWeight: 600 }}>
                            {lowest.churn_rate_pct}% churn rate
                        </p>
                    </div>
                    <div style={{ ...styles.insightCard, borderColor: 'var(--primary)' }}>
                        <p style={styles.insightLabel}>Churn rate spread</p>
                        <p style={styles.insightValue}>
                            {(highest.churn_rate_pct - lowest.churn_rate_pct).toFixed(1)}%
                        </p>
                        <p style={{ color: 'var(--muted)', fontSize: 12 }}>
                            between best and worst segment
                        </p>
                    </div>
                </div>
            )}

            {/* Tabs + Chart */}
            <div style={styles.card}>
                <div style={styles.tabs}>
                    {TABS.map(t => (
                        <button
                            key={t.key}
                            onClick={() => setTab(t.key)}
                            style={{
                                ...styles.tab,
                                borderBottom: tab === t.key
                                    ? '2px solid var(--primary)'
                                    : '2px solid transparent',
                                color: tab === t.key ? 'var(--text)' : 'var(--muted)',
                            }}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>
                <div style={{ marginTop: 24 }}>
                    <CohortChart
                        data={activeData}
                        title={TABS.find(t => t.key === tab)?.label}
                    />
                </div>
            </div>

        </div>
    )
}

const styles = {
    page: {
        maxWidth: 1100, margin: '0 auto', padding: '32px 24px',
        display: 'flex', flexDirection: 'column', gap: 24,
    },
    loading: { padding: 48, color: 'var(--muted)' },
    headerRow: {
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
    },
    back: {
        background: 'none', border: 'none', color: 'var(--muted)',
        cursor: 'pointer', fontSize: 14, padding: 0, marginBottom: 8,
        display: 'block',
    },
    title: { fontSize: 24, fontWeight: 700 },
    subtitle: { color: 'var(--muted)', marginTop: 4 },
    insightRow: {
        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16,
    },
    insightCard: {
        background: 'var(--surface)', border: '1px solid',
        borderRadius: 12, padding: '20px 24px',
        display: 'flex', flexDirection: 'column', gap: 6,
    },
    insightLabel: { color: 'var(--muted)', fontSize: 12 },
    insightValue: { fontSize: 20, fontWeight: 700 },
    card: {
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 12, padding: 24,
    },
    tabs: {
        display: 'flex', gap: 0,
        borderBottom: '1px solid var(--border)',
    },
    tab: {
        background: 'none', border: 'none', padding: '10px 20px',
        cursor: 'pointer', fontSize: 14, fontWeight: 500,
        transition: 'color 0.15s',
    },
}
