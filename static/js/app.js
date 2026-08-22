(function () {
  let selectedFile = null;
  let lastResult = null;

  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const browseBtn = document.getElementById("browse-btn");
  const dropzoneEmpty = document.getElementById("dropzone-empty");
  const filePreview = document.getElementById("file-preview");
  const previewImg = document.getElementById("preview-img");
  const previewName = document.getElementById("preview-name");
  const analyzeBtn = document.getElementById("analyze-btn");
  const analyzeForm = document.getElementById("analyze-form");
  const loading = document.getElementById("loading");
  const tabResults = document.getElementById("tab-results");

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.disabled) return;
      switchTab(btn.dataset.tab);
      if (btn.dataset.tab === "research") loadAnalytics();
    });
  });

  function switchTab(name) {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
    document.querySelectorAll(".panel").forEach((p) => {
      p.classList.remove("active");
      p.classList.add("hidden");
    });
    const panel = document.getElementById("panel-" + name);
    panel.classList.add("active");
    panel.classList.remove("hidden");
    if (name === "results" && lastResult) {
      renderResults(lastResult);
    }
  }

  function setFile(file) {
    if (!file || !file.type.startsWith("image/")) return;
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      previewName.textContent = file.name;
      dropzoneEmpty.classList.add("hidden");
      filePreview.classList.remove("hidden");
      analyzeBtn.disabled = false;
    };
    reader.readAsDataURL(file);
  }

  dropzone.addEventListener("click", () => fileInput.click());
  browseBtn.addEventListener("click", (e) => { e.stopPropagation(); fileInput.click(); });
  fileInput.addEventListener("change", () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });
  dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.style.borderColor = "#3b82f6"; });
  dropzone.addEventListener("dragleave", () => { dropzone.style.borderColor = ""; });
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "";
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
  });

  analyzeForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    loading.classList.remove("hidden");
    const formData = new FormData(analyzeForm);
    formData.set("file", selectedFile);

    try {
      const res = await fetch("/api/analyze", { method: "POST", body: formData });
      let data;
      try {
        data = await res.json();
      } catch {
        loading.classList.add("hidden");
        analyzeBtn.disabled = false;
        alert("Server error — please try again");
        return;
      }
      loading.classList.add("hidden");
      analyzeBtn.disabled = false;

      if (!res.ok) {
        alert(data.error || "Analysis failed");
        return;
      }

      lastResult = data;
      renderResults(data);
      tabResults.disabled = false;
      switchTab("results");
    } catch (err) {
      loading.classList.add("hidden");
      analyzeBtn.disabled = false;
      console.error(err);
      alert("Network error — please try again");
    }
  });

  function renderResults(data) {
    if (!data) return;

    const viz = document.getElementById("result-viz");
    if (data.visualization) {
      viz.src = "data:image/png;base64," + data.visualization;
      viz.style.display = "block";
    }

    const p = data.patient || {};
    document.getElementById("patient-summary").innerHTML = `
      <dt>Patient ID</dt><dd>${esc(p.id || "—")}</dd>
      <dt>Sex</dt><dd>${esc(p.sex)}</dd>
      <dt>Age</dt><dd>${esc(p.age || "—")}</dd>
      <dt>OA Status</dt><dd>${esc(p.oa_status)}</dd>
      <dt>Case ID</dt><dd>${esc(data.case_id)}</dd>
    `;

    const ma = data.meniscus_analysis;
    const tbody = document.querySelector("#meniscus-table tbody");
    tbody.innerHTML = ma.oa_assessment.location_comparisons.map((c) => `
      <tr>
        <td>${esc(c.location)}</td>
        <td>${c.measured_mm}</td>
        <td>${c.reference_mm}</td>
        <td style="color:${c.below_reference ? '#ef4444' : '#22c55e'}">${c.difference_percent}%</td>
      </tr>
    `).join("");

    const oa = ma.oa_assessment;
    const oaBox = document.getElementById("oa-box");
    oaBox.className = "oa-box " + oa.ai_oa_likelihood.toLowerCase();
    oaBox.innerHTML = `
      <strong>AI OA Likelihood: ${oa.ai_oa_likelihood}</strong>
      <p>Mean meniscus thickness: <strong>${oa.mean_thickness_mm} mm</strong> (ref: ${oa.reference_mean_mm} mm)</p>
      <p>Reduction vs reference: ${oa.reduction_vs_reference_percent}%</p>
      <p class="muted">${oa.note}</p>
    `;

    const imp = data.implant_sizing;
    document.getElementById("bone-measurements").innerHTML = `
      <div class="bone-row"><span>Femoral width</span><strong>${imp.femoral.width_mm} mm</strong></div>
      <div class="bone-row"><span>Femoral AP</span><strong>${imp.femoral.ap_mm} mm</strong></div>
      <div class="bone-row"><span>Tibial width</span><strong>${imp.tibial.width_mm} mm</strong></div>
      <div class="bone-row"><span>Tibial AP</span><strong>${imp.tibial.ap_mm} mm</strong></div>
    `;

    document.getElementById("implant-rec").innerHTML = `
      <div class="rec-card"><span>Femoral</span><strong>Size ${imp.recommended_femoral.size}</strong><small>Score: ${imp.recommended_femoral.score}%</small></div>
      <div class="rec-card"><span>Tibial</span><strong>Size ${imp.recommended_tibial.size}</strong><small>Score: ${imp.recommended_tibial.score}%</small></div>
    `;

    document.getElementById("match-columns").innerHTML = `
      <div><h4>Femoral Matches</h4><div class="match-list">${renderMatches(imp.femoral_matches)}</div></div>
      <div><h4>Tibial Matches</h4><div class="match-list">${renderMatches(imp.tibial_matches)}</div></div>
    `;
  }

  function renderMatches(matches) {
    return matches.map((m) => `
      <div class="match-item">
        <span>Size ${m.size} (${m.width_mm}×${m.ap_mm}mm)</span>
        <span>${m.score}%</span>
      </div>
    `).join("");
  }

  async function loadAnalytics() {
    try {
      const res = await fetch("/api/analytics");
      const data = await res.json();

      const sg = document.getElementById("stats-grid");
      sg.innerHTML = `
        <div class="stat-card"><div class="val">${data.total_cases}</div><div class="lbl">Total Cases</div></div>
        <div class="stat-card"><div class="val">${data.by_sex?.male?.avg_meniscus_mm || 0}</div><div class="lbl">Male Avg (mm)</div></div>
        <div class="stat-card"><div class="val">${data.by_sex?.female?.avg_meniscus_mm || 0}</div><div class="lbl">Female Avg (mm)</div></div>
        <div class="stat-card"><div class="val">${data.by_oa_status?.oa?.avg_meniscus_mm || 0}</div><div class="lbl">OA Avg (mm)</div></div>
        <div class="stat-card"><div class="val">${data.by_oa_status?.non_oa?.avg_meniscus_mm || 0}</div><div class="lbl">Non-OA Avg (mm)</div></div>
      `;

      const tbody = document.querySelector("#cases-table tbody");
      const cases = data.recent_cases || [];
      tbody.innerHTML = cases.length
        ? cases.map((c) => `
          <tr>
            <td>${esc(c.patient_id || "—")}</td>
            <td>${esc(c.sex)}</td>
            <td>${esc(c.age || "—")}</td>
            <td>${esc(c.oa_status)}</td>
            <td>${c.mean_thickness_mm}</td>
            <td>${c.recommended_femoral_size}</td>
            <td>${c.recommended_tibial_size}</td>
          </tr>
        `).join("")
        : `<tr><td colspan="7" style="text-align:center;color:#8b9dc3">No cases yet — run an analysis first</td></tr>`;
    } catch {
      /* ignore */
    }
  }

  document.getElementById("new-analysis").addEventListener("click", () => {
    switchTab("analyze");
  });

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }
})();
