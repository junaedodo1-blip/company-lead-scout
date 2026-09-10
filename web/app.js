let discoveredLeads = [];
let activeThreadId = null;
let activeOpenReplyThreadId = null;
let currentSelectedLeadForEmail = null;

document.addEventListener("DOMContentLoaded", () => {
  const companyInput = document.getElementById("company-input");
  const maxResultsInput = document.getElementById("max-results");
  const searchBtn = document.getElementById("search-btn");
  const btnText = document.getElementById("btn-text");
  const btnSpinner = document.getElementById("btn-spinner");
  const emptyState = document.getElementById("empty-state");
  const leadsContainer = document.getElementById("leads-container");
  const leadsCount = document.getElementById("leads-count");
  const exportBtn = document.getElementById("export-btn");
  const syncSheetsQuickBtn = document.getElementById("sync-sheets-quick-btn");

  // Navigation Tab Switching across 6 Workspace Tabs
  document.querySelectorAll(".nav-tab").forEach(tabBtn => {
    tabBtn.addEventListener("click", (e) => {
      e.preventDefault();
      document.querySelectorAll(".nav-tab").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-view").forEach(v => {
        v.classList.add("hidden");
        v.style.setProperty("display", "none", "important");
      });

      tabBtn.classList.add("active");
      const targetViewId = tabBtn.getAttribute("data-tab");
      const targetView = document.getElementById(targetViewId);
      if (targetView) {
        targetView.classList.remove("hidden");
        targetView.style.setProperty("display", "block", "important");
      }

      if (targetViewId === "mailflare-tab-view") {
        loadMailflareThreads();
      } else if (targetViewId === "warmup-tab-view") {
        loadWarmupStatus();
      } else if (targetViewId === "openreply-tab-view") {
        loadOpenReplyThreads();
      } else if (targetViewId === "sheets-tab-view") {
        loadSheetsConfig();
      } else if (targetViewId === "analytics-tab-view") {
        loadAnalyticsFunnel();
      }
    });
  });

  // Modal Elements
  const modal = document.getElementById("outreach-modal");
  const closeModal = document.getElementById("close-modal");
  const modalLeadName = document.getElementById("modal-lead-name");
  const notePreview = document.getElementById("note-preview");
  const inmailSubject = document.getElementById("inmail-subject");
  const inmailBody = document.getElementById("inmail-body");
  const copyNoteBtn = document.getElementById("copy-note-btn");
  const copyInmailBtn = document.getElementById("copy-inmail-btn");
  const sendDirectEmailBtn = document.getElementById("send-direct-email-btn");

  // Role Pills Toggle
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
    const selectedTitles = Array.from(document.querySelectorAll(".pill input:checked")).map(cb => cb.value);

    searchBtn.disabled = true;
    btnText.textContent = "Scanning decision-makers...";
    btnSpinner.classList.remove("hidden");

    let seconds = 0;
    const progressTimer = setInterval(() => {
      seconds += 1;
      btnText.textContent = Scanning decision-makers... (s);
    }, 1000);

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
      alert("Error finding decision makers: " + err.message);
    } finally {
      clearInterval(progressTimer);
      searchBtn.disabled = false;
      btnText.textContent = "🔍 Find Decision Makers";
      btnSpinner.classList.add("hidden");
    }
  });

  function renderLeads(leads) {
    if (!leads || leads.length === 0) {
      emptyState.classList.remove("hidden");
      leadsContainer.classList.add("hidden");
      exportBtn.classList.add("hidden");
      if (syncSheetsQuickBtn) syncSheetsQuickBtn.classList.add("hidden");
      leadsCount.textContent = "0 Leads Found";
      return;
    }

    emptyState.classList.add("hidden");
    leadsContainer.classList.remove("hidden");
    exportBtn.classList.remove("hidden");
    if (syncSheetsQuickBtn) syncSheetsQuickBtn.classList.remove("hidden");
    leadsCount.textContent = ${leads.length} Leads Discovered;

    leadsContainer.innerHTML = "";
    leads.forEach((lead, index) => {
      const card = document.createElement("div");
      card.className = "lead-card";

      card.innerHTML = 
        <div class="lead-header">
          <div>
            <h3 class="lead-name"></h3>
            <div class="lead-title"></div>
          </div>
          <span class="company-badge"></span>
        </div>

        <div class="lead-meta">
          <span>📍 </span>
        </div>

        <p class="raw-snippet"></p>

        <div class="lead-actions">
          <a href="" target="_blank" class="btn btn-secondary btn-small">
            🔗 LinkedIn Profile
          </a>
          <button class="btn btn-secondary btn-small intel-audit-btn" data-comp="">
            🛡️ 360° Audit
          </button>
          <button class="btn btn-primary btn-small outreach-btn" data-index="">
            💬 Outreach & Email
          </button>
        </div>
      ;

      leadsContainer.appendChild(card);
    });

    document.querySelectorAll(".outreach-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = btn.getAttribute("data-index");
        currentSelectedLeadForEmail = discoveredLeads[idx];
        openOutreachModal(currentSelectedLeadForEmail);
      });
    });

    document.querySelectorAll(".intel-audit-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const comp = btn.getAttribute("data-comp");
        openIntelModal(comp);
      });
    });
  }

  // --- MAILFLARE INBOX LOGIC ---
  const threadListEl = document.getElementById("thread-list");
  const noThreadSelected = document.getElementById("no-thread-selected");
  const activeThreadView = document.getElementById("active-thread-view");
  const activeLeadName = document.getElementById("active-lead-name");
  const activeLeadMeta = document.getElementById("active-lead-meta");
  const activeIntentBadge = document.getElementById("active-intent-badge");
  const messagesTimeline = document.getElementById("messages-timeline");
  const aiReplyBox = document.getElementById("ai-reply-box");
  const aiReplyText = document.getElementById("ai-reply-text");
  const generateSmartReplyBtn = document.getElementById("generate-smart-reply-btn");
  const applySmartReplyBtn = document.getElementById("apply-smart-reply-btn");
  const replyInput = document.getElementById("reply-input");
  const sendReplyBtn = document.getElementById("send-reply-btn");

  async function loadMailflareThreads() {
    try {
      const res = await fetch("/api/mailflare/threads");
      const data = await res.json();
      renderMailflareThreadList(data.threads || []);
    } catch (err) {
      console.error("Failed to load Mailflare threads:", err);
    }
  }

  function renderMailflareThreadList(threads) {
    threadListEl.innerHTML = "";
    if (threads.length === 0) {
      threadListEl.innerHTML = <p style="font-size:12px; color:var(--text-muted);">No active conversations yet.</p>;
      return;
    }

    threads.forEach(t => {
      const item = document.createElement("div");
      item.className = 	hread-item ;
      item.innerHTML = 
        <div style="display:flex; justify-between; align-items:center;">
          <span class="thread-lead-name"></span>
          <span class="intent-badge"></span>
        </div>
        <div class="thread-comp"></div>
        <div class="thread-subj"></div>
      ;

      item.addEventListener("click", () => loadActiveMailflareThread(t.thread_id));
      threadListEl.appendChild(item);
    });
  }

  async function loadActiveMailflareThread(threadId) {
    activeThreadId = threadId;
    try {
      const res = await fetch(/api/mailflare/threads/);
      const thread = await res.json();

      noThreadSelected.classList.add("hidden");
      activeThreadView.classList.remove("hidden");

      activeLeadName.textContent = thread.lead_name;
      activeLeadMeta.textContent = ${thread.company} • ;
      activeIntentBadge.textContent = thread.intent || "Active";

      messagesTimeline.innerHTML = "";
      (thread.messages || []).forEach(m => {
        const bubble = document.createElement("div");
        bubble.className = msg-bubble ;
        bubble.innerHTML = 
          <div class="msg-meta"> • </div>
          <div style="white-space:pre-wrap;"></div>
        ;
        messagesTimeline.appendChild(bubble);
      });
      messagesTimeline.scrollTop = messagesTimeline.scrollHeight;

      loadSmartReply(threadId);
    } catch (err) {
      console.error("Error loading thread detail:", err);
    }
  }

  async function loadSmartReply(threadId) {
    try {
      const res = await fetch(/api/mailflare/smart-reply?thread_id=, { method: "POST" });
      const data = await res.json();
      aiReplyText.textContent = data.suggested_reply;
    } catch (err) {
      aiReplyText.textContent = "AI Smart Reply unavailable.";
    }
  }

  if (sendReplyBtn) {
    sendReplyBtn.addEventListener("click", async () => {
      const bodyText = replyInput.value.trim();
      if (!bodyText || !activeThreadId) return;

      sendReplyBtn.disabled = true;
      try {
        await fetch("/api/mailflare/reply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ thread_id: activeThreadId, body: bodyText })
        });
        replyInput.value = "";
        loadActiveMailflareThread(activeThreadId);
      } catch (err) {
        alert("Failed to send reply: " + err.message);
      } finally {
        sendReplyBtn.disabled = false;
      }
    });
  }

  // --- OPENREPLY HUB LOGIC (INSTAGRAM, WHATSAPP, FACEBOOK) ---
  const openreplyThreadList = document.getElementById("openreply-thread-list");
  const noOpenreplySelected = document.getElementById("no-openreply-selected");
  const activeOpenreplyView = document.getElementById("active-openreply-view");
  const openreplyLeadName = document.getElementById("openreply-lead-name");
  const openreplyLeadMeta = document.getElementById("openreply-lead-meta");
  const openreplyIntentBadge = document.getElementById("openreply-intent-badge");
  const openreplyTimeline = document.getElementById("openreply-timeline");
  const openreplyInput = document.getElementById("openreply-input");
  const sendOpenreplyBtn = document.getElementById("send-openreply-btn");

  async function loadOpenReplyThreads() {
    try {
      const res = await fetch("/api/openreply/threads");
      const data = await res.json();
      renderOpenReplyThreadList(data.threads || []);
    } catch (err) {
      console.error("Failed to load OpenReply threads:", err);
    }
  }

  function renderOpenReplyThreadList(threads) {
    openreplyThreadList.innerHTML = "";
    if (threads.length === 0) {
      openreplyThreadList.innerHTML = <p style="font-size:12px; color:var(--text-muted);">No multi-channel conversations yet.</p>;
      return;
    }

    threads.forEach(t => {
      const item = document.createElement("div");
      item.className = 	hread-item ;
      const badgeClass = t.channel === "instagram" ? "badge-ig" : (t.channel === "whatsapp" ? "badge-wa" : "badge-fb");

      item.innerHTML = 
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span class="thread-lead-name"></span>
          <span class="channel-badge "></span>
        </div>
        <div class="thread-comp"></div>
        <div class="thread-subj"></div>
      ;

      item.addEventListener("click", () => loadActiveOpenReplyThread(t));
      openreplyThreadList.appendChild(item);
    });
  }

  function loadActiveOpenReplyThread(thread) {
    activeOpenReplyThreadId = thread.thread_id;
    noOpenreplySelected.classList.add("hidden");
    activeOpenreplyView.classList.remove("hidden");

    openreplyLeadName.textContent = thread.lead_name;
    openreplyLeadMeta.textContent = ${thread.company} •  ();
    openreplyIntentBadge.textContent = thread.intent || "Active";

    openreplyTimeline.innerHTML = "";
    (thread.messages || []).forEach(m => {
      const bubble = document.createElement("div");
      bubble.className = msg-bubble ;
      bubble.innerHTML = 
        <div class="msg-meta"> • </div>
        <div style="white-space:pre-wrap;"></div>
      ;
      openreplyTimeline.appendChild(bubble);
    });
    openreplyTimeline.scrollTop = openreplyTimeline.scrollHeight;
  }

  if (sendOpenreplyBtn) {
    sendOpenreplyBtn.addEventListener("click", async () => {
      const bodyText = openreplyInput.value.trim();
      if (!bodyText || !activeOpenReplyThreadId) return;

      sendOpenreplyBtn.disabled = true;
      try {
        await fetch("/api/openreply/send", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ thread_id: activeOpenReplyThreadId, body: bodyText })
        });
        openreplyInput.value = "";
        loadOpenReplyThreads();
      } catch (err) {
        alert("Failed to send multi-channel message.");
      } finally {
        sendOpenreplyBtn.disabled = false;
      }
    });
  }

  // --- GOOGLE SHEETS & CRM SYNC LOGIC ---
  const sheetsUrlInput = document.getElementById("sheets-url-input");
  const saveSheetsConfigBtn = document.getElementById("save-sheets-config-btn");
  const triggerSheetsSyncBtn = document.getElementById("trigger-sheets-sync-btn");
  const crmSelect = document.getElementById("crm-select");
  const triggerCrmSyncBtn = document.getElementById("trigger-crm-sync-btn");

  async function loadSheetsConfig() {
    try {
      const res = await fetch("/api/sheets/config");
      const cfg = await res.json();
      if (sheetsUrlInput) sheetsUrlInput.value = cfg.webhook_url || "";
      document.getElementById("sheets-meta-text").textContent = Total Synced:  Leads • Auto-Sync Active;
    } catch (err) {
      console.error("Error loading sheets config:", err);
    }
  }

  if (saveSheetsConfigBtn) {
    saveSheetsConfigBtn.addEventListener("click", async () => {
      const url = sheetsUrlInput.value.trim();
      await fetch("/api/sheets/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ webhook_url: url, enabled: true })
      });
      alert("Google Sheets Webhook Configuration Saved!");
      loadSheetsConfig();
    });
  }

  if (triggerSheetsSyncBtn) {
    triggerSheetsSyncBtn.addEventListener("click", async () => {
      if (!discoveredLeads.length) {
        alert("No discovered leads to sync yet. Find decision makers first!");
        return;
      }
      triggerSheetsSyncBtn.disabled = true;
      triggerSheetsSyncBtn.textContent = "Syncing...";
      try {
        const res = await fetch("/api/sheets/sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(discoveredLeads)
        });
        const result = await res.json();
        alert(result.message || "Synced leads to Google Sheets!");
        loadSheetsConfig();
      } catch (err) {
        alert("Failed to sync leads to Google Sheets.");
      } finally {
        triggerSheetsSyncBtn.disabled = false;
        triggerSheetsSyncBtn.textContent = "📊 Sync Current Leads to Sheet";
      }
    });
  }

  if (syncSheetsQuickBtn) {
    syncSheetsQuickBtn.addEventListener("click", () => {
      if (triggerSheetsSyncBtn) triggerSheetsSyncBtn.click();
    });
  }

  if (triggerCrmSyncBtn) {
    triggerCrmSyncBtn.addEventListener("click", async () => {
      if (!discoveredLeads.length) {
        alert("No discovered leads to push to CRM yet.");
        return;
      }
      const crmType = crmSelect.value;
      triggerCrmSyncBtn.disabled = true;
      triggerCrmSyncBtn.textContent = "Pushing to CRM...";
      try {
        const res = await fetch("/api/crm/sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ leads: discoveredLeads, crm_type: crmType })
        });
        const result = await res.json();
        alert(result.message || Pushed leads to !);
        document.getElementById("crm-meta-text").textContent = ${result.total_synced_contacts} Contacts Pushed to  CRM;
      } catch (err) {
        alert("Failed to push leads to CRM.");
      } finally {
        triggerCrmSyncBtn.disabled = false;
        triggerCrmSyncBtn.textContent = "🚀 Push Leads to CRM";
      }
    });
  }

  // --- ANALYTICS FUNNEL LOGIC ---
  async function loadAnalyticsFunnel() {
    try {
      const res = await fetch("/api/analytics/funnel");
      const data = await res.json();
      const f = data.funnel || {};
      document.getElementById("funnel-discovered").textContent = f.discovered_leads || 0;
      document.getElementById("funnel-sent").textContent = f.outreach_sent || 0;
      document.getElementById("funnel-replies").textContent = f.replies_received || 0;
      document.getElementById("funnel-meetings").textContent = f.meetings_booked || 0;
    } catch (err) {
      console.error("Error loading analytics:", err);
    }
  }

  // --- EMAIL WARMUP LOGIC ---
  async function loadWarmupStatus() {
    try {
      const res = await fetch("/api/mailflare/warmup/status");
      const status = await res.json();

      document.getElementById("health-score-val").textContent = ${status.deliverability_health_score} / 100;
      document.getElementById("placement-rate-val").textContent = ${status.inbox_placement_rate}%;
      document.getElementById("daily-vol-val").textContent = ${status.warmup_emails_sent_today} / ;
      document.getElementById("spam-rescued-val").textContent = ${status.spam_rescued_count} Emails;

      const statusLabel = document.getElementById("warmup-status-label");
      const toggleBtn = document.getElementById("toggle-warmup-btn");

      if (status.active) {
        statusLabel.className = "badge-active";
        statusLabel.textContent = "Warmup Active";
        toggleBtn.textContent = "Pause Warmup";
      } else {
        statusLabel.className = "badge-danger";
        statusLabel.textContent = "Warmup Paused";
        toggleBtn.textContent = "Resume Warmup";
      }
    } catch (err) {
      console.error("Failed to load warmup status:", err);
    }
  }

  const toggleWarmupBtn = document.getElementById("toggle-warmup-btn");
  if (toggleWarmupBtn) {
    toggleWarmupBtn.addEventListener("click", async () => {
      const isCurrentlyActive = toggleWarmupBtn.textContent.includes("Pause");
      try {
        await fetch("/api/mailflare/warmup/status", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ active: !isCurrentlyActive })
        });
        loadWarmupStatus();
      } catch (err) {
        alert("Failed to update warmup state.");
      }
    });
  }

  // Intel Modal Handlers
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
    intelCompanyName.textContent = 360° Intelligence & Competitor Audit for ;
    intelModal.classList.remove("hidden");
    intelSpinner.classList.remove("hidden");
    intelContent.classList.add("hidden");

    try {
      const res = await fetch(/api/company/intel?company=);
      const data = await res.json();
      
      intelWeakspots.innerHTML = "";
      const weakSpots = data.analysis?.weak_spots || [];
      if (weakSpots.length === 0) {
        intelWeakspots.innerHTML = <span class="badge badge-success">No critical digital weak spots detected</span>;
      } else {
        weakSpots.forEach(ws => {
          intelWeakspots.innerHTML += <div class="badge badge-danger"><strong>:</strong> </div>;
        });
      }

      intelPitchAngle.textContent = (data.analysis?.pitch_hooks || [])[0] || "No pitch angle generated";

      intelCompetitors.innerHTML = "";
      const comps = data.competitors || [];
      if (comps.length === 0) {
        intelCompetitors.innerHTML = <p>No competitor data found.</p>;
      } else {
        comps.forEach(c => {
          intelCompetitors.innerHTML += 
            <div class="competitor-card">
              <div class="comp-name"></div>
              <div class="comp-domain"></div>
              <div class="comp-snippet"></div>
            </div>
          ;
        });
      }

    } catch (err) {
      console.error("Intel fetch error:", err);
    } finally {
      intelSpinner.classList.add("hidden");
      intelContent.classList.remove("hidden");
    }
  }

  // Modal Handlers
  function openOutreachModal(lead) {
    if (!lead) return;
    modalLeadName.textContent = Outreach Copy for  ();
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
    const fullText = Subject: \n\n;
    navigator.clipboard.writeText(fullText);
    copyInmailBtn.textContent = "✅ Copied!";
    setTimeout(() => copyInmailBtn.textContent = "📋 Copy InMail", 2000);
  });

  // CSV Export Handler
  exportBtn.addEventListener("click", async () => {
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
