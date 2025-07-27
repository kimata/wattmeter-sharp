import { memo, useMemo } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  BarController,
  LineController,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { Chart } from 'react-chartjs-2'
import type { SensorData } from '../types'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  BarController,
  LineController,
  Title,
  Tooltip,
  Legend
)

interface AvailabilityChartProps {
  sensors: SensorData[]
}

function AvailabilityChartComponent({ sensors }: AvailabilityChartProps) {
  const chartData = useMemo(() => ({
    labels: sensors.map(sensor => sensor.name),
    datasets: [
      {
        label: '過去24時間 (%)',
        type: 'bar' as const,
        data: sensors.map(sensor => sensor.availability_24h),
        backgroundColor: sensors.map(sensor =>
          sensor.availability_24h >= 90 ? 'rgba(76, 175, 80, 0.8)' :   // 明るい緑
          sensor.availability_24h >= 70 ? 'rgba(255, 193, 7, 0.8)' :   // 明るい黄色
          'rgba(244, 67, 54, 0.8)'                                     // 明るい赤
        ),
        borderColor: sensors.map(sensor =>
          sensor.availability_24h >= 90 ? 'rgba(76, 175, 80, 1)' :     // 緑のボーダー
          sensor.availability_24h >= 70 ? 'rgba(255, 193, 7, 1)' :     // 黄色のボーダー
          'rgba(244, 67, 54, 1)'                                       // 赤のボーダー
        ),
        borderWidth: 2,
        yAxisID: 'y'
      },
      {
        label: '累計稼働率 (%)',
        type: 'line' as const,
        data: sensors.map(sensor => sensor.availability_total),
        borderColor: 'transparent',                                     // 線を透明に
        backgroundColor: 'transparent',
        borderWidth: 0,                                                 // 線幅を0に
        pointBackgroundColor: sensors.map(sensor =>
          sensor.availability_total >= 90 ? 'rgba(76, 175, 80, 1)' :   // 緑
          sensor.availability_total >= 70 ? 'rgba(255, 193, 7, 1)' :   // 黄色
          'rgba(244, 67, 54, 1)'                                       // 赤
        ),
        pointBorderColor: sensors.map(sensor =>
          sensor.availability_total >= 90 ? 'rgba(76, 175, 80, 1)' :   // 緑
          sensor.availability_total >= 70 ? 'rgba(255, 193, 7, 1)' :   // 黄色
          'rgba(244, 67, 54, 1)'                                       // 赤
        ),
        pointBorderWidth: 2,
        pointRadius: 8,
        pointHoverRadius: 10,
        fill: false,
        tension: 0.3,
        yAxisID: 'y'
      }
    ]
  }), [sensors])

  const chartOptions = useMemo(() => ({
    responsive: true,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
      },
      title: {
        display: false
      },
      tooltip: {
        callbacks: {
          label: (context: any) => {
            return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`
          }
        }
      }
    },
    scales: {
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: (value: any) => `${value}%`
        },
        title: {
          display: true,
          text: '稼働率 (%)'
        }
      }
    }
  }), [])

  return (
    <div className="row mb-5" data-testid="availability-chart">
      <div className="col">
        <h2 className="h4 mb-3">センサー稼働率</h2>
        <Chart type="bar" data={chartData} options={chartOptions} />
      </div>
    </div>
  )
}

export const AvailabilityChart = memo(AvailabilityChartComponent)
