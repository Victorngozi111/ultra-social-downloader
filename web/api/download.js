// Mock download endpoint. Wire up your actual downloader here.

module.exports = (req, res) => {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  const { url, quality } = req.body || {};
  if (!url) return res.status(400).json({ error: 'URL is required' });

  res.status(200).json({
    ok: true,
    file: `demo-${quality || 'best'}.mp4`,
    message: 'Download complete (mock). Implement real download logic server-side.'
  });
};
