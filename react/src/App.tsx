import { useState, useEffect } from 'react'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import localizedFormat from 'dayjs/plugin/localizedFormat'
import 'dayjs/locale/ja'
import './App.css'

import type { ApiResponse, CommunicationErrorResponse } from './types'
import { useApi } from './hooks/useApi'
import { ErrorMessage } from './components/ErrorMessage'
import { LazyAvailabilityChart } from './components/LazyAvailabilityChart'
import { SensorTable } from './components/SensorTable'
import { CommunicationErrorChart } from './components/CommunicationErrorChart'
import { CommunicationErrorTable } from './components/CommunicationErrorTable'
import { Footer } from './components/Footer'
import { SkeletonChart, SkeletonTable } from './components/Skeleton'

dayjs.extend(relativeTime)
dayjs.extend(localizedFormat)
dayjs.locale('ja')

function App() {
  const [updateTime, setUpdateTime] = useState(dayjs().format('YYYY年MM月DD日 HH:mm:ss'))
  const { data, error } = useApi<ApiResponse>('/wattmeter-sharp/api/sensor_stat', { interval: 60000 })
  const { data: errorData, error: errorApiError } = useApi<CommunicationErrorResponse>('/wattmeter-sharp/api/communication_errors', { interval: 60000 })

  useEffect(() => {
    if (data) {
      setUpdateTime(dayjs().format('YYYY年MM月DD日 HH:mm:ss'))
    }
  }, [data])

  if (error) return <ErrorMessage error={error} />
  if (errorApiError) return <ErrorMessage error={errorApiError} />

  const startDate = data ? dayjs(data.start_date) : null
  const daysSinceStart = startDate ? dayjs().diff(startDate, 'day') : 0

  return (
    <div className="App" data-testid="app">
      <div className="container mt-3">
        <h1 className="mb-4" data-testid="app-title">SHARP HEMS センサー稼働状態</h1>

        {data ? (
          <div className="mb-4" data-testid="data-info">
            <p className="text-muted">
              データ収集開始日: {startDate!.format('YYYY年MM月DD日')} ({daysSinceStart}日前)
            </p>
          </div>
        ) : (
          <div className="mb-4">
            <div className="placeholder-glow">
              <span className="placeholder col-4"></span>
            </div>
          </div>
        )}

        {data ? (
          <LazyAvailabilityChart sensors={data.sensors} />
        ) : (
          <SkeletonChart />
        )}

        {data ? (
          <SensorTable sensors={data.sensors} />
        ) : (
          <SkeletonTable />
        )}

        {errorData ? (
          <CommunicationErrorChart histogram={errorData.histogram} />
        ) : (
          <SkeletonChart />
        )}

        {errorData ? (
          <CommunicationErrorTable errors={errorData.latest_errors} />
        ) : (
          <SkeletonTable />
        )}
      </div>
      <Footer updateTime={updateTime} />
    </div>
  )
}

export default App
