import React from 'react'

export default function ProgressBar({ value, max, label }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div style={{ margin: 'var(--sp-2) 0' }}>
      {label && <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: 2 }}>{label}</div>}
      <div className="progress-bar-wrap">
        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
