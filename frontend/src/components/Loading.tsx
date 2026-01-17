export function Loading() {
  return (
    <div className="container mt-5" data-testid="loading">
      <div className="text-center">
        <div className="spinner-border" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
      </div>
    </div>
  )
}
