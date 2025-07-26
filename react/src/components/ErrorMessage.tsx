interface ErrorMessageProps {
  error: string
}

export function ErrorMessage({ error }: ErrorMessageProps) {
  return (
    <div className="container mt-5">
      <div className="alert alert-danger" role="alert">
        エラー: {error}
      </div>
    </div>
  )
}
