import { Bar } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'

import type { CommunicationErrorHistogram } from '../types'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
)

interface CommunicationErrorChartProps {
  histogram: CommunicationErrorHistogram
}

export function CommunicationErrorChart({ histogram }: CommunicationErrorChartProps) {
  const data = {
    labels: histogram.bin_labels,
    datasets: [
      {
        label: '通信エラー件数',
        data: histogram.bins,
        backgroundColor: 'rgba(220, 53, 69, 0.6)',
        borderColor: 'rgba(220, 53, 69, 1)',
        borderWidth: 1,
      },
    ],
  }

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: false,
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: '時刻（30分刻み）',
        },
        ticks: {
          maxTicksLimit: 12, // 2時間刻みで表示
          callback: function(value: string | number) {
            const index = Number(value)
            return index % 4 === 0 ? histogram.bin_labels[index] : ''
          }
        }
      },
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'エラー件数',
        },
        ticks: {
          stepSize: 1,
        },
      },
    },
  }

  return (
    <div className="row mb-4">
      <div className="col">
        <h2 className="h4 mb-3">通信エラー発生状況（過去24時間、合計: {histogram.total_errors}件）</h2>
        <Bar data={data} options={options} />
      </div>
    </div>
  )
}
