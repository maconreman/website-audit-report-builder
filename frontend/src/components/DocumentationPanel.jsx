import React, { useState, useEffect } from 'react'
import { getDocsDownloadUrl, getAuditDownloadUrl, getXlsxDownloadUrl } from '../api/client'
import Scorecard, { ScorecardsGrid } from './Scorecard'
import BarChart from './BarChart'

const ACTION_COLORS = { Keep: 'var(--success)', 'Remove/Redirect': 'var(--danger)', 'Discuss Further': 'var(--warning)' }

export default function DocumentationPanel({ domain, onGenerate, isProcessing }) {
  const [generated, setGenerated] = useState(false)
  const [activeTab, setActiveTab] = useState('preview')
  const [preview, setPreview] = useState(null)
  const [loadingPreview, setLoadingPreview] = useState(false)

  // Item 4: Auto-generate on mount
  useEffect(() => {
    if (!generated && !isProcessing) {
      autoGenerate()
    }
  }, [])

  const autoGenerate = async () => {
    await onGenerate()
    setGenerated(true)
    fetchPreview()
  }

  const fetchPreview = async () => {
    setLoadingPreview(true)
    try {
      const res = await fetch(`/api/step6/preview/${encodeURIComponent(domain)}?rows=10`)
      if (res.ok) setPreview(await res.json())
    } catch(e) { console.error(e) }
    finally { setLoadingPreview(false) }
  }

  if (!generated) {
    return (
      <div className="panel slide-up">
        <div className="panel-title">Generating audit documentation...</div>
        <p className="panel-subtitle">Please wait while the documentation and Excel export are created.</p>
      </div>
    )
  }

  const s = preview?.summary || {}
  const actionItems = s.action_counts ? Object.entries(s.action_counts).map(([k,v]) => ({ label: k, value: v, color: ACTION_COLORS[k] || 'var(--slate-400)' })) : []
  const catItems = s.category_counts ? Object.entries(s.category_counts).sort((a,b) => b[1]-a[1]).slice(0,8).map(([k,v]) => ({ label: k, value: v, color: 'var(--accent)' })) : []
  const sharedMax = Math.max(...actionItems.map(i => i.value), ...catItems.map(i => i.value), 1)

  return (
    <div className="slide-up">
      <div className="tab-bar">
        <button className={`tab-item ${activeTab === 'preview' ? 'active' : ''}`} onClick={() => setActiveTab('preview')}>Audit Preview</button>
        <button className={`tab-item ${activeTab === 'docs' ? 'active' : ''}`} onClick={() => setActiveTab('docs')}>Documentation</button>
        <button className={`tab-item ${activeTab === 'download' ? 'active' : ''}`} onClick={() => setActiveTab('download')}>Download</button>
      </div>

      {loadingPreview && <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: 'var(--sp-4)' }}>Loading preview...</p>}

      {/* Audit Preview */}
      {activeTab === 'preview' && preview && (
        <div className="fade-in">
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 'var(--sp-3)' }}>
            <a href={getAuditDownloadUrl(domain)} className="btn btn-secondary btn-sm" style={{ textDecoration: 'none' }}>Download CSV</a>
          </div>

          <ScorecardsGrid>
            <Scorecard label="Total Pages" value={s.total_rows?.toLocaleString() || '—'} />
            <Scorecard label="Columns" value={s.total_columns || '—'} />
            {s['Landing Page Traffic'] && <Scorecard label="Total Traffic" value={Math.round(s['Landing Page Traffic'].total).toLocaleString()} sub={`avg ${s['Landing Page Traffic'].mean.toFixed(0)}/page`} />}
            {s['Impressions'] && <Scorecard label="Total Impressions" value={Math.round(s['Impressions'].total).toLocaleString()} />}
          </ScorecardsGrid>

          {(actionItems.length > 0 || catItems.length > 0) && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--sp-6)', marginTop: 'var(--sp-4)' }}>
              {actionItems.length > 0 && (
                <div>
                  <div className="input-label">Action Distribution</div>
                  <BarChart items={actionItems} maxValue={sharedMax} />
                </div>
              )}
              {catItems.length > 0 && (
                <div>
                  <div className="input-label">Page Categories</div>
                  <BarChart items={catItems} maxValue={sharedMax} />
                </div>
              )}
            </div>
          )}

          {preview.preview?.length > 0 && (
            <div style={{ marginTop: 'var(--sp-6)' }}>
              <div className="input-label">First {preview.preview.length} rows</div>
              <div className="data-table-wrap" style={{ maxHeight: 340 }}>
                <table className="data-table">
                  <thead><tr>{preview.columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
                  <tbody>
                    {preview.preview.map((row, i) => (
                      <tr key={i}>{preview.columns.map(c => <td key={c}>{row[c] ?? ''}</td>)}</tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Documentation */}
      {activeTab === 'docs' && (
        <div className="fade-in">
          {preview?.documentation ? (
            <pre style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.75rem', lineHeight: 1.6,
              background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
              borderRadius: 'var(--r-lg)', padding: 'var(--sp-5)', maxHeight: 500, overflowY: 'auto',
              whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: 'var(--text-primary)',
            }}>
              {preview.documentation}
            </pre>
          ) : (
            <p className="panel-subtitle">No documentation available.</p>
          )}
        </div>
      )}

      {/* Download */}
      {activeTab === 'download' && (
        <div className="fade-in" style={{ textAlign: 'center', padding: 'var(--sp-10) 0' }}>
          <h3 style={{ marginBottom: 'var(--sp-2)' }}>Audit Complete</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 'var(--sp-6)' }}>Your files are ready for download.</p>
          <div className="btn-group" style={{ justifyContent: 'center' }}>
            <a href={getXlsxDownloadUrl(domain)} className="btn btn-primary btn-sm" style={{ textDecoration: 'none' }}>Download Excel (.xlsx)</a>
            <a href={getAuditDownloadUrl(domain)} className="btn btn-secondary btn-sm" style={{ textDecoration: 'none' }}>Download CSV</a>
            <a href={getDocsDownloadUrl(domain)} className="btn btn-secondary btn-sm" style={{ textDecoration: 'none' }}>Download Documentation</a>
          </div>
        </div>
      )}

      {!preview && !loadingPreview && activeTab !== 'download' && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: 'var(--sp-4)' }}>No preview available.</p>
      )}
    </div>
  )
}
