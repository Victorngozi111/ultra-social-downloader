// Forwards download requests to a remote worker you control.
// Set REMOTE_WORKER_URL (e.g., https://worker.example.com) in Vercel env vars.

const WORKER_URL = process.env.REMOTE_WORKER_URL;

module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  const { url, quality } = req.body || {};
  if (!url) return res.status(400).json({ error: 'URL is required' });
  if (!WORKER_URL) return res.status(500).json({ error: 'REMOTE_WORKER_URL not configured' });

  try {
    const upstream = await fetch(`${WORKER_URL}/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, quality })
    });

    const data = await upstream.json();

    // If worker didn't return a download_url, synthesize one when file is present.
    if (!data.download_url && data.file) {
      const encoded = encodeURIComponent(data.file);
      data.download_url = `${WORKER_URL}/files/${encoded}`;
    }

    return res.status(upstream.ok ? 200 : upstream.status).json(data);
  } catch (err) {
    return res.status(502).json({ error: 'Upstream download request failed', detail: String(err) });
  }
};
