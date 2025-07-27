import type { CommunicationError } from '../types'

interface CommunicationErrorTableProps {
  errors: CommunicationError[]
}

export function CommunicationErrorTable({ errors }: CommunicationErrorTableProps) {
  if (errors.length === 0) {
    return (
      <div className="row">
        <div className="col">
          <h2 className="h4 mb-3">最新の通信エラーログ（50件）</h2>
          <p className="text-muted">通信エラーはありません。</p>
        </div>
      </div>
    )
  }

  return (
    <div className="row">
      <div className="col">
        <h2 className="h4 mb-3">最新の通信エラーログ（{errors.length}件）</h2>
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
  )
}
