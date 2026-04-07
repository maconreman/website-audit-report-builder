/**
 * API Client for the Website Audit Report Builder.
 * Communicates with the Flask backend via Vite proxy.
 */

const BASE = '/api';

async function request(path, options = {}) {
  const url = `${BASE}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });

  const data = await res.json();

  if (!res.ok) {
    const error = new Error(data.error || `Request failed: ${res.status}`);
    error.status = res.status;
    error.data = data;
    throw error;
  }

  return data;
}

// --- Domain & Session ---

export async function setDomain(domain) {
  return request('/domain', {
    method: 'POST',
    body: JSON.stringify({ domain }),
  });
}

export async function getStatus() {
  return request('/status');
}

export async function getSession(domain) {
  return request(`/session/${encodeURIComponent(domain)}`);
}

export async function resetSession(domain) {
  return request(`/session/${encodeURIComponent(domain)}/reset`, {
    method: 'POST',
  });
}

export async function getFiles(domain) {
  return request(`/files/${encodeURIComponent(domain)}`);
}

// --- File Upload (multipart) ---

export async function uploadFile(domain, fileType, file) {
  const formData = new FormData();
  formData.append('domain', domain);
  formData.append('file_type', fileType);
  formData.append('file', file);

  const res = await fetch(`${BASE}/upload`, {
    method: 'POST',
    body: formData,
    // No Content-Type header — browser sets multipart boundary
  });

  const data = await res.json();

  if (!res.ok) {
    const error = new Error(data.error || 'Upload failed');
    error.status = res.status;
    throw error;
  }

  return data;
}

// --- Step 2: Clean & Process ---

export async function runStep2(domain) {
  return request('/step2/run', {
    method: 'POST',
    body: JSON.stringify({ domain }),
  });
}

export async function getCustomColumns(domain) {
  return request(`/step2/custom-columns/${encodeURIComponent(domain)}`);
}

export async function confirmCustomColumns(domain, selectedTypes) {
  return request('/step2/confirm-custom', {
    method: 'POST',
    body: JSON.stringify({ domain, selected_types: selectedTypes }),
  });
}

// --- Step 3: Merge ---

export async function runStep3(domain) {
  return request('/step3/run', {
    method: 'POST',
    body: JSON.stringify({ domain }),
  });
}

// --- Step 4: Categorize ---

export async function runStep4(domain) {
  return request('/step4/run', {
    method: 'POST',
    body: JSON.stringify({ domain }),
  });
}

export async function getRecommendations(domain) {
  return request(`/step4/recommendations/${encodeURIComponent(domain)}`);
}

export async function approveCategory(domain, patternKey) {
  return request('/step4/approve', {
    method: 'POST',
    body: JSON.stringify({ domain, pattern_key: patternKey }),
  });
}

export async function rejectCategory(domain, patternKey) {
  return request('/step4/reject', {
    method: 'POST',
    body: JSON.stringify({ domain, pattern_key: patternKey }),
  });
}

export async function approveAllCategories(domain) {
  return request('/step4/approve-all', {
    method: 'POST',
    body: JSON.stringify({ domain }),
  });
}

// --- Step 5: Actions ---

export async function runStep5(domain) {
  return request('/step5/run', {
    method: 'POST',
    body: JSON.stringify({ domain }),
  });
}

export async function configureOldContent(domain, settings) {
  return request('/step5/old-content-config', {
    method: 'POST',
    body: JSON.stringify({ domain, ...settings }),
  });
}

export async function getThresholdStats(domain) {
  return request(`/step5/threshold-stats/${encodeURIComponent(domain)}`);
}

export async function applyThreshold(domain, thresholdType, value) {
  return request('/step5/apply-threshold', {
    method: 'POST',
    body: JSON.stringify({ domain, threshold_type: thresholdType, value }),
  });
}

export async function previewThreshold(domain, thresholdType, value) {
  return request('/step5/preview-threshold', {
    method: 'POST',
    body: JSON.stringify({ domain, threshold_type: thresholdType, value }),
  });
}

export async function skipThreshold(domain) {
  return request('/step5/skip-threshold', {
    method: 'POST',
    body: JSON.stringify({ domain }),
  });
}

export async function recentContentKeep(domain) {
  return request('/step5/recent-content-keep', {
    method: 'POST',
    body: JSON.stringify({ domain }),
  });
}

export async function recentContentSkip(domain) {
  return request('/step5/recent-content-skip', {
    method: 'POST',
    body: JSON.stringify({ domain }),
  });
}

// --- Step 6: Documentation ---

export async function generateDocs(domain) {
  return request('/step6/generate', {
    method: 'POST',
    body: JSON.stringify({ domain }),
  });
}

export function getDocsDownloadUrl(domain) {
  return `${BASE}/step6/download/${encodeURIComponent(domain)}`;
}

export function getAuditDownloadUrl(domain) {
  return `${BASE}/step6/download-audit/${encodeURIComponent(domain)}`;
}

export function getXlsxDownloadUrl(domain) {
  return `${BASE}/step6/download-xlsx/${encodeURIComponent(domain)}`;
}
