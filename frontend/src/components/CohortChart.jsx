import {
    Chart as ChartJS, CategoryScale, LinearScale,
    BarElement, Tooltip, Legend
} from 'chart.js'
import { Bar } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

export default function CohortChart({ data, title }) {
    if (!data || !data.length) return null

    const labels = data.map(d => d.segment)
    const churnRates = data.map(d => parseFloat(d.churn_rate_pct))
    const riskScores = data.map(d => parseFloat(d.avg_risk_score || 0))
    const totals = data.map(d => d.total)

    const chartData = {
        labels,
        datasets: [
            {
                label: 'Actual Churn Rate %',
                data: churnRates,
                backgroundColor: 'rgba(239, 68, 68, 0.8)',
                borderRadius: 4,
                yAxisID: 'y',
            },
            {
                label: 'Avg Predicted Risk %',
                data: riskScores,
                backgroundColor: 'rgba(99, 102, 241, 0.6)',
                borderRadius: 4,
                yAxisID: 'y',
            },
        ],
    }

    const options = {
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: {
                labels: { color: '#e2e8f0', font: { size: 12 } },
            },
            tooltip: {
                callbacks: {
                    afterBody: (items) => {
                        const idx = items[0]?.dataIndex
                        return idx !== undefined
                            ? [`Total customers: ${totals[idx]}`]
                            : []
                    },
                },
            },
        },
        scales: {
            x: {
                ticks: { color: '#e2e8f0' },
                grid: { color: '#2a2d3a' },
            },
            y: {
                min: 0,
                max: 100,
                ticks: {
                    color: '#64748b',
                    callback: v => `${v}%`,
                },
                grid: { color: '#2a2d3a' },
            },
        },
    }

    return (
        <div>
            <Bar data={chartData} options={options} height={280} />
            {/* Segment table below chart */}
            <table style={styles.table}>
                <thead>
                    <tr>
                        {['Segment', 'Total', 'Churned', 'Churn Rate', 'Avg Risk'].map(h => (
                            <th key={h} style={styles.th}>{h}</th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.map(d => (
                        <tr key={d.segment} style={styles.tr}>
                            <td style={styles.td}><strong>{d.segment}</strong></td>
                            <td style={styles.td}>{d.total}</td>
                            <td style={styles.td}>{d.churned}</td>
                            <td style={{
                                ...styles.td,
                                color: d.churn_rate_pct > 50 ? 'var(--danger)'
                                    : d.churn_rate_pct > 30 ? 'var(--warning)'
                                        : 'var(--success)',
                                fontWeight: 600,
                            }}>
                                {d.churn_rate_pct}%
                            </td>
                            <td style={styles.td}>{d.avg_risk_score}%</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

const styles = {
    table: {
        width: '100%', borderCollapse: 'collapse',
        marginTop: 20, fontSize: 13,
    },
    th: {
        textAlign: 'left', padding: '8px 12px',
        color: 'var(--muted)', fontSize: 11,
        fontWeight: 600, textTransform: 'uppercase',
        borderBottom: '1px solid var(--border)',
    },
    tr: { borderBottom: '1px solid var(--border)' },
    td: { padding: '10px 12px', color: 'var(--text)' },
}
