import { memo, useMemo, useRef, useEffect } from 'react'
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
import styles from './CommunicationError.module.css'

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
  const notificationRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // ページ読み込み時にハッシュがあれば該当要素にスクロール
    if (window.location.hash === '#sensor-availability') {
      const element = document.getElementById('sensor-availability')
      if (element) {
        setTimeout(() => {
          element.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }, 500)
      }
    }
  }, [])

  const copyPermalink = (elementId: string) => {
    const currentUrl = window.location.origin + window.location.pathname
    const permalink = currentUrl + '#' + elementId

    navigator.clipboard.writeText(permalink).then(() => {
      showCopyNotification('パーマリンクをコピーしました')
      window.history.pushState(null, '', '#' + elementId)
    }).catch(() => {
      // フォールバック
      const textArea = document.createElement('textarea')
      textArea.value = permalink
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)

      showCopyNotification('パーマリンクをコピーしました')
      window.history.pushState(null, '', '#' + elementId)
    })
  }

  const showCopyNotification = (message: string) => {
    if (!notificationRef.current) return

    notificationRef.current.textContent = message
    notificationRef.current.classList.add(styles.show)

    setTimeout(() => {
      notificationRef.current?.classList.remove(styles.show)
    }, 3000)
  }
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
    layout: {
      padding: {
        top: 20,
      }
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
    <>
      <div className={`section ${styles.chartSection}`} id="sensor-availability" data-testid="availability-chart">
        <div className={styles.sectionHeader}>
          <h2 className="title is-4">
            <span className={styles.icon}>📊</span>
            センサー稼働率
            <i
              className={`fas fa-link ${styles.permalinkIcon}`}
              onClick={() => copyPermalink('sensor-availability')}
              title="パーマリンクをコピー"
            />
          </h2>
        </div>
        <div className="table-container">
          <div className="chart-container" style={{ position: 'relative', height: '350px', margin: '0.5rem 0' }}>
            <Chart type="bar" data={chartData} options={chartOptions} />
          </div>
        </div>
      </div>
      <div ref={notificationRef} className={styles.copyNotification}></div>
    </>
  )
}

export const AvailabilityChart = memo(AvailabilityChartComponent)
