import React from 'react'
import BarChart from './BarChart'

export default function RecentContentPanel({ data, onKeep, onSkip }) {
  const actionCounts = data?.action_counts || {}
  const entries = Object.entries(actionCounts)
  const ACTION_COLORS = { 'Remove/Redirect': 'var(--danger)', 'Discuss Further': 'var(--warning)', 'Review': 'var(--info)' }

  return (
    <div className="panel panel-accent slide-up">
      <div className="panel-title">Recent Content Safety Check</div>
      <p className="panel-subtitle">
        {data.total_pages} pages published since {data.cutoff_date} are currently tagged with non-Keep actions.
        Would you like to override them to "Keep"?
      </p>

      <BarChart items={entries.map(([action, count]) => ({ label: action, value: count, color: ACTION_COLORS[action] || 'var(--slate-400)' }))} />

      <div className="btn-group" style={{ marginTop: 'var(--sp-4)' }}>
        <button className="btn btn-primary btn-sm" onClick={onKeep}>Yes, Keep Recent Content</button>
        <button className="btn btn-secondary btn-sm" onClick={onSkip}>No, Leave As Is</button>
      </div>
    </div>
  )
}
