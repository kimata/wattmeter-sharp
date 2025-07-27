import { useRef, useEffect } from 'react'
import type { CommunicationError } from '../types'
import styles from './CommunicationError.module.css'

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
  if (errors.length === 0) {
    return (
      <>
        <div className={`row ${styles.errorTableSection}`} id="communication-error-log">
          <div className="col">
            <div className={styles.sectionHeader}>
              <h2 className="h4 mb-0">
                <span className={styles.icon}>📋</span>
                最新の通信エラーログ（50件）
                <i
                  className={`fas fa-link ${styles.permalinkIcon}`}
                  onClick={() => copyPermalink('communication-error-log')}
                  title="パーマリンクをコピー"
                />
              </h2>
            </div>
            <p className="text-muted">通信エラーはありません。</p>
          </div>
        </div>
        <div ref={notificationRef} className={styles.copyNotification}></div>
      </>
    )
  }

  return (
    <>
      <div className={`row ${styles.errorTableSection}`} id="communication-error-log">
        <div className="col">
          <div className={styles.sectionHeader}>
            <h2 className="h4 mb-0">
              <span className={styles.icon}>📋</span>
              最新の通信エラーログ（{errors.length}件）
              <i
                className={`fas fa-link ${styles.permalinkIcon}`}
                onClick={() => copyPermalink('communication-error-log')}
                title="パーマリンクをコピー"
              />
            </h2>
          </div>
          <div className="table-responsive">
            <table className="table table-striped table-hover">
              <thead>
                <tr>
                  <th scope="col">日時</th>
                  <th scope="col">センサー名</th>
                </tr>
              </thead>
              <tbody>
                {errors.map((error, index) => (
                  <tr key={`${error.sensor_name}-${error.timestamp}-${index}`}>
                    <td>
                      <span className="font-monospace">{error.datetime}</span>
                    </td>
                    <td>
                      <span className="badge bg-danger">{error.sensor_name}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div ref={notificationRef} className={styles.copyNotification}></div>
    </>
  )
}
