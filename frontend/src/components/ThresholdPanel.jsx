import React, { useState, useEffect } from 'react'
import Scorecard, { ScorecardsGrid } from './Scorecard'
import ProgressBar from './ProgressBar'
import * as api from '../api/client'

export default function ThresholdPanel({ data, domain, onApply, onSkip }) {
  const [thresholdType, setThresholdType] = useState('percentage')
  const [value, setValue] = useState(10)
  const [preview, setPreview] = useState(null)
  const stats = data?.stats || {}
  const pctPreview = data?.percentile_preview || {}

  // Live preview when value changes
  useEffect(() => {
    if (!domain || !data?.metric) return
    const timer = setTimeout(async () => {
      try {
        const res = await api.previewThreshold(domain, thresholdType, value)
        setPreview(res)
      } catch(e) { /* ignore */ }
    }, 300)
    return () => clearTimeout(timer)
  }, [domain, thresholdType, value, data?.metric])

  return (
    <div className="panel panel-warning slide-up">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--sp-2)' }}>
        <div className="panel-title">Set Threshold: {data.metric}</div>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Metric {(data.metric_index || 0) + 1} of {data.total_metrics || 1}</span>
      </div>

      <p className="panel-subtitle">Pages meeting the threshold will be marked as "Keep" with a Nexus Note.</p>

      <ProgressBar value={(data.metric_index || 0) + 1} max={data.total_metrics || 1} />

      <ScorecardsGrid>
        <Scorecard label="Unmarked pages" value={data.unmarked_count?.toLocaleString() || '0'} />
        <Scorecard label="Highest" value={stats.max?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || '0'} />
        <Scorecard label="75th percentile" value={stats.p75?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || '0'} />
        <Scorecard label="Non-zero" value={stats.non_zero_count?.toLocaleString() || '0'} />
      </ScorecardsGrid>

      {/* Percentile quick reference */}
      {Object.keys(pctPreview).length > 0 && (
        <div style={{ margin: 'var(--sp-3) 0' }}>
          <div className="input-label">Quick reference</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 4, fontSize: '0.75rem' }}>
            {Object.entries(pctPreview).map(([pct, info]) => (
              <div key={pct} style={{ padding: '4px 8px', background: 'var(--bg-surface)', borderRadius: 'var(--r-sm)', border: '1px solid var(--border-default)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Top {pct}%</span>
                <span style={{ float: 'right', fontWeight: 600 }}>{info.keep_count} pages</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="input-group" style={{ marginTop: 'var(--sp-4)' }}>
        <div className="input-label">Threshold type</div>
        <div className="radio-group">
          <label className="radio-row"><input type="radio" name="tt" value="percentage" checked={thresholdType === 'percentage'} onChange={() => setThresholdType('percentage')} /><span>Percentage — keep top X%</span></label>
          <label className="radio-row"><input type="radio" name="tt" value="absolute" checked={thresholdType === 'absolute'} onChange={() => setThresholdType('absolute')} /><span>Absolute value — keep pages with value at or above X</span></label>
        </div>
      </div>

      <div className="input-group">
        <div className="input-label">{thresholdType === 'percentage' ? 'Keep top X%' : 'Minimum value'}</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-3)' }}>
          <input type="number" className="input-field" value={value} onChange={(e) => setValue(parseFloat(e.target.value) || 0)} min={0} step={thresholdType === 'percentage' ? 1 : 1} style={{ maxWidth: 140 }} />
          {/* Live preview */}
          {preview && (
            <span style={{ fontSize: '0.82rem', color: 'var(--accent)', fontWeight: 600 }}>
              {preview.keep_count} pages will be marked Keep
              {preview.actual_threshold > 0 && <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}> (threshold: {preview.actual_threshold.toLocaleString(undefined, {maximumFractionDigits: 1})})</span>}
            </span>
          )}
        </div>
      </div>

      <div className="btn-group" style={{ marginTop: 'var(--sp-4)' }}>
        <button className="btn btn-primary btn-sm" onClick={() => onApply(thresholdType, value)}>Apply Threshold</button>
        <button className="btn btn-secondary btn-sm" onClick={onSkip}>Skip Metric</button>
      </div>
    </div>
  )
}
