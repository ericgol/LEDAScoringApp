/**
 * LEDA Drone Scoring - Frontend Application
 *
 * Handles: session creation, folder/file selection, drag-and-drop,
 * image upload, and results display.
 */

(function () {
  "use strict";

  // --- State ---
  let sessionId = null;
  let sessionInfo = null;
  let selectedFiles = [];

  // --- DOM References ---
  const sessionForm = document.getElementById("session-form");
  const sessionSetup = document.getElementById("session-setup");
  const imageUpload = document.getElementById("image-upload");
  const resultsSection = document.getElementById("results-section");
  const courseSelect = document.getElementById("course_id");
  const courseInfo = document.getElementById("course-info");
  const uploadInfo = document.getElementById("upload-info");
  const maneuverSequence = document.getElementById("maneuver-sequence");
  const dropZone = document.getElementById("drop-zone");
  const filePreview = document.getElementById("file-preview");
  const fileCount = document.getElementById("file-count");
  const fileList = document.getElementById("file-list");
  const progressSection = document.getElementById("progress-section");
  const progressFill = document.getElementById("progress-fill");
  const progressText = document.getElementById("progress-text");
  const resultsSummary = document.getElementById("results-summary");
  const resultsDetail = document.getElementById("results-detail");

  // --- Course Selection ---
  courseSelect.addEventListener("change", function () {
    const opt = this.options[this.selectedIndex];
    if (!this.value) {
      courseInfo.classList.add("hidden");
      return;
    }
    courseInfo.classList.remove("hidden");
    courseInfo.innerHTML = `
      <p><strong>Total Images:</strong> ${opt.dataset.totalImages}
      &nbsp;|&nbsp; <strong>Time Limit:</strong> ${opt.dataset.timeLimit} min/maneuver
      &nbsp;|&nbsp; <strong>Maneuvers:</strong> ${opt.dataset.maneuvers}</p>
    `;
  });

  // --- Session Creation ---
  sessionForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    const formData = new FormData(sessionForm);
    const data = {};
    formData.forEach((v, k) => (data[k] = v));

    try {
      const res = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!res.ok) {
        const err = await res.json();
        alert("Error: " + (err.error || "Failed to create session"));
        return;
      }

      sessionInfo = await res.json();
      sessionId = sessionInfo.session_id;

      // Transition to upload step
      sessionSetup.classList.add("hidden");
      imageUpload.classList.remove("hidden");

      uploadInfo.innerHTML = `
        <strong>Session created.</strong> Course: ${sessionInfo.course}
        &mdash; Expected: <strong>${sessionInfo.total_images_expected}</strong> images
      `;

      // Show maneuver sequence reference
      renderManeuverSequence(sessionInfo.maneuvers);
    } catch (err) {
      alert("Network error: " + err.message);
    }
  });

  function renderManeuverSequence(maneuvers) {
    let html = "<h3>Expected Image Sequence</h3>";
    for (const m of maneuvers) {
      html += `<div class="maneuver-ref">
        <strong>${m.short_name} - ${m.name}</strong>: ${m.image_count} images
      </div>`;
    }
    maneuverSequence.innerHTML = html;
  }

  // --- File System Access API (SD Card Folder Picker) ---
  const btnFolderPicker = document.getElementById("btn-folder-picker");

  if ("showDirectoryPicker" in window) {
    btnFolderPicker.addEventListener("click", async function () {
      try {
        const dirHandle = await window.showDirectoryPicker({ mode: "read" });
        const files = [];

        for await (const entry of dirHandle.values()) {
          if (entry.kind === "file" && isImageFile(entry.name)) {
            const file = await entry.getFile();
            files.push(file);
          }
        }

        if (files.length === 0) {
          alert("No image files found in the selected folder.");
          return;
        }

        // Sort by filename (drone images are typically sequentially named)
        files.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
        addFiles(files);
      } catch (err) {
        if (err.name !== "AbortError") {
          alert("Error reading folder: " + err.message);
        }
      }
    });
  } else {
    btnFolderPicker.disabled = true;
    btnFolderPicker.title = "File System Access API not supported in this browser";
  }

  // --- Folder Fallback (webkitdirectory) ---
  const btnFolderFallback = document.getElementById("btn-folder-fallback");
  const folderInput = document.getElementById("folder-input");

  btnFolderFallback.addEventListener("click", () => folderInput.click());
  folderInput.addEventListener("change", function () {
    const files = Array.from(this.files).filter((f) => isImageFile(f.name));
    files.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
    addFiles(files);
    this.value = "";
  });

  // --- File Picker ---
  const btnFilePicker = document.getElementById("btn-file-picker");
  const fileInput = document.getElementById("file-input");

  btnFilePicker.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", function () {
    const files = Array.from(this.files).filter((f) => isImageFile(f.name));
    files.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
    addFiles(files);
    this.value = "";
  });

  // --- Drag and Drop ---
  dropZone.addEventListener("dragover", function (e) {
    e.preventDefault();
    e.stopPropagation();
    this.classList.add("drag-over");
  });

  dropZone.addEventListener("dragleave", function (e) {
    e.preventDefault();
    e.stopPropagation();
    this.classList.remove("drag-over");
  });

  dropZone.addEventListener("drop", function (e) {
    e.preventDefault();
    e.stopPropagation();
    this.classList.remove("drag-over");

    const files = Array.from(e.dataTransfer.files).filter((f) => isImageFile(f.name));
    files.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
    addFiles(files);
  });

  // --- File Management ---
  function isImageFile(name) {
    const ext = name.split(".").pop().toLowerCase();
    return ["jpg", "jpeg", "png", "tiff", "tif", "bmp", "dng", "raw"].includes(ext);
  }

  function addFiles(newFiles) {
    selectedFiles = selectedFiles.concat(newFiles);
    renderFileList();
  }

  function renderFileList() {
    if (selectedFiles.length === 0) {
      filePreview.classList.add("hidden");
      return;
    }

    filePreview.classList.remove("hidden");
    fileCount.textContent = selectedFiles.length;

    const expected = sessionInfo ? sessionInfo.total_images_expected : "?";
    const countClass =
      selectedFiles.length === expected ? "count-match" : "count-mismatch";

    fileList.innerHTML = selectedFiles
      .map(
        (f, i) => `
      <div class="file-item">
        <span class="file-index">${i + 1}</span>
        <span class="file-name">${f.name}</span>
        <span class="file-size">${formatSize(f.size)}</span>
        <button type="button" class="btn-remove" data-index="${i}" title="Remove">&times;</button>
      </div>
    `
      )
      .join("");

    // Add count indicator
    fileCount.className = countClass;

    // Bind remove buttons
    fileList.querySelectorAll(".btn-remove").forEach((btn) => {
      btn.addEventListener("click", function () {
        selectedFiles.splice(parseInt(this.dataset.index), 1);
        renderFileList();
      });
    });
  }

  function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1048576).toFixed(1) + " MB";
  }

  // --- Clear Files ---
  document.getElementById("btn-clear-files").addEventListener("click", function () {
    selectedFiles = [];
    renderFileList();
  });

  // --- Upload & Analyze ---
  document.getElementById("btn-analyze").addEventListener("click", async function () {
    if (!sessionId) {
      alert("Please create a session first.");
      return;
    }
    if (selectedFiles.length === 0) {
      alert("No files selected.");
      return;
    }

    // Show progress
    progressSection.classList.remove("hidden");
    progressFill.style.width = "0%";
    progressText.textContent = "Starting upload...";
    this.disabled = true;

    const total = selectedFiles.length;
    const allResults = [];
    let lastSummary = null;
    let errorCount = 0;

    for (let i = 0; i < total; i++) {
      const file = selectedFiles[i];
      const pct = Math.round((i / total) * 100);
      progressFill.style.width = pct + "%";
      progressText.textContent =
        `Analyzing image ${i + 1} of ${total}: ${file.name}`;

      const fd = new FormData();
      fd.append("session_id", sessionId);
      fd.append("image_index", i);
      fd.append("file", file);

      try {
        const res = await fetch("/api/analyze/image", {
          method: "POST",
          body: fd,
        });

        if (res.ok) {
          const data = await res.json();
          allResults.push(data.result);
          lastSummary = data.summary;
        } else {
          errorCount++;
          // Push a placeholder so image_index alignment is preserved
          allResults.push({
            image_index: i,
            filename: file.name,
            maneuver_id: "unknown",
            maneuver_name: "Unknown",
            step_number: i + 1,
            expected_bucket: "?",
            instruction: "Error processing this image",
            analysis: { caption: "", tags: [] },
            score: { result: "pending", reason: "Upload or analysis error" },
          });
        }
      } catch (err) {
        errorCount++;
        allResults.push({
          image_index: i,
          filename: file.name,
          maneuver_id: "unknown",
          maneuver_name: "Unknown",
          step_number: i + 1,
          expected_bucket: "?",
          instruction: "Network error",
          analysis: { caption: "", tags: [] },
          score: { result: "pending", reason: "Network error: " + err.message },
        });
      }
    }

    progressFill.style.width = "100%";
    progressText.textContent =
      errorCount > 0
        ? `Analysis complete with ${errorCount} error(s).`
        : "Analysis complete!";

    // Build a client-side summary if the server never returned one
    if (!lastSummary) {
      const scores = allResults.map((r) => r.score);
      lastSummary = {
        total_images: scores.length,
        passed: scores.filter((s) => s.result === "pass").length,
        failed: scores.filter((s) => s.result === "fail").length,
        needs_review: scores.filter((s) => s.result === "needs_review").length,
        pending: scores.filter((s) => s.result === "pending").length,
        pass_rate: 0,
        overall_result: "incomplete",
      };
    }

    renderResults({
      session_id: sessionId,
      images_processed: allResults.length,
      images_expected: sessionInfo ? sessionInfo.total_images_expected : total,
      results: allResults,
      summary: lastSummary,
    });
  });

  // --- Render Results ---
  function renderResults(data) {
    imageUpload.classList.add("hidden");
    resultsSection.classList.remove("hidden");

    const s = data.summary;
    resultsSummary.innerHTML = `
      <div class="results-summary-box">
        <div class="summary-stats">
          <div class="stat">
            <span class="stat-value">${s.total_images}</span>
            <span class="stat-label">Total</span>
          </div>
          <div class="stat stat-pass">
            <span class="stat-value">${s.passed}</span>
            <span class="stat-label">Passed</span>
          </div>
          <div class="stat stat-fail">
            <span class="stat-value">${s.failed}</span>
            <span class="stat-label">Failed</span>
          </div>
          <div class="stat stat-review">
            <span class="stat-value">${s.needs_review}</span>
            <span class="stat-label">Needs Review</span>
          </div>
        </div>
        <p>Images processed: ${data.images_processed} / ${data.images_expected} expected</p>
        <p><a href="/api/results/${data.session_id}" class="btn btn-secondary">View Full Report</a></p>
      </div>
    `;

    resultsDetail.innerHTML = data.results
      .map(
        (r) => `
      <div class="image-result-card result-${r.score.result === "pass" ? "pass" : r.score.result === "fail" ? "fail" : "review"}">
        <div class="image-result-header">
          <span class="image-index">#${r.image_index + 1}</span>
          <span class="maneuver-name">${r.maneuver_name}</span>
          <span class="expected-bucket">Bucket: ${r.expected_bucket}</span>
          <span class="score-badge score-${r.score.result}">${r.score.result.toUpperCase()}</span>
        </div>
        <div class="image-result-body">
          <p class="instruction">${r.instruction}</p>
          <p><strong>File:</strong> ${r.filename}</p>
          <p><strong>Caption:</strong> ${r.analysis.caption || "N/A"}</p>
          ${
            r.analysis.tags && r.analysis.tags.length
              ? `<p><strong>Tags:</strong> ${r.analysis.tags
                  .slice(0, 8)
                  .map((t) => `<span class="tag">${t.name} (${Math.round(t.confidence * 100)}%)</span>`)
                  .join(" ")}</p>`
              : ""
          }
        </div>
      </div>
    `
      )
      .join("");
  }
})();
