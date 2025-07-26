import { useState, useEffect } from 'react'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import localizedFormat from 'dayjs/plugin/localizedFormat'
import 'dayjs/locale/ja'
import './App.css'

import type { ApiResponse } from './types'
import { useApi } from './hooks/useApi'
import { Loading } from './components/Loading'
import { ErrorMessage } from './components/ErrorMessage'
import { AvailabilityChart } from './components/AvailabilityChart'
import { SensorTable } from './components/SensorTable'
import { Footer } from './components/Footer'

dayjs.extend(relativeTime)
dayjs.extend(localizedFormat)
dayjs.locale('ja')

function App() {
  const [updateTime, setUpdateTime] = useState(dayjs().format('YYYY年MM月DD日 HH:mm:ss'))
  const { data, loading, error } = useApi<ApiResponse>('/wattmeter-sharp/api/sensor_stat', { interval: 60000 })

  useEffect(() => {
    if (data) {
      setUpdateTime(dayjs().format('YYYY年MM月DD日 HH:mm:ss'))
    }
  }, [data])

  if (loading) return <Loading />
  if (error) return <ErrorMessage error={error} />
  if (!data) return null

  const startDate = dayjs(data.start_date)
  const daysSinceStart = dayjs().diff(startDate, 'day')

  return (
    <div className="App">
      <div className="container mt-3">
        <h1 className="mb-4">SHARP HEMS センサー稼働状態</h1>

        <div className="mb-4">
          <p className="text-muted">
            データ収集開始日: {startDate.format('YYYY年MM月DD日')} ({daysSinceStart}日前)
          </p>
        </div>

        <AvailabilityChart sensors={data.sensors} />
        <SensorTable sensors={data.sensors} />
      </div>
      <Footer updateTime={updateTime} />
    </div>
  )
}

export default App
