interface SkeletonProps {
  className?: string
  height?: string
  width?: string
}

export function Skeleton({ className = '', height = '20px', width = '100%' }: SkeletonProps) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{
        height,
        width,
        backgroundColor: '#e8e8e8',
        borderRadius: '4px',
        animation: 'skeleton-loading 1.5s infinite ease-in-out',
        backgroundImage: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)',
        backgroundSize: '200px 100%',
        backgroundRepeat: 'no-repeat'
      }}
    >
    </div>
  )
}

export function SkeletonChart() {
  return (
    <div className="section" data-testid="skeleton-chart">
      <div className="sectionHeader">
        <h2 className="title is-4">
          <span>📊</span>
          <Skeleton height="24px" width="200px" className="ml-2" />
        </h2>
      </div>
      <div className="table-container">
        <div className="chart-container" style={{ position: 'relative', height: '350px', margin: '0.5rem 0' }}>
          <div className="is-flex is-justify-content-space-between is-align-items-end" style={{ height: '100%' }}>
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i} className="is-flex is-flex-direction-column is-align-items-center">
                <Skeleton
                  height={`${120 + Math.random() * 100}px`}
                  width="40px"
                  className="mb-2"
                />
                <Skeleton height="16px" width="60px" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export function SkeletonTable() {
  return (
    <div className="section" data-testid="skeleton-table">
      <div className="sectionHeader">
        <h2 className="title is-4">
          <span>🔧</span>
          センサー詳細
        </h2>
      </div>
      <div className="table-container">
        <table className="table is-striped is-hoverable is-fullwidth">
          <thead>
            <tr>
              <th>#</th>
              <th>センサー名</th>
              <th>累計稼働率</th>
              <th>過去24時間</th>
              <th>消費電力</th>
              <th>最終受信</th>
              <th>状態</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 6 }, (_, i) => (
              <tr key={i}>
                <td>{i + 1}</td>
                <td><Skeleton height="20px" width="120px" /></td>
                <td>
                  <div className="is-flex is-align-items-center">
                    <Skeleton height="20px" width="100px" className="mr-3" />
                    <Skeleton height="20px" width="60px" />
                  </div>
                </td>
                <td>
                  <div className="is-flex is-align-items-center">
                    <Skeleton height="20px" width="100px" className="mr-3" />
                    <Skeleton height="20px" width="60px" />
                  </div>
                </td>
                <td><Skeleton height="20px" width="80px" /></td>
                <td><Skeleton height="20px" width="140px" /></td>
                <td><Skeleton height="24px" width="50px" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
