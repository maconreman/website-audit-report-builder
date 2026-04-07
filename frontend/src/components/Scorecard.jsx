import React from 'react'

export default function Scorecard({ label, value, sub }) {
  return (
    <div className="scorecard">
      <div className="scorecard-label">{label}</div>
      <div className="scorecard-value">{value}</div>
      {sub && <div className="scorecard-sub">{sub}</div>}
    </div>
  )
}

export function ScorecardsGrid({ children }) {
  return <div className="scorecard-grid">{children}</div>
}
