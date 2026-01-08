// Mock info endpoint. Replace with real logic (e.g., ytdl-core or yt-dlp via serverless) when ready.

module.exports = (req, res) => {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  const { url, quality } = req.body || {};
  if (!url) return res.status(400).json({ error: 'URL is required' });

  res.status(200).json({
    ok: true,
    title: 'Sample media title',
    duration: '3:12',
    quality: quality || 'best',
    message: 'Metadata fetched (mocked). Swap in your backend to go live.'
  });
};
