import {
    Chart as ChartJS, CategoryScale, LinearScale,
    PointElement, LineElement, Filler, Tooltip
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip)

export default function ChurnTrendChart({ data }) {
    if (!data.length) return <p style={{ color: 'var(--muted)' }}>No data</p>

    const chartData = {
        labels: data.map(d => d.month),
        datasets: [{
            label: 'Churned Customers',
            data: data.map(d => d.churned_count),
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239,68,68,0.1)',
            fill: true,
            tension: 0.4,
            pointRadius: 3,
        }],
    }

    const options = {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
            x: { ticks: { color: '#64748b' }, grid: { color: '#2a2d3a' } },
            y: { ticks: { color: '#64748b' }, grid: { color: '#2a2d3a' } },
        },
    }

    return <Line data={chartData} options={options} />
}
