let discoveredLeads = [];

document.addEventListener("DOMContentLoaded", () => {
  const companyInput = document.getElementById("company-input");
  const maxResultsInput = document.getElementById("max-results");
  const searchBtn = document.getElementById("search-btn");
  const btnText = document.getElementById("btn-text");
  const btnSpinner = document.getElementById("btn-spinner");
  const emptyState = document.getElementById("empty-state");
  const leadsList = document.getElementById("leads-list");
  const leadCount = document.getElementById("lead-count");
  const exportCsvBtn = document.getElementById("export-csv-btn");
  
  // Modal Elements
  const modal = document.getElementById("outreach-modal");
  const closeModal = document.getElementById("close-modal");
  const modalLeadName = document.getElementById("modal-lead-name");
  const notePreview = document.getElementById("note-preview");
  const inmailSubject = document.getElementById("inmail-subject");
  const inmailBody = document.getElementById("inmail-body");
  const copyNoteBtn = document.getElementById("copy-note-btn");
  const copyInmailBtn = document.getElementById("copy-inmail-btn");

  // Toggle role pills
  document.querySelectorAll(".pill").forEach(pill => {
    pill.addEventListener("click", (e) => {
      const checkbox = pill.querySelector("input");
      if (e.target !== checkbox) checkbox.checked = !checkbox.checked;
      pill.classList.toggle("active", checkbox.checked);
    });
  });

  // Quick Intel Audit Handler
  const quickIntelBtn = document.getElementById("quick-intel-btn");
  if (quickIntelBtn) {
    quickIntelBtn.addEventListener("click", () => {
      const rawInput = companyInput.value.trim();
      if (!rawInput) {
        alert("Please enter a target company name or domain first.");
        return;
      }
      const firstCompany = rawInput.split("\n")[0].trim();
      openIntelModal(firstCompany);
    });
  }

  // Search Button Click Handler

  searchBtn.addEventListener("click", async () => {
    const rawInput = companyInput.value.trim();
    if (!rawInput) {
      alert("Please enter at least one target company name or domain.");
      return;
    }

    const companies = rawInput.split("\n").map(c => c.trim()).filter(Boolean);
    const maxResults = parseInt(maxResultsInput.value) || 5;

    // Selected titles
    const selectedTitles = Array.from(document.querySelectorAll(".pill input:checked")).map(cb => cb.value);

    // UI Loading State
    searchBtn.disabled = true;
    btnText.textContent = "Scanning LinkedIn...";
    btnSpinner.classList.remove("hidden");

    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          companies: companies,
          target_titles: selectedTitles.length ? selectedTitles : null,
          max_results_per_company: maxResults
        })
      });

      const data = await response.json();
      discoveredLeads = data.leads || [];
      renderLeads(discoveredLeads);

    } catch (err) {
      console.error("Search error:", err);
      alert("Failed to connect to search backend server.");
    } finally {
      searchBtn.disabled = false;
      btnText.textContent = "🔍 Find Decision Makers";
      btnSpinner.classList.add("hidden");
    }
  });

  // Render Leads Function
  function renderLeads(leads) {
    leadCount.textContent = leads.length;
    exportCsvBtn.disabled = leads.length === 0;

    if (leads.length === 0) {
      emptyState.classList.remove("hidden");
      leadsList.classList.add("hidden");
      return;
    }

    emptyState.classList.add("hidden");
    leadsList.classList.remove("hidden");
    leadsList.innerHTML = "";

    leads.forEach((lead, idx) => {
      const item = document.createElement("div");
      item.className = "lead-item";

      item.innerHTML = `
        <div class="lead-info">
          <div class="lead-name">${escapeHtml(lead.name)}</div>
          <div class="lead-title">${escapeHtml(lead.title)} • <span class="lead-company">${escapeHtml(lead.company)}</span></div>
        </div>
        <div class="lead-actions">
          <button class="action-btn view-intel" data-company="${escapeHtml(lead.company)}">🛡️ Company Intel</button>
          <button class="action-btn view-outreach" data-index="${idx}">📝 Outreach Copy</button>
          <a href="${escapeHtml(lead.linkedin_url)}" target="_blank" rel="noopener" class="action-btn">🔗 LinkedIn</a>
        </div>
      `;
      leadsList.appendChild(item);
    });

    // Attach outreach view listeners
    document.querySelectorAll(".view-outreach").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const index = e.target.getAttribute("data-index");
        openOutreachModal(discoveredLeads[index]);
      });
    });

    // Attach intel view listeners
    document.querySelectorAll(".view-intel").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const company = e.target.getAttribute("data-company");
        openIntelModal(company);
      });
    });
  }

  // Intel Modal handlers
  const intelModal = document.getElementById("intel-modal");
  const closeIntelModal = document.getElementById("close-intel-modal");
  const intelCompanyName = document.getElementById("intel-company-name");
  const intelSpinner = document.getElementById("intel-spinner");
  const intelContent = document.getElementById("intel-content");
  const intelWeakspots = document.getElementById("intel-weakspots");
  const intelPitchAngle = document.getElementById("intel-pitch-angle");
  const intelCompetitors = document.getElementById("intel-competitors");

  closeIntelModal.addEventListener("click", () => intelModal.classList.add("hidden"));
  intelModal.addEventListener("click", (e) => {
    if (e.target === intelModal) intelModal.classList.add("hidden");
  });

  async function openIntelModal(company) {
    if (!company) return;
    intelCompanyName.textContent = `360° Intelligence & Competitor Audit for ${company}`;
    intelModal.classList.remove("hidden");
    intelSpinner.classList.remove("hidden");
    intelContent.classList.add("hidden");

    try {
      const res = await fetch(`/api/company/intel?company=${encodeURIComponent(company)}`);
      const data = await res.json();
      
      // Render Weak Spots
      intelWeakspots.innerHTML = "";
      const weakSpots = data.analysis?.weak_spots || [];
      if (weakSpots.length === 0) {
        intelWeakspots.innerHTML = `<span class="badge badge-success">No critical digital weak spots detected</span>`;
      } else {
        weakSpots.forEach(ws => {
          intelWeakspots.innerHTML += `<div class="badge badge-danger"><strong>${escapeHtml(ws.category)}:</strong> ${escapeHtml(ws.issue)}</div>`;
        });
      }

      // Pitch angle
      intelPitchAngle.textContent = (data.analysis?.pitch_hooks || [])[0] || "No pitch angle generated";

      // Competitors
      intelCompetitors.innerHTML = "";
      const comps = data.competitors || [];
      if (comps.length === 0) {
        intelCompetitors.innerHTML = `<p>No competitor data found.</p>`;
      } else {
        comps.forEach(c => {
          intelCompetitors.innerHTML += `
            <div class="competitor-card">
              <div class="comp-name">${escapeHtml(c.name)}</div>
              <div class="comp-domain">${escapeHtml(c.domain)}</div>
              <div class="comp-snippet">${escapeHtml(c.snippet)}</div>
            </div>
          `;
        });
      }

    } catch (err) {
      console.error("Intel fetch error:", err);
    } finally {
      intelSpinner.classList.add("hidden");
      intelContent.classList.remove("hidden");
    }
  }


  // Modal handlers
  function openOutreachModal(lead) {
    if (!lead) return;
    modalLeadName.textContent = `Outreach Copy for ${lead.name} (${lead.company})`;
    notePreview.textContent = lead.connection_note || "";
    inmailSubject.textContent = lead.inmail?.subject || "";
    inmailBody.textContent = lead.inmail?.body || "";
    modal.classList.remove("hidden");
  }

  closeModal.addEventListener("click", () => modal.classList.add("hidden"));
  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.add("hidden");
  });

  // Copy Clipboard Handlers
  copyNoteBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(notePreview.textContent);
    copyNoteBtn.textContent = "✅ Copied!";
    setTimeout(() => copyNoteBtn.textContent = "📋 Copy Note", 2000);
  });

  copyInmailBtn.addEventListener("click", () => {
    const fullText = `Subject: ${inmailSubject.textContent}\n\n${inmailBody.textContent}`;
    navigator.clipboard.writeText(fullText);
    copyInmailBtn.textContent = "✅ Copied!";
    setTimeout(() => copyInmailBtn.textContent = "📋 Copy InMail", 2000);
  });

  // CSV Export Handler
  exportCsvBtn.addEventListener("click", async () => {
    if (!discoveredLeads.length) return;
    const response = await fetch("/api/export/csv", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(discoveredLeads)
    });
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "target_company_leads.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
  });

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
});
