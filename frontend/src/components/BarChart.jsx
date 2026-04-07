import React from 'react'

/** Simple horizontal bar chart. items: [{label, value, color?}] */
export default function BarChart({ items, maxValue }) {
  if (!items || items.length === 0) return null
  const max = maxValue || Math.max(...items.map(i => i.value), 1)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, margin: 'var(--sp-3) 0' }}>
      {items.map((item, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', minWidth: 100, textAlign: 'right' }}>
            {item.label}
          </span>
          <div style={{ flex: 1, background: 'var(--slate-100)', borderRadius: 3, height: 18, overflow: 'hidden' }}>
            <div style={{
              width: `${Math.max((item.value / max) * 100, 1)}%`,
              height: '100%',
              background: item.color || 'var(--accent)',
              borderRadius: 3,
              transition: 'width 600ms ease',
              display: 'flex',
              alignItems: 'center',
              paddingLeft: 6,
            }}>
              <span style={{ fontSize: '0.68rem', fontWeight: 600, color: '#fff', whiteSpace: 'nowrap' }}>
                {item.value.toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
