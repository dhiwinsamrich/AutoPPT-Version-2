import { useEffect, useRef } from 'react'
import { clsx } from 'clsx'

type Props = {
  logs: string[]
  className?: string
}

export function LogViewer({ logs, className }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight
    }
  }, [logs])

  return (
    <div
      ref={ref}
      className={clsx(
        'rounded-xl border border-white/10 bg-white/5 p-4 text-xs font-mono text-white/80 backdrop-blur-sm transition',
        'overflow-auto whitespace-pre-wrap shadow-inner shadow-black/10',
        className
      )}
    >
      {logs.length === 0 ? (
        <div className="text-white/40">No logs yet…</div>
      ) : (
        logs.map((line, i) => <div key={i}>{line}</div>)
      )}
    </div>
  )
}


