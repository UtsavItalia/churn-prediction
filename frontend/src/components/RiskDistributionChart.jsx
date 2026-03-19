import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import { Doughnut } from 'react-chartjs-2'

ChartJS.register(ArcElement, Tooltip, Legend)

export default function RiskDistributionChart({ stats }) {
    const chartData = {
        labels: ['Critical', 'High', 'Medium', 'Low'],
        datasets: [{
            data: [
                stats.critical_risk_count,
                stats.high_risk_count,
                stats.medium_risk_count,
                stats.low_risk_count,
            ],
            backgroundColor: ['#dc2626', '#ef4444', '#f59e0b', '#10b981'],
            borderWidth: 0,
        }],
    }

    const options = {
        responsive: true,
        cutout: '65%',
        plugins: {
            legend: {
                position: 'right',
                labels: { color: '#e2e8f0', padding: 16, font: { size: 13 } },
            },
        },
    }

    return <Doughnut data={chartData} options={options} />
}
