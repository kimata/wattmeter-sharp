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

    // Clipboard APIが利用可能かチェック
    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      navigator.clipboard.writeText(permalink).then(() => {
        showCopyNotification('パーマリンクをコピーしました')
        window.history.pushState(null, '', '#' + elementId)
      }).catch(() => {
        // Clipboard APIが失敗した場合のフォールバック
        fallbackCopyToClipboard(permalink, elementId)
      })
    } else {
      // Clipboard APIが利用できない場合のフォールバック
      fallbackCopyToClipboard(permalink, elementId)
    }
  }

  const fallbackCopyToClipboard = (text: string, elementId: string) => {
    try {
      const textArea = document.createElement('textarea')
      textArea.value = text
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      const successful = document.execCommand('copy')
      document.body.removeChild(textArea)

      if (successful) {
        showCopyNotification('パーマリンクをコピーしました')
      } else {
        showCopyNotification('コピーに失敗しました')
      }
      window.history.pushState(null, '', '#' + elementId)
    } catch (err) {
      console.error('コピーに失敗しました:', err)
      showCopyNotification('コピーに失敗しました')
      window.history.pushState(null, '', '#' + elementId)
    }
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
          sensor.availability_24h >= 90 ? 'rgba(76, 175, 80, 0.5)' :   // より淡い緑
          sensor.availability_24h >= 70 ? 'rgba(255, 193, 7, 0.5)' :   // より淡い黄色
          'rgba(244, 67, 54, 0.5)'                                     // より淡い赤
        ),
        borderColor: sensors.map(sensor =>
          sensor.availability_24h >= 90 ? 'rgba(76, 175, 80, 0.7)' :   // 淡い緑のボーダー
          sensor.availability_24h >= 70 ? 'rgba(255, 193, 7, 0.7)' :   // 淡い黄色のボーダー
          'rgba(244, 67, 54, 0.7)'                                     // 淡い赤のボーダー
        ),
        borderWidth: 2,
        order: 2,                                                       // 背面に配置
        yAxisID: 'y'
      },
      {
        label: '累計稼働率 (%)',
        type: 'line' as const,
        data: sensors.map(sensor => sensor.availability_total),
        borderColor: 'transparent',                                     // 線を透明に
        backgroundColor: 'transparent',
        borderWidth: 0,                                                 // 線幅を0に
        showLine: false,                                                // 線を非表示
        pointBackgroundColor: sensors.map(sensor =>
          sensor.availability_total >= 90 ? 'rgba(56, 142, 60, 1)' :   // 濃い緑
          sensor.availability_total >= 70 ? 'rgba(245, 124, 0, 1)' :   // 濃いオレンジ
          'rgba(211, 47, 47, 1)'                                       // 濃い赤
        ),
        pointBorderColor: sensors.map(sensor =>
          sensor.availability_total >= 90 ? 'rgba(56, 142, 60, 1)' :   // 濃い緑
          sensor.availability_total >= 70 ? 'rgba(245, 124, 0, 1)' :   // 濃いオレンジ
          'rgba(211, 47, 47, 1)'                                       // 濃い赤
        ),
        pointBorderWidth: 2,
        pointRadius: 6,
        pointHoverRadius: 8,
        pointStyle: 'circle',                                           // ポイントスタイルを丸印に指定
        order: 1,                                                       // 前面に配置
        fill: false,
        tension: 0.3,
        yAxisID: 'y'
      }
    ]
  }), [sensors])

  const chartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    clip: false as any,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    layout: {
      padding: {
        top: 20,
        left: 10,
        right: 10,
        bottom: 20
      }
    },
    font: {
      family: '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", "Yu Gothic", sans-serif',
      size: 14
    },
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
        labels: {
          font: {
            family: '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", "Yu Gothic", sans-serif',
            size: 14
          },
          generateLabels: (chart: any) => {
            const original = chart.constructor.defaults.plugins.legend.labels.generateLabels
            const labels = original.call(chart, chart)

            // 累計稼働率のラベルをカスタマイズ
            labels.forEach((label: any) => {
              if (label.text === '累計稼働率 (%)') {
                label.pointStyle = 'circle'
                // 濃い緑を使用
                label.fillStyle = 'rgba(56, 142, 60, 1)'
                label.strokeStyle = 'rgba(56, 142, 60, 1)'
                label.lineWidth = 0
              }
            })

            return labels
          }
        }
      },
      title: {
        display: false
      },
      tooltip: {
        titleFont: {
          family: '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", "Yu Gothic", sans-serif',
          size: 14
        },
        bodyFont: {
          family: '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", "Yu Gothic", sans-serif',
          size: 14
        },
        callbacks: {
          label: (context: any) => {
            return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`
          }
        }
      }
    },
    scales: {
      x: {
        ticks: {
          font: {
            family: '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", "Yu Gothic", sans-serif',
            size: 14
          }
        }
      },
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        beginAtZero: true,
        min: 0,
        max: 100,
        ticks: {
          stepSize: 20,
          callback: (value: any) => `${value}%`,
          font: {
            family: '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", "Yu Gothic", sans-serif',
            size: 14
          }
        },
        grid: {
          display: true,
          color: 'rgba(0, 0, 0, 0.1)'
        },
        title: {
          display: true,
          text: '稼働率 (%)',
          font: {
            family: '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", "Yu Gothic", sans-serif',
            size: 14
          }
        }
      }
    }
  }), [])

  return (
    <>
      <div className={`section ${styles.chartSection}`} id="sensor-availability" data-testid="availability-chart">
        <div className={styles.sectionHeader}>
          <h2 className="title is-4">
            <span className="icon"><i className="fas fa-chart-line"></i></span>
            センサー稼働率
            <i
              className={`fas fa-link ${styles.permalinkIcon}`}
              onClick={() => copyPermalink('sensor-availability')}
              title="パーマリンクをコピー"
            />
          </h2>
        </div>
        <div className="box">
          <div style={{ position: 'relative', height: '400px', width: '100%' }}>
            <Chart type="bar" data={chartData} options={chartOptions} />
          </div>
        </div>
      </div>
      <div ref={notificationRef} className={styles.copyNotification}></div>
    </>
  )
}

export const AvailabilityChart = memo(AvailabilityChartComponent)
