import {
    Chart as ChartJS, CategoryScale, LinearScale,
    PointElement, LineElement, Filler, Tooltip, Legend
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(
    CategoryScale, LinearScale, PointElement,
    LineElement, Filler, Tooltip, Legend
)

const RISK_COLORS = {
    Critical: '#dc2626',
    High: '#ef4444',
    Medium: '#f59e0b',
    Low: '#10b981',
}

export default function PredictionHistoryChart({ data }) {
    if (!data || data.length === 0) {
        return (
            <div style={styles.empty}>
                No prediction history yet. Click "Run Prediction" to start tracking.
            </div>
        )
    }

    // Format timestamps for labels
    const labels = data.map(d =>
        new Date(d.predicted_at).toLocaleDateString('en-US', {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        })
    )

    const probabilities = data.map(d =>
        parseFloat((d.churn_probability * 100).toFixed(1))
    )

    // Color each point by its risk segment
    const pointColors = data.map(d =>
        RISK_COLORS[d.risk_segment] || '#64748b'
    )

    const chartData = {
        labels,
        datasets: [
            {
                label: 'Churn Probability %',
                data: probabilities,
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99,102,241,0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 6,
                pointBackgroundColor: pointColors,
                pointBorderColor: pointColors,
                pointHoverRadius: 8,
            },
            // Risk threshold lines as datasets
            {
                label: 'Critical threshold (75%)',
                data: new Array(labels.length).fill(75),
                borderColor: 'rgba(220,38,38,0.4)',
                borderDash: [6, 4],
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
            },
            {
                label: 'High threshold (50%)',
                data: new Array(labels.length).fill(50),
                borderColor: 'rgba(239,68,68,0.3)',
                borderDash: [6, 4],
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
            },
            {
                label: 'Medium threshold (25%)',
                data: new Array(labels.length).fill(25),
                borderColor: 'rgba(245,158,11,0.3)',
                borderDash: [6, 4],
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
            },
        ],
    }

    const options = {
        responsive: true,
        interaction: {
            mode: 'index',
            intersect: false,
        },
        plugins: {
            legend: {
                labels: {
                    color: '#64748b',
                    fontSize: 11,
                    filter: (item) => !item.text.includes('threshold'),
                },
            },
            tooltip: {
                callbacks: {
                    label: (ctx) => {
                        if (ctx.datasetIndex !== 0) return null
                        const d = data[ctx.dataIndex]
                        const version = d.model_version || 'unknown'
                        return [
                            ` Churn probability: ${ctx.raw}%`,
                            ` Risk segment: ${d.risk_segment}`,
                            ` Model: ${version}`,
                        ]
                    },
                },
            },
        },
        scales: {
            x: {
                ticks: {
                    color: '#64748b',
                    maxRotation: 45,
                    font: { size: 11 },
                },
                grid: { color: '#2a2d3a' },
            },
            y: {
                min: 0,
                max: 100,
                ticks: {
                    color: '#64748b',
                    callback: (v) => `${v}%`,
                },
                grid: { color: '#2a2d3a' },
            },
        },
    }

    // Summary stats below chart
    const latest = probabilities[probabilities.length - 1]
    const earliest = probabilities[0]
    const trend = latest - earliest
    const trendStr = trend > 0
        ? `↑ +${trend.toFixed(1)}% since first prediction`
        : `↓ ${trend.toFixed(1)}% since first prediction`
    const trendColor = trend > 0 ? 'var(--danger)' : 'var(--success)'

    return (
        <div>
            <Line data={chartData} options={options} />
            <div style={styles.summary}>
                <div style={styles.summaryItem}>
                    <span style={styles.summaryLabel}>Predictions recorded</span>
                    <span style={styles.summaryValue}>{data.length}</span>
                </div>
                <div style={styles.summaryItem}>
                    <span style={styles.summaryLabel}>Latest score</span>
                    <span style={styles.summaryValue}>{latest}%</span>
                </div>
                <div style={styles.summaryItem}>
                    <span style={styles.summaryLabel}>Trend</span>
                    <span style={{ ...styles.summaryValue, color: trendColor }}>
                        {trendStr}
                    </span>
                </div>
                <div style={styles.summaryItem}>
                    <span style={styles.summaryLabel}>Models used</span>
                    <span style={styles.summaryValue}>
                        {[...new Set(data.map(d => d.model_version))].join(', ')}
                    </span>
                </div>
            </div>
        </div>
    )
}

const styles = {
    empty: {
        color: 'var(--muted)', fontSize: 13,
        padding: '24px 0', textAlign: 'center',
    },
    summary: {
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 16, marginTop: 20,
        paddingTop: 16, borderTop: '1px solid var(--border)',
    },
    summaryItem: {
        display: 'flex', flexDirection: 'column', gap: 4,
    },
    summaryLabel: { color: 'var(--muted)', fontSize: 11 },
    summaryValue: { fontWeight: 600, fontSize: 14 },
}
