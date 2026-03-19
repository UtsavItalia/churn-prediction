import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ShapWaterfallChart from '../components/ShapWaterfallChart'
import PredictionHistoryChart from '../components/PredictionHistoryChart'
import { getCustomer, predictCustomer, getPredictionHistory } from '../services/api'

export default function CustomerDetail() {
    const [history, setHistory] = useState([])
    const { id } = useParams()
    const navigate = useNavigate()
    const [customer, setCustomer] = useState(null)
    const [predicting, setPredicting] = useState(false)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        getCustomer(id)
            .then(res => {
                setCustomer(res.data)
            })
            .catch(err => {
                console.error('Failed to load customer:', err)
            })
            .finally(() => {
                setLoading(false)  // always unblock loading
            })

        getPredictionHistory(id)
            .then(res => setHistory(res.data))
            .catch(() => setHistory([]))
    }, [id])


    const handlePredict = async () => {
        setPredicting(true)
        const res = await predictCustomer(id)
        setCustomer(prev => ({
            ...prev,
            churn_probability: res.data.churn_probability,
            risk_segment: res.data.risk_segment,
            top_features: res.data.top_features,
            predicted_at: res.data.predicted_at,
        }))
        setHistory(prev => [...prev, {
            predicted_at: res.data.predicted_at,
            churn_probability: res.data.churn_probability,
            risk_segment: res.data.risk_segment,
            model_version: res.data.model_version,
        }])
        setPredicting(false)
    }

    if (loading) return (
        <div style={styles.loading}>Loading customer...</div>
    )
    if (!customer) return (
        <div style={styles.loading}>Customer not found.</div>
    )


    const riskColor = {
        Critical: 'var(--critical)',
        High: 'var(--danger)',
        Medium: 'var(--warning)',
        Low: 'var(--success)',
    }[customer.risk_segment] || 'var(--muted)'

    return (
        <div style={styles.page}>

            {/* Back */}
            <button onClick={() => navigate('/')} style={styles.back}>
                ← Back to Dashboard
            </button>

            {/* Header */}
            <div style={styles.header}>
                <div>
                    <h1 style={styles.title}>{customer.customer_id}</h1>
                    <p style={styles.subtitle}>
                        {customer.industry} · {customer.company_size} · {customer.country}
                    </p>
                </div>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    {customer.risk_segment && (
                        <span style={{ ...styles.riskBadge, background: riskColor }}>
                            {customer.risk_segment} Risk
                        </span>
                    )}
                    <button
                        onClick={handlePredict}
                        disabled={predicting}
                        style={styles.predictBtn}
                    >
                        {predicting ? 'Running...' : 'Run Prediction'}
                    </button>
                </div>
            </div>

            {/* Info Grid */}
            <div style={styles.grid3}>
                <InfoCard label="Plan" value={customer.plan_tier} />
                <InfoCard label="Contract" value={customer.contract_type} />
                <InfoCard label="Acquired Via" value={customer.acquisition_channel} />
                <InfoCard label="Customer Since"
                    value={new Date(customer.created_at).toLocaleDateString()} />
                <InfoCard label="Status"
                    value={customer.churned ? 'Churned' : 'Active'}
                    color={customer.churned ? 'var(--danger)' : 'var(--success)'} />
                <InfoCard label="Churn Reason"
                    value={customer.churn_reason || '—'} />
            </div>

            {/* Prediction */}
            {customer.churn_probability != null && (
                <div style={styles.card}>
                    <h2 style={styles.cardTitle}>Churn Prediction</h2>
                    <div style={styles.probRow}>
                        <div style={styles.probValue}>
                            {(customer.churn_probability * 100).toFixed(1)}%
                        </div>
                        <div style={styles.probBar}>
                            <div style={{
                                ...styles.probFill,
                                width: `${customer.churn_probability * 100}%`,
                                background: riskColor,
                            }} />
                        </div>
                    </div>
                    <p style={styles.probSub}>
                        Predicted at {new Date(customer.predicted_at).toLocaleString()}
                    </p>

                    {/* Top Features */}
                    {customer.top_features && (
                        <div style={{ marginTop: 24 }}>
                            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
                                SHAP Feature Contributions
                            </h3>
                            <p style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 16 }}>
                                Positive values push toward churn · Negative values reduce risk
                            </p>
                            <ShapWaterfallChart data={customer.top_features} />
                        </div>
                    )}
                </div>
            )}

            {/* Prediction History */}
            <div style={styles.card}>
                <h2 style={styles.cardTitle}>Risk Score History</h2>
                <p style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 16 }}>
                    Churn probability over time · Dashed lines show risk thresholds
                </p>
                <PredictionHistoryChart data={history} />
            </div>

        </div>
    )
}

function InfoCard({ label, value, color }) {
    return (
        <div style={styles.infoCard}>
            <p style={styles.infoLabel}>{label}</p>
            <p style={{ ...styles.infoValue, color: color || 'var(--text)' }}>{value}</p>
        </div>
    )
}

const styles = {
    page: {
        maxWidth: 900, margin: '0 auto', padding: '32px 24px',
        display: 'flex', flexDirection: 'column', gap: 24,
    },
    loading: { padding: 48, color: 'var(--muted)' },
    back: {
        background: 'none', border: 'none', color: 'var(--muted)',
        cursor: 'pointer', fontSize: 14, textAlign: 'left', padding: 0,
    },
    header: {
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
    },
    title: { fontSize: 22, fontWeight: 700 },
    subtitle: { color: 'var(--muted)', marginTop: 4 },
    riskBadge: {
        padding: '6px 14px', borderRadius: 20, fontSize: 13,
        fontWeight: 600, color: '#fff',
    },
    predictBtn: {
        background: 'var(--primary)', border: 'none', color: '#fff',
        padding: '8px 20px', borderRadius: 8, cursor: 'pointer',
        fontSize: 14, fontWeight: 600,
    },
    grid3: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 },
    infoCard: {
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 10, padding: '16px 20px',
    },
    infoLabel: { color: 'var(--muted)', fontSize: 12, marginBottom: 4 },
    infoValue: { fontWeight: 600, fontSize: 15 },
    card: {
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 12, padding: 24,
    },
    cardTitle: { fontSize: 16, fontWeight: 600, marginBottom: 16 },
    probRow: { display: 'flex', alignItems: 'center', gap: 20, marginBottom: 8 },
    probValue: { fontSize: 36, fontWeight: 700, minWidth: 90 },
    probBar: {
        flex: 1, height: 12, background: 'var(--border)',
        borderRadius: 6, overflow: 'hidden',
    },
    probFill: { height: '100%', borderRadius: 6, transition: 'width 0.5s ease' },
    probSub: { color: 'var(--muted)', fontSize: 12 },
    featureRow: {
        display: 'flex', justifyContent: 'space-between',
        padding: '8px 0', borderBottom: '1px solid var(--border)',
    },
    featureName: { color: 'var(--muted)', textTransform: 'capitalize' },
    featureVal: { fontWeight: 600 },
}
