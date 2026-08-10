/**
 * ==============================================================================
 * UNIFIED MASTER GOOGLE APPS SCRIPT
 * Dùng chung cho 3 Dự Án trên 1 File Google Sheet Duy Nhất:
 *   1. Omni-Video          (Tab "Omni-Video")
 *   2. Auto-Video-Factory  (Tab "Auto-Video-Factory", "Video-Factory-SCENES", "Video-Factory-EFFECTS")
 *   3. Video-Post          (Tab "Master")
 * ==============================================================================
 */

// Tên các Tab chuẩn trong Single Workbook
var TAB_OMNI = "Omni-Video";
var TAB_FACTORY_PROJECTS = "Auto-Video-Factory";
var TAB_FACTORY_SCENES = "Video-Factory-SCENES";
var TAB_FACTORY_EFFECTS = "Video-Factory-EFFECTS";
var TAB_MASTER_POST = "Master";

var INPUT_TABS = [TAB_OMNI, TAB_FACTORY_PROJECTS];

var MASTER_HEADERS = [
  "job_id", "title", "video_path", "shopee_link",
  "caption_fb", "caption_yt", "caption_ig", "caption_tt", "caption_shopee", "caption_zalo",
  "brand_fb", "brand_yt", "brand_ig",
  "status_fb", "status_yt", "status_ig", "status_tt", "status_shopee", "status_zalo"
];

function doGet(e) {
  try {
    var action = (e && e.parameter && e.parameter.action) ? e.parameter.action : "";
    if (action === "sync_input_tabs") {
      var syncRes = syncInputTabsToMaster();
      return responseJSON({ status: "success", result: syncRes });
    }
    return ContentService.createTextOutput("⚡ Unified Master Webhook (Omni-Video + Auto-Video-Factory + Video-Post) is Active!");
  } catch (err) {
    return responseJSON({ status: "error", message: err.toString() });
  }
}

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return responseJSON({ status: "error", message: "Empty post body" });
    }

    var data = JSON.parse(e.postData.contents);
    var action = data.action;
    var ss = SpreadsheetApp.getActiveSpreadsheet();

    ensureSheetsAndHeaders(ss);

    if (action === "sync_project") {
      updateProjectTracker(ss, data.project);
      syncInputTabsToMaster();
      return responseJSON({ status: "success", message: "Đã đồng bộ dự án Auto-Video-Factory và cập nhật tab Master" });
    } 
    else if (action === "sync_scenes") {
      updateScenesDetail(ss, data.projectId, data.scenes);
      return responseJSON({ status: "success", message: "Đã đồng bộ scenes vào Video-Factory-SCENES" });
    } 
    else if (action === "sync_analytics") {
      updateEffectsAnalytics(ss, data.analytics);
      return responseJSON({ status: "success", message: "Đã đồng bộ analytics vào Video-Factory-EFFECTS" });
    }
    else if (action === "get_all_products") {
      var targetTab = data.sheetName || TAB_OMNI;
      var sheet = ss.getSheetByName(targetTab) || ss.getSheetByName(TAB_OMNI);
      var rows = sheet.getDataRange().getValues();
      var productsMap = {};

      for (var i = 1; i < rows.length; i++) {
        var itemId = String(rows[i][0]).trim();
        if (itemId) {
          productsMap[itemId] = {
            itemId: itemId,
            jobId: itemId,
            productName: String(rows[i][1] || "").trim(),
            title: String(rows[i][1] || "").trim(),
            price: String(rows[i][2] || "").trim(),
            salesCount: String(rows[i][3] || "").trim(),
            shopName: String(rows[i][4] || "").trim(),
            productUrl: String(rows[i][7] || "").trim(),
            shopeeLink: String(rows[i][8] || "").trim(),
            cdnUrl: String(rows[i][9] || "").trim(),
            localPath: String(rows[i][10] || "").trim(),
            status: String(rows[i][11] || "").trim(),
            outputFile: String(rows[i][12] || "").trim(),
            videoPath: String(rows[i][12] || "").trim(),
            brandFb: String(rows[i][13] || "").trim(),
            brandYt: String(rows[i][14] || "").trim(),
            brandIg: String(rows[i][15] || "").trim(),
            brandTt: String(rows[i][16] || "").trim(),
            brandShopee: String(rows[i][17] || "").trim(),
            brandZalo: String(rows[i][18] || "").trim()
          };
        }
      }
      return responseJSON({ status: "success", products: productsMap });
    }
    else if (action === "update_status") {
      var targetId = String(data.itemId || data.jobId || data.projectId).trim();
      var targetTab = data.sheetName || TAB_OMNI;
      var sheet = ss.getSheetByName(targetTab) || ss.getSheetByName(TAB_OMNI);
      var rows = sheet.getDataRange().getValues();
      var updated = false;

      for (var j = 1; j < rows.length; j++) {
        if (String(rows[j][0]).trim() === targetId) {
          var newStatus = data.status || "Đã tạo Video";
          var videoFile = data.outputFile || data.videoPath || "";
          var statusCol = (targetTab === TAB_OMNI) ? 12 : 2;
          sheet.getRange(j + 1, statusCol).setValue(newStatus);
          if (videoFile) {
            var pathCol = (targetTab === TAB_OMNI) ? 13 : 11;
            sheet.getRange(j + 1, pathCol).setValue(videoFile);
          }
          updated = true;
          break;
        }
      }

      syncInputTabsToMaster();

      if (updated) {
        return responseJSON({ status: "success", message: "Đã cập nhật trạng thái mã " + targetId + " ở tab " + targetTab });
      } else {
        return responseJSON({ status: "error", message: "Không tìm thấy mã " + targetId + " ở tab " + targetTab });
      }
    }
    else if (action === "import_csv_text" && data.csvText) {
      var targetTab = data.sheetName || TAB_OMNI;
      var sheet = ss.getSheetByName(targetTab) || ss.getSheetByName(TAB_OMNI);
      var msg = processCSVTextImport(sheet, data.csvText, targetTab);
      return responseJSON({ status: "success", message: msg });
    }
    else if (action === "sync_input_tabs") {
      var res = syncInputTabsToMaster();
      return responseJSON({ status: "success", result: res });
    }
    else if (action === "update_rows" || action === "upsert_rows") {
      var masterSheet = ss.getSheetByName(TAB_MASTER_POST);
      var records = data.records || [];
      var existingData = masterSheet.getDataRange().getValues();
      var idRowMap = {};

      for (var r = 1; r < existingData.length; r++) {
        var id = String(existingData[r][0]).trim();
        if (id) idRowMap[id] = r + 1;
      }

      records.forEach(function(rec) {
        var rowData = MASTER_HEADERS.map(function(h) {
          return rec[h] !== undefined ? rec[h] : "";
        });
        var targetRow = idRowMap[String(rec.job_id).trim()];
        if (targetRow) {
          masterSheet.getRange(targetRow, 1, 1, MASTER_HEADERS.length).setValues([rowData]);
        } else {
          masterSheet.appendRow(rowData);
        }
      });
      return responseJSON({ status: "success", count: records.length });
    }

    var itemId = String(data.itemId || "").trim();
    if (itemId && (data.cdnUrl || data.productUrl)) {
      var omniSheet = ss.getSheetByName(TAB_OMNI);
      var rows = omniSheet.getDataRange().getValues();
      var rowIndex = -1;

      for (var i = 1; i < rows.length; i++) {
        var cellVal = String(rows[i][0]).trim();
        var cellUrl = String(rows[i][7] || "").trim();
        if (cellVal === itemId || (cellUrl && cellUrl.includes(itemId))) {
          rowIndex = i + 1;
          break;
        }
      }

      var localPath = "Product_Assets/" + itemId + "/";
      if (rowIndex > 0) {
        if (data.cdnUrl) omniSheet.getRange(rowIndex, 10).setValue(data.cdnUrl);
        omniSheet.getRange(rowIndex, 11).setValue(localPath);
        var curSt = String(omniSheet.getRange(rowIndex, 12).getValue() || "").trim();
        if (curSt !== "Đã tạo Video" && curSt !== "Đã tạo Prompt") {
          omniSheet.getRange(rowIndex, 12).setValue("Đã chọn ảnh");
        }
        return responseJSON({ status: "success", message: "Đã cập nhật ảnh cho mã " + itemId + " dòng " + rowIndex });
      } else {
        var newRow = [
          itemId, data.productName || "Sản phẩm mới", data.price || "", data.salesCount || "",
          data.shopName || "", "", "", data.productUrl || "", data.productUrl || "",
          data.cdnUrl || "", localPath, "Đã chọn ảnh", "", "", "", "", "", "", ""
        ];
        omniSheet.appendRow(newRow);
        return responseJSON({ status: "success", message: "Đã thêm sản phẩm mới mã " + itemId });
      }
    }

    return responseJSON({ status: "error", message: "Unknown action: " + action });
  } catch (err) {
    return responseJSON({ status: "error", message: err.toString() });
  }
}

function ensureSheetsAndHeaders(ss) {
  let sheetOmni = ss.getSheetByName(TAB_OMNI);
  if (!sheetOmni) {
    sheetOmni = ss.insertSheet(TAB_OMNI);
    const headers = [
      "job_id", "title", "Giá", "Doanh thu", "Tên cửa hàng", "Tỉ lệ hoa hồng", "Hoa hồng",
      "link", "shopee_link", "Link ảnh CDN chọn lọc", "File ảnh lưu local",
      "Trạng thái Master Prompt", "video_path", "brand_fb", "brand_yt", "brand_ig", "brand_tt", "brand_shopee", "brand_zalo"
    ];
    sheetOmni.appendRow(headers);
    formatHeaderRow(sheetOmni, "#1F4E78");
  }

  let sheetFactory = ss.getSheetByName(TAB_FACTORY_PROJECTS);
  if (!sheetFactory) {
    sheetFactory = ss.insertSheet(TAB_FACTORY_PROJECTS);
    const headers = [
      "job_id", "Status", "Input File", "title", "raw_caption", "Original Duration",
      "Short Duration", "Scene Count", "Opening Hook Score", "Effects Summary", "video_path",
      "Created At", "Rendered At", "brand_fb", "brand_yt", "brand_ig", "brand_tt", "brand_shopee", "brand_zalo"
    ];
    sheetFactory.appendRow(headers);
    formatHeaderRow(sheetFactory, "#2E75B6");
  }

  let sheetScenes = ss.getSheetByName(TAB_FACTORY_SCENES);
  if (!sheetScenes) {
    sheetScenes = ss.insertSheet(TAB_FACTORY_SCENES);
    const headers = [
      "Project ID", "Scene ID", "Scene Type", "Time (Start-End)", "Target Duration",
      "Subtitle (IN HOA)", "Voice Text", "Visual Cue", "Subtitle Style",
      "Advanced Effect", "Transition Out"
    ];
    sheetScenes.appendRow(headers);
    formatHeaderRow(sheetScenes, "#002060");
  }

  let sheetEffects = ss.getSheetByName(TAB_FACTORY_EFFECTS);
  if (!sheetEffects) {
    sheetEffects = ss.insertSheet(TAB_FACTORY_EFFECTS);
    const headers = ["Effect Key", "Success Count", "Fail Count", "Success Rate (%)", "Safe Pool Status"];
    sheetEffects.appendRow(headers);
    formatHeaderRow(sheetEffects, "#548235");
  }

  let sheetMaster = ss.getSheetByName(TAB_MASTER_POST);
  if (!sheetMaster) {
    sheetMaster = ss.insertSheet(TAB_MASTER_POST);
    sheetMaster.appendRow(MASTER_HEADERS);
    formatHeaderRow(sheetMaster, "#C65911");
  }
}

function formatHeaderRow(sheet, backgroundColor) {
  const range = sheet.getRange(1, 1, 1, sheet.getLastColumn());
  range.setFontWeight("bold");
  range.setFontColor("#FFFFFF");
  range.setBackground(backgroundColor);
  sheet.setFrozenRows(1);
}

function updateProjectTracker(ss, p) {
  const sheet = ss.getSheetByName(TAB_FACTORY_PROJECTS);
  const data = sheet.getDataRange().getValues();

  let rowIndex = -1;
  const pId = String(p.projectId || p.job_id || p.jobId).trim();

  for (let i = 1; i < data.length; i++) {
    if (String(data[i][0]).trim() === pId) {
      rowIndex = i + 1;
      break;
    }
  }

  const rowValues = [
    pId,
    p.status || p.Status || "",
    p.inputFile || p.input_file || "",
    p.title || "",
    p.rawCaption || p.captionHashtags || p.raw_caption || "",
    p.originalDuration || p.original_duration || "",
    p.shortDuration || p.short_duration || "",
    p.sceneCount || p.scene_count || "",
    p.hookScore || p.hook_score || "",
    p.effectsSummary || p.effects_summary || "",
    p.outputFile || p.video_path || "",
    p.createdAt || p.created_at || "",
    p.renderedAt || p.rendered_at || "",
    p.brandFb || p.brand_fb || "",
    p.brandYt || p.brand_yt || "",
    p.brandIg || p.brand_ig || "",
    p.brandTt || p.brand_tt || "",
    p.brandShopee || p.brand_shopee || "",
    p.brandZalo || p.brand_zalo || ""
  ];

  if (rowIndex > 0) {
    for (let c = 0; c < rowValues.length; c++) {
      if (rowValues[c] !== "" && rowValues[c] !== undefined) {
        sheet.getRange(rowIndex, c + 1).setValue(rowValues[c]);
      }
    }
  } else {
    sheet.appendRow(rowValues);
  }
}

function updateScenesDetail(ss, projectId, scenes) {
  if (!scenes || !Array.isArray(scenes)) return;
  const sheet = ss.getSheetByName(TAB_FACTORY_SCENES);
  const data = sheet.getDataRange().getValues();
  const pId = String(projectId).trim();

  for (let i = data.length - 1; i >= 1; i--) {
    if (String(data[i][0]).trim() === pId) {
      sheet.deleteRow(i + 1);
    }
  }

  for (const s of scenes) {
    const advEffectName = typeof s.advanced_effect === "object" ? s.advanced_effect?.name : s.advanced_effect;
    const transOutType = s.transition_out ? `${s.transition_out.type} (${s.transition_out.duration}s)` : "none";
    const startVal = s.start_s !== undefined ? s.start_s : s.start;
    const endVal = s.end_s !== undefined ? s.end_s : s.end;
    const durVal = s.duration_s !== undefined ? s.duration_s : s.duration;

    const row = [
      pId,
      s.scene_id || s.id || "",
      s.scene_type || "body",
      `${startVal || 0}s - ${endVal || 0}s`,
      `${durVal || 0}s`,
      s.text_content || s.subtitle || s.text || "",
      s.voice || s.voiceover || "",
      s.visual_description || s.visual_cue || s.description || "",
      `${s.subtitle_style || "default"} (${s.text_position || "bottom"})`,
      `${advEffectName || "none"} (${s.advanced_effect?.camera_motion || "static"})`,
      transOutType
    ];
    sheet.appendRow(row);
  }
}

function updateEffectsAnalytics(ss, analytics) {
  if (!analytics || !Array.isArray(analytics)) return;
  const sheet = ss.getSheetByName(TAB_FACTORY_EFFECTS);
  const lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    sheet.getRange(2, 1, lastRow - 1, sheet.getLastColumn()).clearContent();
  }

  for (const item of analytics) {
    const total = (item.success || 0) + (item.fail || 0);
    const rate = total > 0 ? ((item.success / total) * 100).toFixed(1) + "%" : "0%";
    const status = (item.success >= 5 && (item.success / Math.max(1, total)) >= 0.9) ? "✅ Safe (Sử dụng)" : "⚠️ Restricted";

    sheet.appendRow([
      item.key,
      item.success || 0,
      item.fail || 0,
      rate,
      status
    ]);
  }
}

function syncInputTabsToMaster() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var masterSheet = ss.getSheetByName(TAB_MASTER_POST);
  if (!masterSheet) {
    masterSheet = ss.insertSheet(TAB_MASTER_POST);
    masterSheet.appendRow(MASTER_HEADERS);
  }

  var activeInputJobsMap = {};
  var activeJobIdsList = [];

  INPUT_TABS.forEach(function(tabName) {
    var sheet = ss.getSheetByName(tabName);
    if (!sheet) return;

    var values = sheet.getDataRange().getValues();
    if (values.length < 2) return;

    var headers = values[0].map(function(h) { return String(h).trim().toLowerCase(); });
    
    function findIdx(possibleNames) {
      for (var p = 0; p < possibleNames.length; p++) {
        for (var i = 0; i < headers.length; i++) {
          if (headers[i] === possibleNames[p].toLowerCase()) return i;
        }
      }
      return -1;
    }

    var idIdx = findIdx(["job_id", "mã sản phẩm", "project id", "sku", "id"]);
    var titleIdx = findIdx(["title", "tên sản phẩm", "video title", "tiêu đề"]);
    var rawCapIdx = findIdx(["raw_caption", "mô tả bài đăng", "caption & hashtags", "caption"]);
    var videoPathIdx = findIdx(["video_path", "output file", "đường dẫn video"]);
    var shopeeLinkIdx = findIdx(["shopee_link", "link ưu đãi", "affiliate link", "link sản phẩm"]);
    var brandFbIdx = findIdx(["brand_fb", "fanpage facebook"]);
    var brandYtIdx = findIdx(["brand_yt", "kênh youtube"]);
    var brandIgIdx = findIdx(["brand_ig", "tài khoản instagram"]);

    for (var r = 1; r < values.length; r++) {
      var row = values[r];
      var jobId = idIdx !== -1 ? String(row[idIdx]).trim() : "";
      var videoPath = videoPathIdx !== -1 ? String(row[videoPathIdx]).trim() : "";
      
      if (!jobId && !videoPath) continue;
      if (!jobId) jobId = "JOB_" + r;

      if (!activeInputJobsMap[jobId]) {
        activeInputJobsMap[jobId] = {
          job_id: jobId,
          title: titleIdx !== -1 ? String(row[titleIdx]).trim() : "",
          raw_caption: rawCapIdx !== -1 ? String(row[rawCapIdx]).trim() : "",
          video_path: videoPath,
          shopee_link: shopeeLinkIdx !== -1 ? String(row[shopeeLinkIdx]).trim() : "",
          brand_fb: brandFbIdx !== -1 ? String(row[brandFbIdx]).trim() : "",
          brand_yt: brandYtIdx !== -1 ? String(row[brandYtIdx]).trim() : "",
          brand_ig: brandIgIdx !== -1 ? String(row[brandIgIdx]).trim() : ""
        };
        activeJobIdsList.push(jobId);
      }
    }
  });

  var masterValues = masterSheet.getDataRange().getValues();
  var existingMasterIdsMap = {};

  for (var m = 1; m < masterValues.length; m++) {
    var mRow = masterValues[m];
    var mId = String(mRow[0]).trim();
    if (mId) existingMasterIdsMap[mId] = mRow;
  }

  var rowsToAddCount = 0;
  var newMasterTable = [MASTER_HEADERS];

  for (var k = 0; k < activeJobIdsList.length; k++) {
    var jId = activeJobIdsList[k];
    var inputJob = activeInputJobsMap[jId];

    if (existingMasterIdsMap[jId]) {
      var oldRow = existingMasterIdsMap[jId];
      var updatedRow = [
        inputJob.job_id,
        inputJob.title || oldRow[1],
        inputJob.video_path || oldRow[2],
        inputJob.shopee_link || oldRow[3],
        oldRow[4], oldRow[5], oldRow[6], oldRow[7], oldRow[8], oldRow[9],
        inputJob.brand_fb || oldRow[10],
        inputJob.brand_yt || oldRow[11],
        inputJob.brand_ig || oldRow[12],
        oldRow[13] || "needs_edit",
        oldRow[14] || "needs_edit",
        oldRow[15] || "needs_edit",
        oldRow[16] || "needs_edit",
        oldRow[17] || "needs_edit",
        oldRow[18] || "needs_edit"
      ];
      newMasterTable.push(updatedRow);
    } else {
      rowsToAddCount++;
      var initialCaption = inputJob.title + (inputJob.raw_caption ? "\n" + inputJob.raw_caption : "");
      var newRow = [
        inputJob.job_id,
        inputJob.title,
        inputJob.video_path,
        inputJob.shopee_link,
        initialCaption, initialCaption, initialCaption, initialCaption, initialCaption, initialCaption,
        inputJob.brand_fb, inputJob.brand_yt, inputJob.brand_ig,
        "needs_edit", "needs_edit", "needs_edit", "needs_edit", "needs_edit", "needs_edit"
      ];
      newMasterTable.push(newRow);
    }
  }

  masterSheet.clearContents();
  if (newMasterTable.length > 0) {
    masterSheet.getRange(1, 1, newMasterTable.length, MASTER_HEADERS.length).setValues(newMasterTable);
  }

  return {
    active_input_jobs: activeJobIdsList.length,
    new_jobs_added: rowsToAddCount,
    master_total_rows: newMasterTable.length - 1
  };
}

function processCSVTextImport(sheet, csvText, targetSheetName) {
  var existingData = sheet.getDataRange().getValues();
  var existingItemIds = new Set();
  
  for (var i = 1; i < existingData.length; i++) {
    var itemId = String(existingData[i][0] || "").trim();
    if (itemId) existingItemIds.add(itemId);
  }
  
  var rows = parseCSV(csvText);
  if (rows.length === 0) return "File CSV trống!";
  
  var addedCount = 0;
  var skippedCount = 0;
  var startIndex = (rows[0][0] && (rows[0][0].includes("Mã") || rows[0][0].includes("job_id"))) ? 1 : 0;
  
  for (var k = startIndex; k < rows.length; k++) {
    var r = rows[k];
    if (!r || r.length < 2) continue;
    
    var rawItemId = String(r[0] || "").trim();
    if (rawItemId && existingItemIds.has(rawItemId)) {
      skippedCount++;
    } else {
      var folderPath = rawItemId ? ("Product_Assets/" + rawItemId + "/") : "";
      var newRow = [
        rawItemId, r[1] || "", r[2] || "", r[3] || "", r[4] || "", r[5] || "", r[6] || "",
        r[7] || "", r[8] || "", "", folderPath, "Chưa chọn ảnh", "", "", "", "", "", "", ""
      ];
      sheet.appendRow(newRow);
      if (rawItemId) existingItemIds.add(rawItemId);
      addedCount++;
    }
  }
  
  return "✅ Đã thêm " + addedCount + " sản phẩm vào tab " + targetSheetName + "! (Lọc bỏ " + skippedCount + " trùng)";
}

function parseCSV(text) {
  var p = '', c = '', r = [];
  var q = false;
  var row = [''];
  for (var i = 0; i < text.length; i++) {
    c = text[i]; p = text[i - 1];
    if (c === '"') {
      if (q && text[i + 1] === '"') { row[row.length - 1] += '"'; i++; }
      else { q = !q; }
    } else if (c === ',' && !q) { row.push(''); }
    else if ((c === '\r' || c === '\n') && !q) {
      if (c === '\r' && text[i + 1] === '\n') { i++; }
      r.push(row); row = [''];
    } else { row[row.length - 1] += c; }
  }
  if (row.length > 1 || row[0] !== '') r.push(row);
  return r;
}

function responseJSON(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
