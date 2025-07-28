import styles from './CommunicationError.module.css'

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
    <div className={`section ${styles.chartSection}`} data-testid="skeleton-chart">
      <div className={styles.sectionHeader}>
        <h2 className="title is-4">
          <span className="icon"><i className="fas fa-chart-line"></i></span>
          センサー稼働率
        </h2>
      </div>
      <div className="box">
        <div style={{ position: 'relative', height: '400px', width: '100%' }}>
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

export function SkeletonErrorChart() {
  return (
    <div className={`section ${styles.chartSection}`} data-testid="skeleton-error-chart">
      <div className={styles.sectionHeader}>
        <h2 className="title is-4">
          <span className="icon"><i className="fas fa-chart-bar"></i></span>
          通信エラー発生状況
        </h2>
      </div>
      <div className="box">
        <div style={{ position: 'relative', height: '400px', width: '100%' }}>
          <div className="is-flex is-justify-content-space-between is-align-items-end" style={{ height: '100%' }}>
            {Array.from({ length: 12 }, (_, i) => (
              <div key={i} className="is-flex is-flex-direction-column is-align-items-center">
                <Skeleton
                  height={`${30 + Math.random() * 60}px`}
                  width="20px"
                  className="mb-2"
                />
                <Skeleton height="12px" width="30px" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export function SkeletonErrorTable() {
  return (
    <div className={`section ${styles.errorTableSection}`} data-testid="skeleton-error-table">
      <div className={styles.sectionHeader}>
        <h2 className="title is-4">
          <span className="icon"><i className="fas fa-list"></i></span>
          最新の通信エラー
        </h2>
      </div>
      <div className="table-container">
        <table className="table is-striped is-hoverable is-fullwidth">
          <thead>
            <tr>
              <th>センサー名</th>
              <th>発生日時</th>
              <th>エラー種別</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: 5 }, (_, i) => (
              <tr key={i}>
                <td><Skeleton height="20px" width="120px" /></td>
                <td><Skeleton height="20px" width="140px" /></td>
                <td><Skeleton height="20px" width="100px" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function SkeletonTable() {
  return (
    <div className={`section ${styles.errorTableSection}`} data-testid="skeleton-table">
      <div className={styles.sectionHeader}>
        <h2 className="title is-4">
          <span className="icon"><i className="fas fa-cog"></i></span>
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
