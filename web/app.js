const form = document.getElementById('download-form');
const statusHead = document.getElementById('status-head');
const statusBody = document.getElementById('status-body');
const logEl = document.getElementById('log');
const progressBar = document.getElementById('progress-bar');
const startBtn = document.getElementById('get-started');
const downloadBtn = document.getElementById('download-btn');
const downloadAction = document.getElementById('download-action');
const descriptionBlock = document.getElementById('description-block');
const descriptionText = document.getElementById('description-text');
const copyDescriptionBtn = document.getElementById('copy-description');

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
  progressBar.style.width = `${Math.max(0, Math.min(100, percent))}%`;
}

function setDescription(text) {
  if (text) {
    descriptionText.value = text;
    descriptionBlock.style.display = 'flex';
  } else {
    descriptionText.value = '';
    descriptionBlock.style.display = 'none';
  }
}

function setDownloadLink(url) {
  if (url) {
    downloadBtn.href = url;
    downloadAction.style.display = 'flex';
  } else {
    downloadBtn.removeAttribute('href');
    downloadAction.style.display = 'none';
  }
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

  setStatus('Fetching info', 'Talking to the downloader…');
  log(`Requested: ${url} (${quality})`);
  setProgress(10);
  setDownloadLink(null);
  setDescription(null);

  try {
    const info = await fetchInfo(url, quality);
    setStatus('Ready', info.message || 'Metadata received.');
    log(`Info: ${info.title} (${info.duration || 'n/a'})`);
    if (info.description) setDescription(info.description);
    setProgress(40);

    const dl = await startDownload(url, quality);
    setStatus('Complete', dl.message || 'Download finished.');
    log(`Result: ${dl.file || 'download ready'}`);
    if (dl.download_url) {
      log(`Download URL: ${dl.download_url}`);
    }
    setDownloadLink(dl.download_url || null);
    setProgress(100);
  } catch (err) {
    console.error(err);
    setStatus('Error', err.message || 'Request failed');
    log(`Error: ${err.message || 'request failed'}`);
    setProgress(0);
    setDownloadLink(null);
    setDescription(null);
  }
});

startBtn?.addEventListener('click', () => {
  document.getElementById('url').focus();
});

copyDescriptionBtn?.addEventListener('click', async () => {
  if (!descriptionText.value) return;
  try {
    await navigator.clipboard.writeText(descriptionText.value);
    copyDescriptionBtn.textContent = 'Copied';
    setTimeout(() => (copyDescriptionBtn.textContent = 'Copy'), 1200);
  } catch (e) {
    copyDescriptionBtn.textContent = 'Failed';
    setTimeout(() => (copyDescriptionBtn.textContent = 'Copy'), 1200);
  }
});
