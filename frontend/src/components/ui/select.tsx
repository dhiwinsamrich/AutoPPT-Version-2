import { useEffect, useMemo, useRef, useState } from 'react'
import { clsx } from 'clsx'

type Option = { label: string; value: string }

type Props = {
  options: Option[]
  value?: string
  onChange?: (e: { target: { value: string } }) => void
  className?: string
  placeholder?: string
}

export function Select({ options, value, onChange, className, placeholder }: Props) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const selected = useMemo(() => options.find(o => o.value === value), [options, value])
  const [highlightIndex, setHighlightIndex] = useState<number>(() => Math.max(0, options.findIndex(o => o.value === value)))

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!containerRef.current) return
      if (containerRef.current.contains(e.target as Node)) return
      setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [])

  return (
    <div ref={containerRef} className={clsx('relative', className)}>
      <button
        type="button"
        className="flex w-full items-center justify-between rounded-xl border border-white/12 bg-black/70 px-3 py-2 text-sm text-white transition hover:border-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/25"
        onClick={() => {
          setOpen(v => !v)
          setHighlightIndex(Math.max(0, options.findIndex(o => o.value === value)))
        }}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setOpen(true)
            setTimeout(() => listRef.current?.focus(), 0)
          }
        }}
      >
        <span className={clsx('truncate text-left', selected ? 'text-white' : 'text-white/50')}>
          {selected ? selected.label : (placeholder || 'Select')}
        </span>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          className={clsx('text-white/70 transition-transform', open ? 'rotate-180' : '')}
        >
          <path d="M7 10l5 5 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <div className="absolute z-50 mt-2 w-full origin-top overflow-hidden rounded-xl border border-white/12 bg-black/95 shadow-xl shadow-black/40 backdrop-blur transition-all duration-150 ease-out">
          <ul
            ref={listRef}
            tabIndex={0}
            className="max-h-64 overflow-auto py-1 outline-none"
            onKeyDown={(e) => {
              if (e.key === 'Escape') { e.preventDefault(); setOpen(false); return }
              if (e.key === 'ArrowDown') { e.preventDefault(); setHighlightIndex(i => Math.min(options.length - 1, i + 1)); return }
              if (e.key === 'ArrowUp') { e.preventDefault(); setHighlightIndex(i => Math.max(0, i - 1)); return }
              if (e.key === 'Enter') {
                e.preventDefault();
                const opt = options[highlightIndex]
                if (opt) { onChange?.({ target: { value: opt.value } }); setOpen(false) }
              }
            }}
          >
            {options.map((opt, idx) => {
              const active = opt.value === value
              const highlighted = idx === highlightIndex
              return (
                <li key={opt.value}>
                  <button
                    type="button"
                    className={clsx(
                      'relative w-full px-3 py-2 text-left text-sm transition-colors duration-150',
                      highlighted ? 'bg-white/10 text-white' : 'hover:bg-white/10 text-white/80',
                      active && 'text-white font-medium'
                    )}
                    onMouseEnter={() => setHighlightIndex(idx)}
                    onClick={() => {
                      onChange?.({ target: { value: opt.value } })
                      setOpen(false)
                    }}
                  >
                    {opt.label}
                  </button>
                  {idx < options.length - 1 && <div className="h-px w-full bg-white/5" />}
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}


