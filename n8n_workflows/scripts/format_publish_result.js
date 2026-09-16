/**
 * n8n Code Node: Format Publish Results for Google Sheet Write-back
 * 
 * Assembles the status updates for status_yt, status_fb, status_ig on Tab Master.
 */

const items = $input.all();
const updates = [];

for (const item of items) {
  const data = item.json;
  
  // Extract results from branches
  const rowNumber = data.row_number;
  const updatesObj = {
    row_number: rowNumber,
    job_id: data.job_id,
  };
  
  // YouTube Status Update
  if (data.youtube_result) {
    const ytVideoId = data.youtube_result.id;
    if (ytVideoId) {
      updatesObj.status_yt = `https://www.youtube.com/watch?v=${ytVideoId}`;
    } else if (data.youtube_result.error) {
      updatesObj.status_yt = 'failed';
    }
  }
  
  // Facebook Status Update
  if (data.facebook_result) {
    if (data.facebook_result.success || data.facebook_result.id) {
      updatesObj.status_fb = 'published';
    } else if (data.facebook_result.error) {
      updatesObj.status_fb = 'failed';
    }
  }
  
  // Instagram Status Update
  if (data.instagram_result) {
    const igMediaId = data.instagram_result.id;
    if (igMediaId) {
      updatesObj.status_ig = `https://www.instagram.com/p/${igMediaId}`;
    } else if (data.instagram_result.error) {
      updatesObj.status_ig = 'failed';
    }
  }
  
  updates.push({ json: updatesObj });
}

return updates;
