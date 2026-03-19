import {
    Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip
} from 'chart.js'
import { Bar } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip)

export default function FeatureImportanceChart({ data }) {
    const top10 = data.slice(0, 10)
    const labels = top10.map(d => d.feature.replace(/_/g, ' '))
    const values = top10.map(d => parseFloat(d.importance.toFixed(4)))

    const chartData = {
        labels,
        datasets: [{
            label: 'Importance',
            data: values,
            backgroundColor: 'rgba(99,102,241,0.8)',
            borderRadius: 4,
        }],
    }

    const options = {
        indexAxis: 'y',
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
            x: { ticks: { color: '#64748b' }, grid: { color: '#2a2d3a' } },
            y: { ticks: { color: '#e2e8f0' }, grid: { display: false } },
        },
    }

    return <Bar data={chartData} options={options} height={320} />
}
