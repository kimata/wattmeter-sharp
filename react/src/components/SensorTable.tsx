import { useState } from 'react'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/ja'
import type { SensorData } from '../types'

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

  const formatPowerConsumption = (power: number | null) => {
    if (power === null) return 'N/A'
    return `${power.toLocaleString()} W`
  }

  return (
    <div className="row">
      <div className="col">
        <h2 className="h4 mb-3">センサー詳細</h2>
        <div className="table-responsive">
          <table className="table table-striped table-hover">
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
                    <div className="d-flex align-items-center">
                      <div className="progress me-3" style={{ height: '20px', width: '100px' }}>
                        <div
                          className="progress-bar bg-secondary"
                          role="progressbar"
                          style={{ width: `${sensor.availability_total}%` }}
                          aria-valuenow={sensor.availability_total}
                          aria-valuemin={0}
                          aria-valuemax={100}
                        >
                        </div>
                      </div>
                      <span className="text-nowrap" style={{ width: '60px', textAlign: 'right', display: 'inline-block' }}>
                        {sensor.availability_total.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td>
                    <div className="d-flex align-items-center">
                      <div className="progress me-3" style={{ height: '20px', width: '100px' }}>
                        <div
                          className="progress-bar bg-secondary"
                          role="progressbar"
                          style={{ width: `${sensor.availability_24h}%` }}
                          aria-valuenow={sensor.availability_24h}
                          aria-valuemin={0}
                          aria-valuemax={100}
                        >
                        </div>
                      </div>
                      <span className="text-nowrap" style={{ width: '60px', textAlign: 'right', display: 'inline-block' }}>
                        {sensor.availability_24h.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className="text-end">
                    {formatPowerConsumption(sensor.power_consumption)}
                  </td>
                  <td>
                    {sensor.last_received ? (
                      <>
                        {dayjs(sensor.last_received).format('M/D HH:mm:ss')}
                        <span className="text-muted ms-1">
                          {getRelativeTime(sensor.last_received)}
                        </span>
                      </>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td>
                    <span className={`badge ${
                      sensor.availability_total >= 90 ? 'bg-success' :
                      sensor.availability_total >= 70 ? 'bg-warning' :
                      'bg-danger'
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
    </div>
  )
}
