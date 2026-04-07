import React, { useState, useCallback, useRef, useEffect } from 'react'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import StepWizard from './components/StepWizard'
import DomainInput from './components/DomainInput'
import FileUpload from './components/FileUpload'
import LogPanel from './components/LogPanel'
import CategoryApproval from './components/CategoryApproval'
import ThresholdPanel from './components/ThresholdPanel'
import OldContentPanel from './components/OldContentPanel'
import RecentContentPanel from './components/RecentContentPanel'
import DocumentationPanel from './components/DocumentationPanel'
import Scorecard, { ScorecardsGrid } from './components/Scorecard'
import BarChart from './components/BarChart'
import * as api from './api/client'
import './App.css'

const STEPS = [
  { id: 1, label: 'Upload Data' },
  { id: 2, label: 'Clean & Process' },
  { id: 3, label: 'Merge Sources' },
  { id: 4, label: 'Categorize' },
  { id: 5, label: 'Assign Actions' },
  { id: 6, label: 'Documentation' },
]

function appendLogs(logs, addLog) {
  if (!logs) return
  for (const l of logs) addLog(l.message, l.type || 'info')
}

export default function App() {
  const [darkMode, setDarkMode] = useState(true)
  const [domain, setDomain] = useState('')
  const [currentStep, setCurrentStep] = useState(1)
  const [completedSteps, setCompletedSteps] = useState([])
  const [logs, setLogs] = useState([])
  const [isProcessing, setIsProcessing] = useState(false)

  // Interactive panels (only shown when user input is needed)
  const [showCategoryApproval, setShowCategoryApproval] = useState(false)
  const [categoryData, setCategoryData] = useState(null)
  const [showThreshold, setShowThreshold] = useState(false)
  const [thresholdData, setThresholdData] = useState(null)
  const [showOldContent, setShowOldContent] = useState(false)
  const [oldContentOptions, setOldContentOptions] = useState(null)
  const [showRecentContent, setShowRecentContent] = useState(false)
  const [recentContentData, setRecentContentData] = useState(null)
  const [dateWarning, setDateWarning] = useState(null)
  const [stepResults, setStepResults] = useState({})

  const [uploadedFiles, setUploadedFiles] = useState({ sf: false, ga4_organic: false, external_links: false })
  const logEndRef = useRef(null)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  useEffect(() => {
    setShowCategoryApproval(false); setShowThreshold(false)
    setShowOldContent(false); setShowRecentContent(false)
  }, [currentStep])

  const addLog = useCallback((msg, type = 'info') => {
    setLogs(prev => [...prev, { id: Date.now() + Math.random(), message: msg, type, timestamp: new Date().toLocaleTimeString() }])
  }, [])
  const clearLogs = useCallback(() => setLogs([]), [])
  const markComplete = useCallback((id) => setCompletedSteps(prev => prev.includes(id) ? prev : [...prev, id].sort()), [])
  const goToStep = useCallback((id) => {
    const max = Math.max(1, ...completedSteps, 0) + 1
    if (id <= max) setCurrentStep(id)
  }, [completedSteps])
  const goBack = useCallback(() => { if (currentStep > 1) setCurrentStep(currentStep - 1) }, [currentStep])

  const onFileUploaded = useCallback((ft) => {
    setUploadedFiles(prev => ({ ...prev, [ft]: true }))
    addLog(`Uploaded: ${ft.replace('_', ' ').toUpperCase()}`, 'success')
  }, [addLog])
  const onDomainSet = useCallback((d) => { setDomain(d); if (d) addLog(`Domain set: ${d}`, 'success') }, [addLog])

  const allFilesUploaded = uploadedFiles.sf && uploadedFiles.ga4_organic && uploadedFiles.external_links

  const hp = {
    domain, addLog, clearLogs, setIsProcessing, markComplete, setCurrentStep,
    setShowCategoryApproval, setCategoryData, setDateWarning,
    setShowThreshold, setThresholdData, setShowOldContent, setOldContentOptions,
    setShowRecentContent, setRecentContentData, setStepResults,
  }

  // AUTO-CHAIN: after uploading all files, run Steps 2-3 automatically, then pause at 4 for category decisions
  const startAutoChain = async () => {
    clearLogs()
    setIsProcessing(true)
    addLog('Starting audit pipeline...', 'heading')

    try {
      // Step 2
      setCurrentStep(2)
      addLog('Step 2: Cleaning and processing data...', 'heading')
      const r2 = await api.runStep2(domain)
      appendLogs(r2.logs, addLog)
      if (r2.date_warning) setDateWarning(r2.date_warning)
      if (r2.custom_columns_auto_selected?.length > 0) {
        addLog(`Auto-selected: ${r2.custom_columns_auto_selected.join(', ')}`, 'info')
      }
      setStepResults(prev => ({ ...prev, step2: { sf_200_rows: r2.sf_200_rows, url_prefix: r2.url_prefix, has_trailing_slash: r2.has_trailing_slash } }))
      markComplete(2)
      addLog('Step 2 complete.', 'success')

      // Step 3
      setCurrentStep(3)
      addLog('Step 3: Merging data sources...', 'heading')
      const r3 = await api.runStep3(domain)
      appendLogs(r3.logs, addLog)
      setStepResults(prev => ({ ...prev, step3: { initial_rows: r3.initial_rows, final_rows: r3.final_rows, final_columns: r3.final_columns } }))
      markComplete(3)
      addLog('Step 3 complete.', 'success')

      // Step 4 — detect patterns, then pause for user decisions if needed
      setCurrentStep(4)
      addLog('Step 4: Detecting page categories...', 'heading')
      const r4 = await api.runStep4(domain)
      appendLogs(r4.logs, addLog)

      if (r4.status === 'awaiting_approval' && r4.total_patterns > 0) {
        setCategoryData({ recommendations: r4.recommendations, keys: r4.keys })
        setShowCategoryApproval(true)
        addLog('Review detected URL patterns below.', 'info')
        setIsProcessing(false)
        // Chain resumes after category approval finishes (see catAction)
      } else {
        if (r4.category_summary) setStepResults(prev => ({ ...prev, step4: r4.category_summary }))
        markComplete(4)
        addLog('Step 4 complete.', 'success')
        // Continue to Step 5
        await continueFromStep5(hp)
      }
    } catch (e) {
      addLog(`Error: ${e.message}`, 'error')
      setIsProcessing(false)
    }
  }

  return (
    <ErrorBoundary>
      <Layout>
        <header className="app-header">
          <div className="app-brand">
            <h1>Website Audit</h1>
            <span>Report Builder</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-4)' }}>
            {domain && <div className="app-header-domain">{domain}</div>}
            <button className="btn-back" style={{ color: 'var(--slate-400)', fontSize: '0.75rem' }}
              onClick={() => setDarkMode(!darkMode)}>
              {darkMode ? 'Light Mode' : 'Dark Mode'}
            </button>
          </div>
        </header>

        <StepWizard steps={STEPS} currentStep={currentStep} completedSteps={completedSteps} onStepClick={goToStep} isProcessing={isProcessing} />

        <main className="app-main">
          {currentStep > 1 && (
            <div className="step-nav slide-up">
              <button className="btn-back" onClick={goBack} disabled={isProcessing}>Back to Step {currentStep - 1}</button>
            </div>
          )}

          {/* STEP 1 — Upload */}
          {currentStep === 1 && (
            <div className="step-content slide-up">
              <div className="step-header">
                <h2>Upload Your Data</h2>
                <p className="step-desc">Enter your domain and upload all three CSV files. The audit will run automatically.</p>
              </div>
              <DomainInput domain={domain} onDomainSet={onDomainSet} disabled={isProcessing} />
              {domain && <FileUpload domain={domain} uploadedFiles={uploadedFiles} onFileUploaded={onFileUploaded} disabled={isProcessing} allRequired={true} />}
              {domain && allFilesUploaded && (
                <button className="btn btn-primary btn-lg" style={{ marginTop: 'var(--sp-6)' }}
                  onClick={() => { markComplete(1); startAutoChain() }} disabled={isProcessing}>
                  Run Audit
                </button>
              )}
              {domain && !allFilesUploaded && uploadedFiles.sf && (
                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 'var(--sp-4)' }}>
                  All three CSV files are required before running the audit.
                </p>
              )}
            </div>
          )}

          {/* STEP 2 — shown during auto-chain */}
          {currentStep === 2 && (
            <div className="step-content slide-up">
              <div className="step-header">
                <h2>Clean and Process Data</h2>
                <p className="step-desc">Filtering HTML pages, extracting custom data, calculating reading times and page highlights.</p>
              </div>
              {stepResults.step2 && (
                <ScorecardsGrid>
                  <Scorecard label="HTML 200 Pages" value={stepResults.step2.sf_200_rows?.toLocaleString() || '—'} />
                  <Scorecard label="URL Prefix" value={stepResults.step2.url_prefix || '—'} />
                </ScorecardsGrid>
              )}
              {isProcessing && <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 'var(--sp-4)' }}>Processing...</p>}
            </div>
          )}

          {/* STEP 3 */}
          {currentStep === 3 && (
            <div className="step-content slide-up">
              <div className="step-header">
                <h2>Merge Data Sources</h2>
                <p className="step-desc">Joining GA4 Organic and External Links data into the audit.</p>
              </div>
              {stepResults.step3 && (
                <ScorecardsGrid>
                  <Scorecard label="Initial Rows" value={stepResults.step3.initial_rows?.toLocaleString() || '—'} />
                  <Scorecard label="Final Rows" value={stepResults.step3.final_rows?.toLocaleString() || '—'} />
                  <Scorecard label="Total Columns" value={stepResults.step3.final_columns || '—'} />
                </ScorecardsGrid>
              )}
              {isProcessing && <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 'var(--sp-4)' }}>Merging...</p>}
            </div>
          )}

          {/* STEP 4 — pauses for category decisions */}
          {currentStep === 4 && (
            <div className="step-content slide-up">
              <div className="step-header">
                <h2>Assign Page Categories</h2>
                <p className="step-desc">Review detected URL patterns. Select "Manual Check" for pages that need Nexus review.</p>
              </div>
              {stepResults.step4 && !showCategoryApproval && (
                <BarChart items={Object.entries(stepResults.step4).map(([k,v]) => ({ label: k, value: v, color: k === 'Manual Check' ? 'var(--warning)' : 'var(--accent)' }))} />
              )}
              {showCategoryApproval && categoryData && (
                <CategoryApproval data={categoryData}
                  onApprove={(k) => catAction('approve', k, hp)}
                  onReject={(k) => catAction('reject', k, hp)}
                  onApproveAll={() => catAction('approve_all', null, hp)} />
              )}
              {completedSteps.includes(4) && !showCategoryApproval && !isProcessing && (
                <button className="btn btn-primary btn-sm" style={{ marginTop: 'var(--sp-4)' }}
                  onClick={() => continueFromStep5(hp)} disabled={isProcessing}>
                  Continue to Actions
                </button>
              )}
            </div>
          )}

          {/* STEP 5 — pauses for thresholds/recent/old content decisions */}
          {currentStep === 5 && (
            <div className="step-content slide-up">
              <div className="step-header">
                <h2>Assign Actions</h2>
                <p className="step-desc">Automatic rules applied. Set thresholds for remaining pages.</p>
              </div>
              {stepResults.step5 && !showOldContent && !showThreshold && !showRecentContent && (
                <BarChart items={Object.entries(stepResults.step5).map(([k,v]) => {
                  const c = { Keep: 'var(--success)', 'Remove/Redirect': 'var(--danger)', 'Discuss Further': 'var(--warning)' }
                  return { label: k, value: v, color: c[k] || 'var(--slate-400)' }
                })} />
              )}
              {showThreshold && thresholdData && <ThresholdPanel data={thresholdData} domain={domain} onApply={(t, v) => threshApply(t, v, hp)} onSkip={() => threshSkip(hp)} />}
              {showRecentContent && recentContentData && <RecentContentPanel data={recentContentData} onKeep={() => recentAction('keep', hp)} onSkip={() => recentAction('skip', hp)} />}
              {showOldContent && oldContentOptions && <OldContentPanel options={oldContentOptions} onConfirm={(s) => { setShowOldContent(false); oldContentConfirm(s, hp) }} />}
              {isProcessing && !showThreshold && !showRecentContent && !showOldContent && (
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 'var(--sp-4)' }}>Processing actions...</p>
              )}
            </div>
          )}

          {/* STEP 6 — auto-generates docs on arrival */}
          {currentStep === 6 && (
            <div className="step-content slide-up">
              <div className="step-header">
                <h2>Audit Complete</h2>
                <p className="step-desc">Documentation and Excel export have been generated.</p>
              </div>
              <DocumentationPanel domain={domain} onGenerate={() => runStep6(hp)} isProcessing={isProcessing} />
            </div>
          )}

          <LogPanel logs={logs} onClear={clearLogs} logEndRef={logEndRef} />
        </main>
      </Layout>
    </ErrorBoundary>
  )
}

/* ========================================
   HANDLERS
   ======================================== */

// Step 5 response router
function route5(res, p) {
  if (res.status === 'awaiting_threshold') {
    p.setThresholdData(res.threshold_stats); p.setShowThreshold(true)
  } else if (res.status === 'awaiting_recent_content') {
    p.setShowThreshold(false); p.setRecentContentData(res.recent_content); p.setShowRecentContent(true)
  } else if (res.status === 'awaiting_old_content_config') {
    p.setShowThreshold(false); p.setShowRecentContent(false)
    p.setOldContentOptions({ has_date_published: res.has_date_published, has_date_modified: res.has_date_modified })
    p.setShowOldContent(true)
  } else {
    p.setShowThreshold(false); p.setShowRecentContent(false); p.setShowOldContent(false)
    if (res.action_summary) p.setStepResults(prev => ({ ...prev, step5: res.action_summary }))
    p.markComplete(5); p.addLog('Step 5 complete.', 'success'); p.setCurrentStep(6)
    p.setIsProcessing(false)
  }
}

// Continue chain from Step 5 (called after Step 4 finishes)
async function continueFromStep5(p) {
  p.setIsProcessing(true)
  p.setCurrentStep(5)
  p.addLog('Step 5: Assigning actions...', 'heading')
  try {
    const r = await api.runStep5(p.domain)
    appendLogs(r.logs, p.addLog)
    route5(r, p)
  } catch (e) {
    p.addLog(`Error: ${e.message}`, 'error')
    p.setIsProcessing(false)
  }
}

// Step 6
async function runStep6(p) {
  p.setIsProcessing(true)
  try {
    p.addLog('Generating documentation and Excel export...', 'heading')
    const r = await api.generateDocs(p.domain)
    appendLogs(r.logs, p.addLog)
    p.markComplete(6)
  } catch (e) {
    p.addLog(`Error: ${e.message}`, 'error')
  } finally {
    p.setIsProcessing(false)
  }
}

// Category actions — resume chain after all categories decided
async function catAction(act, key, p) {
  try {
    if (act === 'approve') {
      const r = await api.approveCategory(p.domain, key)
      p.addLog(`Approved: ${key} -> ${r.category}`, 'info')
    } else if (act === 'reject') {
      await api.rejectCategory(p.domain, key)
      p.addLog(`Manual Check: ${key}`, 'info')
    } else if (act === 'approve_all') {
      p.setIsProcessing(true)
      const r = await api.approveAllCategories(p.domain)
      appendLogs(r.logs, p.addLog)
      if (r.category_summary) p.setStepResults(prev => ({ ...prev, step4: r.category_summary }))
      p.setShowCategoryApproval(false)
      p.markComplete(4)
      p.addLog('Step 4 complete.', 'success')
      // Auto-continue to Step 5
      await continueFromStep5(p)
    }
  } catch (e) { p.addLog(`Error: ${e.message}`, 'error'); p.setIsProcessing(false) }
}

async function oldContentConfirm(settings, p) {
  p.setIsProcessing(true)
  try {
    const r = await api.configureOldContent(p.domain, settings)
    appendLogs(r.logs, p.addLog)
    route5(r, p)
  } catch (e) { p.addLog(`Error: ${e.message}`, 'error'); p.setIsProcessing(false) }
}

async function threshApply(type, value, p) {
  p.setIsProcessing(true)
  try {
    const r = await api.applyThreshold(p.domain, type, value)
    appendLogs(r.logs, p.addLog)
    if (r.status === 'next_metric' && r.next_threshold_stats) p.setThresholdData(r.next_threshold_stats)
    else route5(r, p)
  } catch (e) { p.addLog(`Error: ${e.message}`, 'error') }
  finally { p.setIsProcessing(false) }
}

async function threshSkip(p) {
  p.setIsProcessing(true)
  try {
    const r = await api.skipThreshold(p.domain)
    appendLogs(r.logs, p.addLog)
    if (r.status === 'next_metric' && r.next_threshold_stats) p.setThresholdData(r.next_threshold_stats)
    else route5(r, p)
  } catch (e) { p.addLog(`Error: ${e.message}`, 'error') }
  finally { p.setIsProcessing(false) }
}

async function recentAction(act, p) {
  p.setIsProcessing(true)
  try {
    const r = act === 'keep' ? await api.recentContentKeep(p.domain) : await api.recentContentSkip(p.domain)
    appendLogs(r.logs, p.addLog)
    route5(r, p)
  } catch (e) { p.addLog(`Error: ${e.message}`, 'error'); p.setIsProcessing(false) }
}
