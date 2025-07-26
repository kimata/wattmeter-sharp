import dayjs from 'dayjs'
import { version as reactVersion } from 'react'
import { Github } from 'react-bootstrap-icons'

interface FooterProps {
  updateTime: string
}

export function Footer({ updateTime }: FooterProps) {
  const buildDate = dayjs(import.meta.env.VITE_BUILD_DATE || new Date().toISOString())
  const imageBuildDate = import.meta.env.VITE_IMAGE_BUILD_DATE || 'Unknown'

  return (
    <div className="p-1 float-end text-end m-2 mt-4">
      <small>
        <p className="text-muted m-0">
          <small>更新日時: {updateTime}</small>
        </p>
        <p className="text-muted m-0">
          <small>
            イメージビルド: {imageBuildDate !== 'Unknown' ?
              `${dayjs(imageBuildDate).format('YYYY年MM月DD日 HH:mm:ss')} [${dayjs(imageBuildDate).fromNow()}]` :
              'Unknown'
            }
          </small>
        </p>
        <p className="text-muted m-0">
          <small>
            React ビルド: {buildDate.format('YYYY年MM月DD日 HH:mm:ss')} [{buildDate.fromNow()}]
          </small>
        </p>
        <p className="text-muted m-0">
          <small>
            React バージョン: {reactVersion}
          </small>
        </p>
        <p className="display-6">
          <a
            href="https://github.com/kimata/wattmeter-sharp"
            className="text-secondary"
          >
            <Github />
          </a>
        </p>
      </small>
    </div>
  )
}
