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
    <div className="App japanese-font" data-testid="app">
      <div className="container is-fluid" style={{ padding: '0.5rem' }}>
        <section className="section" style={{ padding: '1rem 0.5rem' }}>
          <div className="container" style={{ maxWidth: '100%', padding: 0 }}>
            <h1 className="title is-2 has-text-centered" data-testid="app-title">
              <span className="icon is-large"><i className="fas fa-chart-line"></i></span>
              SHARP HEMS センサー稼働状態
            </h1>

            {data ? (
              <div className="mb-4" data-testid="data-info">
                <p className="subtitle has-text-centered">
                  データ収集開始日: {startDate!.format('YYYY年MM月DD日')} ({daysSinceStart}日前)
                </p>
              </div>
            ) : (
              <div className="mb-4">
                <div className="is-loading">
                  <span className="button is-loading is-white"></span>
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
        </section>
      </div>
      <Footer updateTime={updateTime} />
    </div>
  )
}

export default App
