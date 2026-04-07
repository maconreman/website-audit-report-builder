import React, { useState } from 'react'

export default function OldContentPanel({ options, onConfirm }) {
  const [enabled, setEnabled] = useState(false)
  const [cutoffYear, setCutoffYear] = useState(2020)
  const dateFields = []
  if (options?.has_date_published) dateFields.push('Date Published')
  if (options?.has_date_modified) dateFields.push('Date Modified')
  const [dateField, setDateField] = useState(dateFields[0] || 'Date Published')

  return (
    <div className="panel panel-info slide-up">
      <div className="panel-title">Old Content Check</div>
      <p className="panel-subtitle">Flag content published before a cutoff year as "Remove/Redirect".</p>
      <div className="input-group">
        <div className="radio-group">
          <label className="radio-row"><input type="radio" name="oc" checked={enabled} onChange={() => setEnabled(true)} /><span>Yes, check for old content</span></label>
          <label className="radio-row"><input type="radio" name="oc" checked={!enabled} onChange={() => setEnabled(false)} /><span>No, skip this step</span></label>
        </div>
      </div>
      {enabled && (
        <>
          <div className="input-group">
            <div className="input-label">Cutoff year</div>
            <input type="number" className="input-field" value={cutoffYear} onChange={(e) => setCutoffYear(parseInt(e.target.value) || 2020)} min={2000} max={2026} style={{ maxWidth: 100 }} />
          </div>
          {dateFields.length > 1 && (
            <div className="input-group">
              <div className="input-label">Date field</div>
              <div className="radio-group">
                {dateFields.map(f => <label key={f} className="radio-row"><input type="radio" name="df" value={f} checked={dateField === f} onChange={() => setDateField(f)} /><span>{f}</span></label>)}
              </div>
            </div>
          )}
        </>
      )}
      <button className="btn btn-primary btn-sm" style={{ marginTop: 'var(--sp-3)' }} onClick={() => onConfirm({ enabled, cutoff_year: enabled ? cutoffYear : null, date_field: enabled ? dateField : null })}>Continue</button>
    </div>
  )
}
