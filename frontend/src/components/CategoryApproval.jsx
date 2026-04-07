import React, { useState } from 'react'
import ProgressBar from './ProgressBar'

export default function CategoryApproval({ data, onApprove, onReject, onApproveAll }) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [decisions, setDecisions] = useState({})
  const keys = data?.keys || []
  const recommendations = data?.recommendations || {}
  const currentKey = keys[currentIndex]
  const current = recommendations[currentKey]
  const isFinished = currentIndex >= keys.length
  const advance = () => setCurrentIndex(prev => prev + 1)

  const handleApprove = () => { setDecisions(prev => ({ ...prev, [currentKey]: 'approved' })); onApprove(currentKey); advance() }
  const handleReject = () => { setDecisions(prev => ({ ...prev, [currentKey]: 'manual_check' })); onReject(currentKey); advance() }
  const handleApproveAll = () => {
    const remaining = {}
    for (let i = currentIndex; i < keys.length; i++) remaining[keys[i]] = 'approved'
    setDecisions(prev => ({ ...prev, ...remaining }))
    onApproveAll()
    setCurrentIndex(keys.length)
  }

  if (isFinished || !current) {
    const approved = Object.values(decisions).filter(d => d === 'approved').length
    const flagged = Object.values(decisions).filter(d => d === 'manual_check').length
    return (
      <div className="panel panel-success slide-up">
        <div className="panel-title">Categories Reviewed</div>
        <p style={{ fontSize: '0.87rem', color: 'var(--text-secondary)', marginBottom: 'var(--sp-3)' }}>
          {approved} approved, {flagged} flagged for manual review.
        </p>
        <button className="btn btn-primary btn-sm" onClick={onApproveAll}>Finalize and Apply Categories</button>
      </div>
    )
  }

  return (
    <div className="panel panel-info slide-up">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--sp-2)' }}>
        <div className="panel-title">Page Category Review</div>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{currentIndex + 1} of {keys.length}</span>
      </div>

      <ProgressBar value={currentIndex + 1} max={keys.length} />

      <div className="stat-box" style={{ marginTop: 'var(--sp-3)' }}>
        <div className="stat-row"><span className="stat-label">Pattern</span><span className="stat-value" style={{ fontFamily: 'var(--font-mono)' }}>/{current.pattern_value}</span></div>
        <div className="stat-row"><span className="stat-label">Type</span><span className="stat-value">{current.pattern_type === 'subdomain' ? 'Subdomain' : 'Path segment'}</span></div>
        <div className="stat-row"><span className="stat-label">Suggested category</span><span className="stat-value" style={{ color: 'var(--accent)' }}>{current.suggested_category}</span></div>
        <div className="stat-row"><span className="stat-label">Matching URLs</span><span className="stat-value">{current.url_count}</span></div>
      </div>

      {current.example_urls?.length > 0 && (
        <div style={{ margin: 'var(--sp-3) 0' }}>
          <div className="input-label">Example URLs</div>
          {current.example_urls.map((url, i) => <code key={i} className="url-example">{url}</code>)}
        </div>
      )}

      <div className="btn-group" style={{ marginTop: 'var(--sp-4)' }}>
        <button className="btn btn-primary btn-sm" onClick={handleApprove}>Approve</button>
        <button className="btn btn-secondary btn-sm" onClick={handleReject}>Manual Check</button>
        <button className="btn btn-ghost btn-sm" onClick={handleApproveAll}>Approve All Remaining</button>
      </div>
    </div>
  )
}
