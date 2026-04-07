import React, { useEffect, useRef, useState } from 'react'

const TYPE_STYLE = {
  info: { symbol: '\u2022', color: 'var(--text-muted)' },
  success: { symbol: '\u2713', color: 'var(--success)' },
  error: { symbol: '\u2717', color: 'var(--danger)' },
  heading: { symbol: '', color: 'var(--text-primary)' },
}

export default function LogPanel({ logs, onClear, logEndRef }) {
  const containerRef = useRef(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    if (containerRef.current) containerRef.current.scrollTop = containerRef.current.scrollHeight
  }, [logs])

  if (logs.length === 0) return null

  const lastLog = logs[logs.length - 1]
  const errorCount = logs.filter(l => l.type === 'error').length

  return (
    <div className="panel slide-up" style={{ marginTop: 'var(--sp-8)', padding: 0, overflow: 'hidden' }}>
      {/* Collapsed header — always shows last message */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: 'var(--sp-3) var(--sp-4)', cursor: 'pointer',
          background: 'var(--bg-surface)', borderBottom: expanded ? '1px solid var(--border-default)' : 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', minWidth: 0, flex: 1 }}>
          <span style={{
            fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-muted)',
            textTransform: 'uppercase', letterSpacing: '0.06em', flexShrink: 0,
          }}>
            Activity
          </span>
          {!expanded && (
            <span style={{ fontSize: '0.78rem', color: lastLog.type === 'error' ? 'var(--danger)' : 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {lastLog.message}
            </span>
          )}
          {errorCount > 0 && (
            <span style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--danger)', background: 'var(--danger-bg)', padding: '1px 6px', borderRadius: 10, flexShrink: 0 }}>
              {errorCount} error{errorCount > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', flexShrink: 0 }}>
          {expanded && <button className="btn-back" onClick={(e) => { e.stopPropagation(); onClear() }} style={{ fontSize: '0.72rem' }}>Clear</button>}
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{expanded ? 'Collapse' : `${logs.length} entries`}</span>
        </div>
      </div>
      {/* Expanded body */}
      {expanded && (
        <div ref={containerRef} style={{ padding: 'var(--sp-3) var(--sp-4)', maxHeight: 200, overflowY: 'auto' }}>
          {logs.map((log) => {
            const cfg = TYPE_STYLE[log.type] || TYPE_STYLE.info
            const isH = log.type === 'heading'
            return (
              <div key={log.id} style={{
                display: 'flex', gap: 'var(--sp-2)', padding: '1px 0', alignItems: 'baseline',
                fontSize: isH ? '0.8rem' : '0.75rem', fontWeight: isH ? 600 : 400, color: cfg.color,
              }}>
                {!isH && <span style={{ color: cfg.color, flexShrink: 0, width: 10, textAlign: 'center' }}>{cfg.symbol}</span>}
                <span style={{ wordBreak: 'break-word' }}>{log.message}</span>
              </div>
            )
          })}
          <div ref={logEndRef} />
        </div>
      )}
    </div>
  )
}
