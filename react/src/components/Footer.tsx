import dayjs from 'dayjs'
import { version as reactVersion } from 'react'

interface FooterProps {
  updateTime: string
}

export function Footer({ updateTime }: FooterProps) {
  const buildDate = dayjs(import.meta.env.VITE_BUILD_DATE || new Date().toISOString())
  const imageBuildDate = import.meta.env.VITE_IMAGE_BUILD_DATE || 'Unknown'

  return (
    <div className="is-pulled-right has-text-right p-2 mt-4" data-testid="footer">
      <div className="is-size-7">
        <p className="has-text-grey mb-0">
          <small>更新日時: {updateTime}</small>
        </p>
        <p className="has-text-grey mb-0">
          <small>
            イメージビルド: {imageBuildDate !== 'Unknown' ?
              `${dayjs(imageBuildDate).format('YYYY年MM月DD日 HH:mm:ss')} [${dayjs(imageBuildDate).fromNow()}]` :
              'Unknown'
            }
          </small>
        </p>
        <p className="has-text-grey mb-0">
          <small>
            React ビルド: {buildDate.format('YYYY年MM月DD日 HH:mm:ss')} [{buildDate.fromNow()}]
          </small>
        </p>
        <p className="has-text-grey mb-0">
          <small>
            React バージョン: {reactVersion}
          </small>
        </p>
        <p className="is-size-4">
          <a
            href="https://github.com/kimata/wattmeter-sharp"
            className="has-text-grey-light"
          >
            <i className="fab fa-github"></i>
          </a>
        </p>
      </div>
    </div>
  )
}
