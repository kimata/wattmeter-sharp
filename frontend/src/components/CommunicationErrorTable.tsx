import { useRef, useEffect } from 'react'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/ja'
import type { CommunicationError } from '../types'
import styles from './CommunicationError.module.css'

dayjs.extend(relativeTime)
dayjs.locale('ja')

interface CommunicationErrorTableProps {
  errors: CommunicationError[]
}

export function CommunicationErrorTable({ errors }: CommunicationErrorTableProps) {
  const notificationRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // ページ読み込み時にハッシュがあれば該当要素にスクロール
    if (window.location.hash === '#communication-error-log') {
      const element = document.getElementById('communication-error-log')
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

  const getRelativeTime = (dateString: string) => {
    const date = dayjs(dateString)
    const now = dayjs()
    const diffMinutes = now.diff(date, 'minute')

    if (diffMinutes < 60) {
      return `(${diffMinutes}分前)`
    } else if (diffMinutes < 1440) {
      const hours = Math.floor(diffMinutes / 60)
      return `(${hours}時間前)`
    } else {
      const days = Math.floor(diffMinutes / 1440)
      return `(${days}日前)`
    }
  }
  if (errors.length === 0) {
    return (
      <>
        <div className={`section ${styles.errorTableSection}`} id="communication-error-log">
          <div className={styles.sectionHeader}>
            <h2 className="title is-4">
              <span className="icon"><i className="fas fa-list"></i></span>
              最新の通信エラーログ（50件）
              <i
                className={`fas fa-link ${styles.permalinkIcon}`}
                onClick={() => copyPermalink('communication-error-log')}
                title="パーマリンクをコピー"
              />
            </h2>
          </div>
          <p className="has-text-grey">通信エラーはありません。</p>
        </div>
        <div ref={notificationRef} className={styles.copyNotification}></div>
      </>
    )
  }

  return (
    <>
      <div className={`section ${styles.errorTableSection}`} id="communication-error-log">
        <div className={styles.sectionHeader}>
          <h2 className="title is-4">
            <span className="icon"><i className="fas fa-list"></i></span>
            最新の通信エラーログ（{errors.length}件）
            <i
              className={`fas fa-link ${styles.permalinkIcon}`}
              onClick={() => copyPermalink('communication-error-log')}
              title="パーマリンクをコピー"
            />
          </h2>
        </div>
        <div className="table-container">
          <table className="table is-striped is-hoverable is-fullwidth">
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>日時</th>
                <th style={{ textAlign: 'left' }}>センサー名</th>
              </tr>
            </thead>
            <tbody>
              {errors.map((error, index) => (
                <tr key={`${error.sensor_name}-${error.timestamp}-${index}`}>
                  <td style={{ textAlign: 'left' }}>
                    {dayjs(error.datetime).format('M/D HH:mm:ss')}
                    <span className="has-text-grey ml-1">
                      {getRelativeTime(error.datetime)}
                    </span>
                  </td>
                  <td style={{ textAlign: 'left' }}>
                    {error.sensor_name}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div ref={notificationRef} className={styles.copyNotification}></div>
    </>
  )
}
