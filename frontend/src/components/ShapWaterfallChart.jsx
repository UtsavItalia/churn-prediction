import {
    Chart as ChartJS, CategoryScale, LinearScale,
    BarElement, Tooltip, Legend
} from 'chart.js'
import { Bar } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

export default function ShapWaterfallChart({ data }) {
    if (!data || !Object.keys(data).length) return null

    const entries = Object.entries(data)
    const labels = entries.map(([k]) => k.replace(/_/g, ' '))
    const values = entries.map(([, v]) => parseFloat(v))

    // Color by direction: positive = danger (toward churn), negative = success
    const colors = values.map(v =>
        v > 0
            ? 'rgba(239, 68, 68, 0.85)'    // red — increases churn risk
            : 'rgba(16, 185, 129, 0.85)'   // green — decreases churn risk
    )

    const chartData = {
        labels,
        datasets: [{
            label: 'SHAP Value',
            data: values,
            backgroundColor: colors,
            borderRadius: 4,
        }],
    }

    const options = {
        indexAxis: 'y',
        responsive: true,
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: (ctx) => {
                        const v = ctx.raw
                        const dir = v > 0 ? '↑ increases churn risk' : '↓ reduces churn risk'
                        return ` SHAP: ${v.toFixed(4)}  ${dir}`
                    }
                }
            }
        },
        scales: {
            x: {
                ticks: { color: '#64748b' },
                grid: { color: '#2a2d3a' },
                // Draw a center line at 0
                afterDraw(chart) {
                    const ctx = chart.ctx
                    const xAxis = chart.scales.x
                    const yAxis = chart.scales.y
                    const x = xAxis.getPixelForValue(0)
                    ctx.save()
                    ctx.beginPath()
                    ctx.moveTo(x, yAxis.top)
                    ctx.lineTo(x, yAxis.bottom)
                    ctx.strokeStyle = 'rgba(255,255,255,0.2)'
                    ctx.lineWidth = 1
                    ctx.stroke()
                    ctx.restore()
                }
            },
            y: {
                ticks: { color: '#e2e8f0' },
                grid: { display: false },
            },
        },
    }

    return (
        <div>
            <Bar data={chartData} options={options} height={200} />
            <div style={styles.legend}>
                <span style={styles.legendItem}>
                    <span style={{ ...styles.dot, background: '#ef4444' }} />
                    Increases churn risk
                </span>
                <span style={styles.legendItem}>
                    <span style={{ ...styles.dot, background: '#10b981' }} />
                    Reduces churn risk
                </span>
            </div>
        </div>
    )
}

const styles = {
    legend: {
        display: 'flex', gap: 24, marginTop: 12,
        justifyContent: 'center',
    },
    legendItem: {
        display: 'flex', alignItems: 'center', gap: 6,
        color: 'var(--muted)', fontSize: 12,
    },
    dot: {
        width: 8, height: 8, borderRadius: '50%', display: 'inline-block',
    },
}
