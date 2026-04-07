import React, { useState } from 'react'
import { setDomain as apiSetDomain } from '../api/client'

export default function DomainInput({ domain, onDomainSet, disabled }) {
  const [value, setValue] = useState(domain || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    const raw = value.trim()
    if (!raw) { setError('Please enter a domain'); return }
    setLoading(true); setError('')
    try {
      const data = await apiSetDomain(raw)
      onDomainSet(data.domain)
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  if (domain) {
    return (
      <div className="panel panel-success slide-up">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div className="input-label">Active Domain</div>
            <div style={{ fontSize: '1rem', fontWeight: 600 }}>{domain}</div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => { onDomainSet(''); setValue('') }} disabled={disabled}>Change</button>
        </div>
      </div>
    )
  }

  return (
    <div className="panel slide-up">
      <div className="panel-title">Set Domain</div>
      <p className="panel-subtitle">This determines the folder structure for all uploaded and generated files.</p>
      <div style={{ display: 'flex', gap: 'var(--sp-2)', alignItems: 'flex-start' }}>
        <div className="input-group" style={{ flex: 1, marginBottom: 0 }}>
          <input type="text" className="input-field" placeholder="example.com" value={value}
            onChange={(e) => setValue(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSubmit(e)}
            disabled={disabled || loading} autoFocus />
        </div>
        <button className="btn btn-primary" onClick={handleSubmit} disabled={disabled || loading || !value.trim()}>
          {loading ? 'Setting...' : 'Set Domain'}
        </button>
      </div>
      {error && <p style={{ color: 'var(--danger)', fontSize: '0.82rem', marginTop: 'var(--sp-2)' }}>{error}</p>}
    </div>
  )
}
