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

// Vercel serverless hard limit is 4.5 MB per request.
// We split at 3.5 MB to stay well under it.
const CHUNK_SIZE = 3_500_000; // 3.5 MB in bytes

export async function uploadFile(domain, fileType, file, onProgress) {
  // ── Safety check: reject obviously wrong files early ──────────────────────
  if (!file.name.toLowerCase().endsWith('.csv')) {
    throw new Error('Only .csv files are accepted.');
  }

  // ── Small file: single request (under 3.5 MB) ─────────────────────────────
  if (file.size <= CHUNK_SIZE) {
    return _uploadSingle(domain, fileType, file);
  }

  // ── Large file: chunked upload ────────────────────────────────────────────
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);

  // Upload each chunk
  for (let i = 0; i < totalChunks; i++) {
    const start = i * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, file.size);
    const chunk = file.slice(start, end);

    const formData = new FormData();
    formData.append('domain', domain);
    formData.append('file_type', fileType);
    formData.append('chunk_index', String(i));
    formData.append('total_chunks', String(totalChunks));
    formData.append('file', chunk, file.name);

    let res;
    try {
      res = await fetch(`${BASE}/upload-chunk`, { method: 'POST', body: formData });
    } catch (networkErr) {
      throw new Error(`Upload failed on chunk ${i + 1}/${totalChunks}: could not reach the server.`);
    }

    const data = await _safeJson(res, `Chunk ${i + 1}/${totalChunks} upload`);
    if (!res.ok) {
      throw new Error(data.error || `Chunk ${i + 1} failed (HTTP ${res.status})`);
    }

    // Report progress as a 0–90 percentage (finalize takes the last 10%)
    if (onProgress) {
      onProgress(Math.round(((i + 1) / totalChunks) * 90));
    }
  }

  // ── Finalize: assemble chunks on the server ───────────────────────────────
  let res;
  try {
    res = await fetch(`${BASE}/upload-finalize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        domain,
        file_type: fileType,
        total_chunks: totalChunks,
        filename: file.name,
      }),
    });
  } catch (networkErr) {
    throw new Error('Upload failed during final assembly: could not reach the server.');
  }

  const data = await _safeJson(res, 'Upload finalize');
  if (!res.ok) {
    throw new Error(data.error || `Finalize failed (HTTP ${res.status})`);
  }

  if (onProgress) onProgress(100);
  return data;
}


// ── Internal helpers ──────────────────────────────────────────────────────────

async function _uploadSingle(domain, fileType, file) {
  const formData = new FormData();
  formData.append('domain', domain);
  formData.append('file_type', fileType);
  formData.append('file', file);

  let res;
  try {
    res = await fetch(`${BASE}/upload`, { method: 'POST', body: formData });
  } catch (networkErr) {
    throw new Error('Upload failed: could not reach the server. Check your connection.');
  }

  const data = await _safeJson(res, 'Upload');
  if (!res.ok) {
    throw new Error(data.error || `Upload failed (HTTP ${res.status})`);
  }
  return data;
}

async function _safeJson(res, label) {
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return res.json();
  }
  const text = await res.text();
  if (res.status === 413 || text.toLowerCase().includes('too large')) {
    throw new Error(
      'A file chunk exceeded the server limit. ' +
      'This is unexpected — please contact support.'
    );
  }
  if (!res.ok) {
    throw new Error(
      `${label} failed (HTTP ${res.status}). ` +
      'The server returned an unexpected response. Please try again.'
    );
  }
  return {};
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
