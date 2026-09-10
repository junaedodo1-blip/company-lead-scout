let discoveredLeads = [];
let activeThreadId = null;
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

  // Navigation Tab Switching
  document.querySelectorAll(".nav-tab").forEach(tabBtn => {
    tabBtn.addEventListener("click", () => {
      document.querySelectorAll(".nav-tab").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-view").forEach(v => v.classList.add("hidden"));

      tabBtn.classList.add("active");
      const targetViewId = tabBtn.getAttribute("data-tab");
      document.getElementById(targetViewId).classList.remove("hidden");

      if (targetViewId === "mailflare-tab-view") {
        loadThreads();
      } else if (targetViewId === "warmup-tab-view") {
        loadWarmupStatus();
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
      leadsCount.textContent = "0 Leads Found";
      return;
    }

    emptyState.classList.add("hidden");
    leadsContainer.classList.remove("hidden");
    exportBtn.classList.remove("hidden");
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
            💬 Copy Outreach & Email
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

  // Send Direct Email via Mailflare
  if (sendDirectEmailBtn) {
    sendDirectEmailBtn.addEventListener("click", async () => {
      if (!currentSelectedLeadForEmail) return;
      const recipientEmail = prompt("Enter recipient email address for outreach:", ${currentSelectedLeadForEmail.name.toLowerCase().replace(/\s+/g, '.')}@.com);
      if (!recipientEmail) return;

      sendDirectEmailBtn.disabled = true;
      sendDirectEmailBtn.textContent = "Sending...";

      try {
        const res = await fetch("/api/mailflare/send", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            to_email: recipientEmail,
            subject: inmailSubject.textContent,
            body: inmailBody.textContent,
            lead_name: currentSelectedLeadForEmail.name,
            company: currentSelectedLeadForEmail.company
          })
        });
        const result = await res.json();
        alert("Outreach Email Dispatched! Track replies in Mailflare Inbox.");
        modal.classList.add("hidden");
      } catch (err) {
        alert("Failed to send email: " + err.message);
      } finally {
        sendDirectEmailBtn.disabled = false;
        sendDirectEmailBtn.textContent = "✉️ Dispatch Email via Mailflare";
      }
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

  async function loadThreads() {
    try {
      const res = await fetch("/api/mailflare/threads");
      const data = await res.json();
      renderThreadList(data.threads || []);
    } catch (err) {
      console.error("Failed to load threads:", err);
    }
  }

  function renderThreadList(threads) {
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

      item.addEventListener("click", () => loadActiveThread(t.thread_id));
      threadListEl.appendChild(item);
    });
  }

  async function loadActiveThread(threadId) {
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

  if (generateSmartReplyBtn) {
    generateSmartReplyBtn.addEventListener("click", () => {
      if (activeThreadId) loadSmartReply(activeThreadId);
    });
  }

  if (applySmartReplyBtn) {
    applySmartReplyBtn.addEventListener("click", () => {
      replyInput.value = aiReplyText.textContent;
    });
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
        loadActiveThread(activeThreadId);
      } catch (err) {
        alert("Failed to send reply: " + err.message);
      } finally {
        sendReplyBtn.disabled = false;
      }
    });
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
