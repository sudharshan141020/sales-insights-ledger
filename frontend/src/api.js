// Same-origin by default (the built frontend is served by the same FastAPI
// process as the API). VITE_API_BASE can override this for local dev when
// running `npm run dev` separately from the backend.
const API_BASE = import.meta.env.VITE_API_BASE || '';

export async function analyzeFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    body: formData,
  });

  const body = await res.json();

  if (!res.ok) {
    const message = typeof body.detail === 'string'
      ? body.detail
      : 'The file could not be analyzed. Check that it is a valid file.';
    throw new Error(message);
  }

  return body;
}

export async function analyzeCombined(files) {
  const formData = new FormData();
  files.forEach((f) => formData.append('files', f));

  const res = await fetch(`${API_BASE}/api/analyze-combined`, {
    method: 'POST',
    body: formData,
  });

  const body = await res.json();

  if (!res.ok) {
    const message = typeof body.detail === 'string'
      ? body.detail
      : 'The files could not be combined.';
    throw new Error(message);
  }

  return body;
}

export async function loadDemoFile() {
  const res = await fetch('/demo-sales-data.csv');
  if (!res.ok) throw new Error('Could not load the demo dataset.');
  const blob = await res.blob();
  return new File([blob], 'demo-sales-data.csv', { type: 'text/csv' });
}
