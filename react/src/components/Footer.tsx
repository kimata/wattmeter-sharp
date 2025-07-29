import dayjs from 'dayjs'
import { version as reactVersion } from 'react'
import { useApi } from '../hooks/useApi'
import type { SysInfo } from '../types'

interface FooterProps {
  updateTime: string
}

export function Footer({ updateTime }: FooterProps) {
  const buildDate = dayjs(import.meta.env.VITE_BUILD_DATE || new Date().toISOString())
  const { data: sysInfo } = useApi<SysInfo>('/wattmeter-sharp/api/sysinfo', { interval: 300000 }) // 5分間隔で更新

  const getImageBuildDate = () => {
    if (!sysInfo?.image_build_date) return 'Unknown'
    const buildDate = dayjs(sysInfo.image_build_date)
    return `${buildDate.format('YYYY年MM月DD日 HH:mm:ss')} [${buildDate.fromNow()}]`
  }

  return (
    <div className="is-pulled-right has-text-right p-2 mt-4" data-testid="footer">
      <div className="is-size-6">
        <p className="has-text-grey mb-0 is-size-7">
          更新日時: {updateTime}
        </p>
        <p className="has-text-grey mb-0 is-size-7">
          イメージビルド: {getImageBuildDate()}
        </p>
        <p className="has-text-grey mb-0 is-size-7">
          React ビルド: {buildDate.format('YYYY年MM月DD日 HH:mm:ss')} [{buildDate.fromNow()}]
        </p>
        <p className="has-text-grey mb-0 is-size-7">
          React バージョン: {reactVersion}
        </p>
        <p className="is-size-2">
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
