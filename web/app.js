const form = document.getElementById('download-form');
const statusHead = document.getElementById('status-head');
const statusBody = document.getElementById('status-body');
const logEl = document.getElementById('log');
const progressBar = document.getElementById('progress-bar');
const demoBtn = document.getElementById('demo-run');
const startBtn = document.getElementById('get-started');

function log(line) {
  const p = document.createElement('p');
  p.className = 'log-line';
  p.textContent = line;
  logEl.appendChild(p);
  logEl.scrollTop = logEl.scrollHeight;
}

function setStatus(title, body) {
  statusHead.textContent = title;
  statusBody.textContent = body;
}

function setProgress(percent) {
  progressBar.style.width = `${percent}%`;
}

async function fetchInfo(url, quality) {
  const res = await fetch('/api/info', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, quality })
  });
  if (!res.ok) throw new Error('Info request failed');
  return res.json();
}

async function startDownload(url, quality) {
  const res = await fetch('/api/download', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, quality })
  });
  if (!res.ok) throw new Error('Download request failed');
  return res.json();
}

function mockProgress() {
  let pct = 0;
  setProgress(0);
  const interval = setInterval(() => {
    pct = Math.min(100, pct + Math.random() * 18);
    setProgress(pct);
    if (pct >= 100) clearInterval(interval);
  }, 300);
}

form?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const url = document.getElementById('url').value.trim();
  const quality = document.getElementById('quality').value;
  if (!url) return;

  setStatus('Fetching info', 'Contacting API…');
  log(`Requested: ${url} (${quality})`);
  mockProgress();

  try {
    const info = await fetchInfo(url, quality);
    setStatus('Ready to download', info.message);
    log(`Info: ${info.title} (${info.duration})`);

    const dl = await startDownload(url, quality);
    setStatus('Complete', dl.message);
    log(`Result: ${dl.file}`);
    setProgress(100);
  } catch (err) {
    console.error(err);
    setStatus('Error', err.message || 'Request failed');
    log(`Error: ${err.message}`);
    setProgress(0);
  }
});

demoBtn?.addEventListener('click', () => {
  document.getElementById('url').value = 'https://youtu.be/demo';
  form.dispatchEvent(new Event('submit'));
});

startBtn?.addEventListener('click', () => {
  document.getElementById('url').focus();
});
