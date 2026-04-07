import React, { useState, useRef } from 'react'
import { uploadFile } from '../api/client'

const FILE_TYPES = [
  { key: 'sf', label: 'Screaming Frog Crawl', description: 'Site crawl export (.csv)', required: true },
  { key: 'ga4_organic', label: 'GA4 Organic Traffic', description: 'Organic landing page report (.csv)', required: true },
  { key: 'external_links', label: 'External Links', description: 'Backlink data (.csv)', required: true },
]

export default function FileUpload({ domain, uploadedFiles, onFileUploaded, disabled, allRequired }) {
  return (
    <div className="slide-up" style={{ marginTop: 'var(--sp-4)' }}>
      <div className="input-label" style={{ marginBottom: 'var(--sp-3)' }}>Upload CSV Files</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
        {FILE_TYPES.map((ft) => (
          <UploadZone key={ft.key} fileType={ft} domain={domain} isUploaded={uploadedFiles[ft.key]} onUploaded={() => onFileUploaded(ft.key)} disabled={disabled} />
        ))}
      </div>
    </div>
  )
}

function UploadZone({ fileType, domain, isUploaded, onUploaded, disabled }) {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState('')
  const [fileName, setFileName] = useState('')
  const inputRef = useRef(null)

  const handleFile = async (file) => {
    if (!file) return
    if (!file.name.endsWith('.csv')) { setError('Only .csv files accepted'); return }
    setIsUploading(true); setError(''); setFileName(file.name)
    try { await uploadFile(domain, fileType.key, file); onUploaded() }
    catch (err) { setError(err.message); setFileName('') }
    finally { setIsUploading(false) }
  }

  return (
    <div
      onDrop={(e) => { e.preventDefault(); setIsDragging(false); if (!disabled && !isUploaded) handleFile(e.dataTransfer.files[0]) }}
      onDragOver={(e) => { e.preventDefault(); if (!disabled && !isUploaded) setIsDragging(true) }}
      onDragLeave={() => setIsDragging(false)}
      onClick={() => { if (!disabled && !isUploaded && inputRef.current) inputRef.current.click() }}
      style={{
        display: 'flex', alignItems: 'center', gap: 'var(--sp-4)',
        padding: 'var(--sp-4) var(--sp-5)',
        borderRadius: 'var(--r-lg)',
        border: isUploaded ? '1px solid var(--success)' : isDragging ? '2px dashed var(--accent)' : '1px dashed var(--border-strong)',
        background: isUploaded ? 'var(--success-bg)' : isDragging ? 'var(--accent-light)' : 'var(--bg-body)',
        cursor: disabled || isUploaded ? 'default' : 'pointer',
        transition: 'all 150ms',
      }}
    >
      <input ref={inputRef} type="file" accept=".csv" onChange={(e) => { handleFile(e.target.files[0]); e.target.value = '' }} style={{ display: 'none' }} />

      <div style={{ width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 'var(--r-md)', background: isUploaded ? 'var(--success)' : 'var(--bg-muted)', flexShrink: 0, color: isUploaded ? '#fff' : 'var(--text-muted)', fontSize: '0.82rem', fontWeight: 600 }}>
        {isUploaded ? (
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3 8.5L6.5 12L13 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
        ) : isUploading ? '...' : 'CSV'}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 500, fontSize: '0.87rem', display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
          {fileType.label}
          {fileType.required && <span style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--accent)', background: 'var(--accent-light)', padding: '1px 6px', borderRadius: 10, letterSpacing: '0.04em' }}>REQUIRED</span>}
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 1 }}>
          {isUploaded ? `Uploaded: ${fileName || 'Complete'}` : isUploading ? `Uploading ${fileName}...` : fileType.description}
        </div>
        {error && <div style={{ fontSize: '0.78rem', color: 'var(--danger)', marginTop: 2 }}>{error}</div>}
      </div>

      {!isUploaded && !isUploading && <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>Drop or click</div>}
    </div>
  )
}
