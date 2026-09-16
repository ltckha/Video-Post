/**
 * n8n Code Node: Candidate Filter & Priority Scheduler
 * 
 * Filters rows from Google Sheet Tab 'Master':
 * 1. Must have a valid Google Drive URL (https://drive.google.com/...)
 * 2. Must have at least 1 platform in 'pending' status (YouTube, Facebook, or Instagram)
 * 3. Sorts by post_before deadline (Urgent <= 3 days first) and content_type interleaving
 */

function extractDriveFileId(url) {
  if (!url) return null;
  const match = url.match(/\/file\/d\/([a-zA-Z0-9_-]+)/) || url.match(/id=([a-zA-Z0-9_-]+)/);
  return match ? match[1] : null;
}

function parseDeadlineDays(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return 999;
  const parts = dateStr.trim().split('/');
  if (parts.length === 3) {
    const day = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1;
    const year = parseInt(parts[2], 10);
    const targetDate = new Date(year, month, day);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diffTime = targetDate - today;
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }
  return 999;
}

const items = $input.all();
const candidates = [];

for (let i = 0; i < items.length; i++) {
  const row = items[i].json;
  const rowNumber = i + 2; // Row index on Google Sheet (1-indexed, header is row 1)
  
  const driveUrl = (row.drive_url || '').trim();
  const fileId = extractDriveFileId(driveUrl);
  
  // Rule 1: Must have valid cloud Google Drive video
  if (!fileId) continue;
  
  const statusYt = (row.status_yt || '').trim().toLowerCase();
  const statusFb = (row.status_fb || '').trim().toLowerCase();
  const statusIg = (row.status_ig || '').trim().toLowerCase();
  
  const isYtPending = statusYt === 'pending';
  const isFbPending = statusFb === 'pending';
  const isIgPending = statusIg === 'pending';
  
  // Rule 2: At least 1 automated platform must be pending
  if (!isYtPending && !isFbPending && !isIgPending) continue;
  
  const daysLeft = parseDeadlineDays(row.post_before);
  
  // Prepare platform metadata
  const rawTitle = (row.title || 'Video Sản Phẩm').replace(/[<>]/g, '').trim();
  let ytTitle = rawTitle;
  if (ytTitle.length > 95) ytTitle = ytTitle.substring(0, 92).trim() + '...';
  
  let ytDesc = (row.caption_yt || rawTitle).trim();
  if (!ytDesc.toLowerCase().includes('#shorts')) {
    ytDesc = `${ytDesc}\n\n#Shorts`.trim();
  }
  
  const fbCaption = (row.caption_fb || rawTitle).trim();
  const igCaption = (row.caption_ig || rawTitle).trim();
  
  candidates.push({
    json: {
      row_number: rowNumber,
      job_id: row.job_id,
      title: rawTitle,
      video_path: row.video_path,
      drive_url: driveUrl,
      drive_file_id: fileId,
      content_type: row.content_type || 'real_product',
      post_before: row.post_before || '',
      days_left: daysLeft,
      shopee_link: row.shopee_link || '',
      
      // Target flags
      post_yt: isYtPending,
      post_fb: isFbPending,
      post_ig: isIgPending,
      
      // Formatted platform metadata
      brand_yt: row.brand_yt || 'Default',
      brand_fb: row.brand_fb || 'Default',
      brand_ig: row.brand_ig || 'Default',
      yt_title: ytTitle,
      yt_caption: ytDesc,
      fb_caption: fbCaption,
      ig_caption: igCaption,
    }
  });
}

// Sort candidates: Urgent events (days_left <= 3) first, then by days_left ascending
candidates.sort((a, b) => {
  const dA = a.json.days_left;
  const dB = b.json.days_left;
  if (dA <= 3 && dB > 3) return -1;
  if (dB <= 3 && dA > 3) return 1;
  return dA - dB;
});

// Take top candidates for this batch run (e.g. top 1-3 videos per scheduled execution)
const limit = 1;
return candidates.slice(0, limit);
