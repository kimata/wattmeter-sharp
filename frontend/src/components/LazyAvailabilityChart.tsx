import { lazy, Suspense } from 'react'
import type { SensorData } from '../types'
import { SkeletonChart } from './Skeleton'

const AvailabilityChart = lazy(() =>
  import('./AvailabilityChart').then(module => ({
    default: module.AvailabilityChart
  }))
)

interface LazyAvailabilityChartProps {
  sensors: SensorData[]
}

export function LazyAvailabilityChart({ sensors }: LazyAvailabilityChartProps) {
  return (
    <Suspense fallback={<SkeletonChart />}>
      <AvailabilityChart sensors={sensors} />
    </Suspense>
  )
}
