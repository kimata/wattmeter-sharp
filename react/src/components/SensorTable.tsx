import { useState, useRef, useEffect } from 'react'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/ja'
import type { SensorData } from '../types'
import { AnimatedNumber } from './common/AnimatedNumber'
import styles from './CommunicationError.module.css'

dayjs.extend(relativeTime)
dayjs.locale('ja')

interface SensorTableProps {
  sensors: SensorData[]
}

type SortKey = 'index' | 'name' | 'availability_total' | 'availability_24h' | 'last_received' | 'status' | 'power_consumption'
type SortDirection = 'asc' | 'desc'

export function SensorTable({ sensors }: SensorTableProps) {
  const [sortKey, setSortKey] = useState<SortKey | null>(null)
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc')
  const notificationRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // ページ読み込み時にハッシュがあれば該当要素にスクロール
    if (window.location.hash === '#sensor-details') {
      const element = document.getElementById('sensor-details')
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

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      // 状態列は降順、他の列は降順を初期値とする
      setSortDirection('desc')
    }
  }

  const getSortIcon = (key: SortKey) => {
    if (sortKey !== key) return ''
    return sortDirection === 'asc' ? ' ▲' : ' ▼'
  }

  const getStatusValue = (sensor: SensorData) => {
    if (sensor.availability_total >= 90) return 3 // 正常
    if (sensor.availability_total >= 70) return 2 // 警告
    return 1 // 異常
  }

  const sortedSensors = sortKey ? [...sensors].sort((a, b) => {
    let aValue: any
    let bValue: any

    switch (sortKey) {
      case 'index':
        aValue = sensors.indexOf(a)
        bValue = sensors.indexOf(b)
        break
      case 'name':
        aValue = a.name
        bValue = b.name
        break
      case 'availability_total':
        aValue = a.availability_total
        bValue = b.availability_total
        break
      case 'availability_24h':
        aValue = a.availability_24h
        bValue = b.availability_24h
        break
      case 'last_received':
        aValue = a.last_received ? dayjs(a.last_received).valueOf() : 0
        bValue = b.last_received ? dayjs(b.last_received).valueOf() : 0
        break
      case 'status':
        aValue = getStatusValue(a)
        bValue = getStatusValue(b)
        break
      case 'power_consumption':
        aValue = a.power_consumption ?? 0
        bValue = b.power_consumption ?? 0
        break
      default:
        return 0
    }

    if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1
    if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1
    return 0
  }) : sensors

  const getRelativeTime = (dateString: string | null) => {
    if (!dateString) return ''
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


  return (
    <>
      <div className={`section ${styles.errorTableSection}`} id="sensor-details" data-testid="sensor-table">
        <div className={styles.sectionHeader}>
          <h2 className="title is-4">
            <span className={styles.icon}>🔧</span>
            センサー詳細
            <i
              className={`fas fa-link ${styles.permalinkIcon}`}
              onClick={() => copyPermalink('sensor-details')}
              title="パーマリンクをコピー"
            />
          </h2>
        </div>
        <div className="table-container">
          <table className="table is-striped is-hoverable is-fullwidth" data-testid="sensors-table">
            <thead>
              <tr>
                <th
                  onClick={() => handleSort('index')}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                >
                  # {getSortIcon('index')}
                </th>
                <th
                  onClick={() => handleSort('name')}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                >
                  センサー名 {getSortIcon('name')}
                </th>
                <th
                  onClick={() => handleSort('availability_total')}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                >
                  累計稼働率 {getSortIcon('availability_total')}
                </th>
                <th
                  onClick={() => handleSort('availability_24h')}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                >
                  過去24時間 {getSortIcon('availability_24h')}
                </th>
                <th
                  onClick={() => handleSort('power_consumption')}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                >
                  消費電力 {getSortIcon('power_consumption')}
                </th>
                <th
                  onClick={() => handleSort('last_received')}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                >
                  最終受信 {getSortIcon('last_received')}
                </th>
                <th
                  onClick={() => handleSort('status')}
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                >
                  状態{getSortIcon('status')}
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedSensors.map((sensor, index) => (
                <tr key={`${sensor.name}-${index}`}>
                  <td>{sortKey === 'index' ? sensors.indexOf(sensor) + 1 : index + 1}</td>
                  <td>{sensor.name}</td>
                  <td>
                    <div className="is-flex is-align-items-center">
                      <progress
                        className="progress mr-3"
                        value={sensor.availability_total}
                        max="100"
                        style={{ height: '20px', width: '100px', backgroundColor: '#f8f8f8' }}
                      >
                        {sensor.availability_total}%
                      </progress>
                      <span className="has-text-right" style={{ width: '60px', textAlign: 'right', display: 'inline-block' }}>
                        <AnimatedNumber value={sensor.availability_total} decimals={1} />%
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="is-flex is-align-items-center">
                      <progress
                        className="progress mr-3"
                        value={sensor.availability_24h}
                        max="100"
                        style={{ height: '20px', width: '100px', backgroundColor: '#f8f8f8' }}
                      >
                        {sensor.availability_24h}%
                      </progress>
                      <span className="has-text-right" style={{ width: '60px', textAlign: 'right', display: 'inline-block' }}>
                        <AnimatedNumber value={sensor.availability_24h} decimals={1} />%
                      </span>
                    </div>
                  </td>
                  <td className="has-text-right">
                    {sensor.power_consumption !== null ? (
                      <>
                        <AnimatedNumber value={sensor.power_consumption} decimals={0} useComma={true} /> W
                      </>
                    ) : (
                      'N/A'
                    )}
                  </td>
                  <td>
                    {sensor.last_received ? (
                      <>
                        {dayjs(sensor.last_received).format('M/D HH:mm:ss')}
                        <span className="has-text-grey ml-1">
                          {getRelativeTime(sensor.last_received)}
                        </span>
                      </>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td>
                    <span className={`tag ${
                      sensor.availability_total >= 90 ? 'is-success' :
                      sensor.availability_total >= 70 ? 'is-warning' :
                      'is-danger'
                    }`}>
                      {sensor.availability_total >= 90 ? '正常' :
                       sensor.availability_total >= 70 ? '警告' :
                       '異常'}
                    </span>
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
