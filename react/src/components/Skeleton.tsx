interface SkeletonProps {
  className?: string
  height?: string
  width?: string
}

export function Skeleton({ className = '', height = '20px', width = '100%' }: SkeletonProps) {
  return (
    <div
      className={`placeholder-glow ${className}`}
      style={{ height, width }}
    >
      <span className="placeholder w-100 h-100 rounded"></span>
    </div>
  )
}

export function SkeletonChart() {
  return (
    <div className="row mb-5" data-testid="skeleton-chart">
      <div className="col">
        <div className="border rounded p-3">
          <div className="mb-3">
            <Skeleton height="24px" width="200px" className="mx-auto" />
          </div>
          <div className="d-flex justify-content-between align-items-end" style={{ height: '300px' }}>
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i} className="d-flex flex-column align-items-center">
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
    <div className="row" data-testid="skeleton-table">
      <div className="col">
        <h2 className="h4 mb-3">センサー詳細</h2>
        <div className="table-responsive">
          <table className="table table-striped">
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
                    <div className="d-flex align-items-center">
                      <Skeleton height="20px" width="100px" className="me-3" />
                      <Skeleton height="20px" width="60px" />
                    </div>
                  </td>
                  <td>
                    <div className="d-flex align-items-center">
                      <Skeleton height="20px" width="100px" className="me-3" />
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
    </div>
  )
}
