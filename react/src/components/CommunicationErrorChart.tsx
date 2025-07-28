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
import { useRef, useEffect } from 'react'

import type { CommunicationErrorHistogram } from '../types'
import styles from './CommunicationError.module.css'

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
  const notificationRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // ページ読み込み時にハッシュがあれば該当要素にスクロール
    if (window.location.hash === '#communication-error-chart') {
      const element = document.getElementById('communication-error-chart')
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
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          font: {
            family: '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", "Yu Gothic", sans-serif',
            size: 14
          }
        }
      },
      title: {
        display: false,
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: '時間帯',
          font: {
            family: '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", "Yu Gothic", sans-serif',
            size: 14
          }
        },
        ticks: {
          maxTicksLimit: 12, // 2時間刻みで表示
          font: {
            family: '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", "Yu Gothic", sans-serif',
            size: 14
          },
          callback: function(value: string | number) {
            const index = Number(value)
            if (index % 4 === 0) {
              const label = histogram.bin_labels[index]
              if (label) {
                // "00:00", "01:30" のような形式を "0時", "1時" に変換
                const hourMatch = label.match(/^(\d{1,2}):/);
                if (hourMatch) {
                  return `${parseInt(hourMatch[1])}時`
                }
              }
              return label
            }
            return ''
          }
        }
      },
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'エラー件数',
          font: {
            family: '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", "Yu Gothic", sans-serif',
            size: 14
          }
        },
        ticks: {
          stepSize: 1,
          font: {
            family: '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", "Yu Gothic", sans-serif',
            size: 14
          }
        },
      },
    },
  }

  return (
    <>
      <div className={`section ${styles.chartSection}`} id="communication-error-chart">
        <div className={styles.sectionHeader}>
          <h2 className="title is-4">
            <span className={styles.icon}>📊</span>
            通信エラー発生状況（過去24時間、合計: {histogram.total_errors}件）
            <i
              className={`fas fa-link ${styles.permalinkIcon}`}
              onClick={() => copyPermalink('communication-error-chart')}
              title="パーマリンクをコピー"
            />
          </h2>
        </div>
        <div className="box">
          <div style={{ position: 'relative', height: '400px', width: '100%' }}>
            <Bar data={data} options={options} />
          </div>
        </div>
      </div>
      <div ref={notificationRef} className={styles.copyNotification}></div>
    </>
  )
}
