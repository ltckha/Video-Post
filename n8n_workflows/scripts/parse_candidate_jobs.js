/**
 * n8n Code Node: Candidate Filter & Dynamic Brand Account Router
 * 
 * Filters rows from Google Sheet Tab 'Master':
 * 1. Must have a valid Google Drive URL (https://drive.google.com/...)
 * 2. Must have at least 1 platform in 'pending' status (YouTube, Facebook, or Instagram)
 * 3. Injects page_id, instagram_account_id, access_token based on brand name
 * 4. Sorts by post_before deadline (Urgent <= 3 days first)
 */

const BRAND_CONFIGS = {
  "Ở Đà Lạt Vậy Thôi": {
    "page_id": "844568818731831",
    "access_token": "EAAJMZCPWzTfUBSDXjrOhVLNT6utNTkN29ZADhOYzSLUC9Yha5iAqUk1ABh2Myf2ZA6MhT1EZAXRZAZCk9i6litchuVu3dsv5XMp9DETDzqEiSeTrpDhfxqTcYShmIsR0KeVIUVA85kNuxus5jwolZCZB7Y9qhRLYTCmFKOt4UaM2CwZAPuj8bka4rT0uDZAHaZAqAx8Umx7iXex6Iri1DI3dVlOnZAM1",
    "expires_at": "5 Tháng 10, 2026"
  },
  "Ờ Đà Lạt vậy thôi": {
    "page_id": "844568818731831",
    "access_token": "EAAJMZCPWzTfUBSDXjrOhVLNT6utNTkN29ZADhOYzSLUC9Yha5iAqUk1ABh2Myf2ZA6MhT1EZAXRZAZCk9i6litchuVu3dsv5XMp9DETDzqEiSeTrpDhfxqTcYShmIsR0KeVIUVA85kNuxus5jwolZCZB7Y9qhRLYTCmFKOt4UaM2CwZAPuj8bka4rT0uDZAHaZAqAx8Umx7iXex6Iri1DI3dVlOnZAM1",
    "expires_at": "5 Tháng 10, 2026"
  },
  "Mua Chuẩn Xài Lâu": {
    "page_id": "784690811398271",
    "instagram_account_id": "17841438149517044",
    "access_token": "EAAJMZCPWzTfUBSO6Mq8yK2rUHRK7shPnPZAW4ZBcX0a75VNYE3EsPZAZCaq9pZBU1a2ko6U67y0uarg2WaqsYf18rWHuc41Tke9ZAyvE7ixYF58ayqDmKJ3l1t9DBdWEGD9ayX7XERZB337APrkUDFWFbaZAZCwTTNHyIGHmYH6IxFMpGvLBhIgJ9TDwWRUEfenusd4O1fbB0Cn1q8PI0v0nuifl0m",
    "expires_at": "5 Tháng 10, 2026"
  },
  "Elegant Steps": {
    "page_id": "759422287260703",
    "access_token": "EAAJMZCPWzTfUBSPSorpZCQPFsgYJZALzuv1pi7W9ZCTbsX4CNIr8gWBNBqFcmnZCBZCuVJze6uCBQVUWzAK0y8L4HY4LUqUdIhFejAiKZCO0NGpei6bHMQwUTcBZCbzWPGgZAHDBHyxgeIXsB9azpUf3kvm2keltG2DqZCvG9jbUKnsYLd1bpZCuXgsAjJAbejmzZB7LmpnFj96BZC3acAcBrwERT",
    "expires_at": "5 Tháng 10, 2026"
  },
  "YenYen Deals": {
    "page_id": "708959132306661",
    "access_token": "EAAJMZCPWzTfUBSCZA0a3atw0j44PhIpLqvbVC9LyS0ZAToys9pCn1Qph810ZCvZBC5BXLtZBZAUOVqBZCK5nmaznPKZBuzoZBPT9eOVJwIoKnUOrUsjZBnMZCdbQUi3ZAmyFdGIE8iEPIOoeVgdq7s2DlegTgFDJRdaKwI8Vo03mkT24yZBZBZAxZBDfcZAb97mZCmkuMRe2rHZCENfrZBpkbihtvLaNJ40uk",
    "expires_at": "5 Tháng 10, 2026"
  },
  "Yen Handmade Leather": {
    "page_id": "152902805484173",
    "access_token": "EAAJMZCPWzTfUBSFTEC8r0CLPruZAFN0xjk2KoTIFk837NtkBxNpdW2EVNA7VJcFSca68qzcPQEMcBqXCQULLa6HCpQZAMC6mrFCUbrw1bBPSP2MAiKvImC7ZC2dmLkmUWmi6L84Ob3FTP7HFxb7GCCPRjbDgsbxzZCJzxeisLz4Vhv55lOpEYmZA0wrkp1W8aRd1xOs77hFwJqByDIF7EZD",
    "expires_at": "5 Tháng 10, 2026"
  },
  "Macadamia Hải Nancy": {
    "page_id": "334201936734694",
    "access_token": "EAAJMZCPWzTfUBSOu5qTjZCzGZBVZChIoT9ZB4k4EPql1TL1vmb8FtABCaTMhYVQIZCUTZAmZBGO2RTizoXNvQOBRGDlZBFHtBjcSCaAAUK5crQbk0ywNJWZCge95cApd4UP3XLH383XZBASAZBAx4jQcyBIZBvJ0q05scJw4BagTqE06NCAD7yTyKfErru4EiWIKyeI4fHzu3uLWeQOZCRhVYqfhfk",
    "expires_at": "5 Tháng 10, 2026"
  },
  "Hiệu giày Hải Nancy": {
    "page_id": "195309723885691",
    "instagram_account_id": "17841406302274470",
    "access_token": "EAAJMZCPWzTfUBSIMhr6i8KbZA4BIoPyg3wEwyNfrZAKvAdm04eeQoYFlKIl091uZCUR8ZAzSftuHuYdBVuWZBTauK6diLtFzoiGPfSodkDxHvvygCKZAO2SK1FzVTZAKILruqzqAF4DfauJHYDv1skLIwArAYa9N0aWfW3kgJYcfwTcLDLJKTWHcjrNZCbAXwrG9rnug4wUVJQYcZBgmO4MFAZD",
    "expires_at": "15 Tháng 10, 2026"
  }
};

function getBrandCreds(brandName) {
  if (!brandName) return {};
  const clean = brandName.trim().toLowerCase();
  for (const [name, data] of Object.entries(BRAND_CONFIGS)) {
    if (name.trim().toLowerCase() === clean) {
      return data;
    }
  }
  // Default fallback to first brand
  return Object.values(BRAND_CONFIGS)[0] || {};
}

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
  
  // Resolve brand credentials dynamically
  const fbBrandName = row.brand_fb || row.brand_tt || 'Hiệu giày Hải Nancy';
  const igBrandName = row.brand_ig || fbBrandName;
  
  const fbCreds = getBrandCreds(fbBrandName);
  const igCreds = getBrandCreds(igBrandName);
  
  const brandFbPageId = fbCreds.page_id || '';
  const brandFbAccessToken = fbCreds.access_token || '';
  const brandIgUserId = igCreds.instagram_account_id || fbCreds.instagram_account_id || '';
  const brandIgAccessToken = igCreds.access_token || fbCreds.access_token || '';
  
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
      post_fb: isFbPending && Boolean(brandFbPageId),
      post_ig: isIgPending && Boolean(brandIgUserId),
      
      // Brand Credentials & IDs
      brand_yt: row.brand_yt || 'Default',
      brand_fb: fbBrandName,
      brand_ig: igBrandName,
      brand_fb_page_id: brandFbPageId,
      brand_fb_access_token: brandFbAccessToken,
      brand_ig_user_id: brandIgUserId,
      brand_ig_access_token: brandIgAccessToken,
      
      // Formatted platform captions
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

const limit = 1;
return candidates.slice(0, limit);
