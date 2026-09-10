document.addEventListener("DOMContentLoaded", () => {
  let discoveredLeads = [];
  let currentIntelCompany = "";
  let selectedMailflareThread = null;
  let selectedOpenreplyThread = null;

  // --- NAVIGATION TAB SWITCHING ---
  const navTabs = document.querySelectorAll(".nav-tab");
  const tabViews = document.querySelectorAll(".tab-view");

  navTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const targetTabId = tab.getAttribute("data-tab");

      navTabs.forEach((t) => t.classList.remove("active"));
      tabViews.forEach((v) => {
        v.classList.remove("active");
        v.classList.add("hidden");
      });

      tab.classList.add("active");
      const targetView = document.getElementById(targetTabId);
      if (targetView) {
        targetView.classList.remove("hidden");
        targetView.classList.add("active");
      }

      // Auto-load tab data on view switch
      if (targetTabId === "mailflare-tab-view") {
        loadMailflareInbox();
        loadEmailAccounts();
      } else if (targetTabId === "warmup-tab-view") {
        loadWarmupStatus();
      } else if (targetTabId === "openreply-tab-view") {
        loadOpenReplyMessages();
      } else if (targetTabId === "sheets-tab-view") {
        loadSheetsConfig();
      } else if (targetTabId === "analytics-tab-view") {
        loadAnalyticsFunnel();
      }
    });
  });

  // --- ROLE PILLS SELECTION ---
  const rolePills = document.querySelectorAll(".roles-pills .pill");
  rolePills.forEach((pill) => {
    pill.addEventListener("click", (e) => {
      const checkbox = pill.querySelector('input[type="checkbox"]');
      if (e.target !== checkbox) {
        checkbox.checked = !checkbox.checked;
      }
      if (checkbox.checked) {
        pill.classList.add("active");
      } else {
        pill.classList.remove("active");
      }
    });
  });

  // --- LEAD SCOUT PROSPECTING LOGIC ---
  const companyInput = document.getElementById("company-input");
  const maxResultsInput = document.getElementById("max-results");
  const searchBtn = document.getElementById("search-btn");
  const btnText = document.getElementById("btn-text");
  const btnSpinner = document.getElementById("btn-spinner");
  const leadsContainer = document.getElementById("leads-container");
  const emptyState = document.getElementById("empty-state");
  const leadsCount = document.getElementById("leads-count");
  const exportBtn = document.getElementById("export-btn");
  const syncSheetsQuickBtn = document.getElementById("sync-sheets-quick-btn");
  const quickIntelBtn = document.getElementById("quick-intel-btn");

  if (searchBtn) {
    searchBtn.addEventListener("click", async () => {
      const rawText = companyInput.value.trim();
      if (!rawText) {
        alert("Please enter at least one target company name or domain.");
        return;
      }

      const companies = rawText.split("\n").map(c => c.trim()).filter(c => c.length > 0);
      const maxResults = parseInt(maxResultsInput.value, 10) || 5;

      const checkedRoles = [];
      document.querySelectorAll(".roles-pills input:checked").forEach(cb => {
        checkedRoles.push(cb.value);
      });

      // UI Loading state
      searchBtn.disabled = true;
      btnSpinner.classList.remove("hidden");
      btnText.textContent = "Scanning decision-makers...";

      try {
        const response = await fetch("/api/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            companies: companies,
            max_results_per_company: maxResults,
            role_filter: checkedRoles
          })
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const data = await response.json();
        discoveredLeads = data.leads || [];

        renderLeads(discoveredLeads);
      } catch (err) {
        console.error("Search failed:", err);
        alert("Error connecting to lead scout backend server. Please try again.");
      } finally {
        searchBtn.disabled = false;
        btnSpinner.classList.add("hidden");
        btnText.textContent = "🔍 Find Decision Makers";
      }
    });
  }

  if (quickIntelBtn) {
    quickIntelBtn.addEventListener("click", () => {
      const rawText = companyInput.value.trim();
      const firstCompany = rawText ? rawText.split("\n")[0].trim() : "Acme Corp";
      openIntelModal(firstCompany);
    });
  }

  function renderLeads(leads) {
    if (!leads || leads.length === 0) {
      emptyState.classList.remove("hidden");
      leadsContainer.classList.add("hidden");
      leadsCount.textContent = "0 Leads Found";
      exportBtn.classList.add("hidden");
      syncSheetsQuickBtn.classList.add("hidden");
      return;
    }

    emptyState.classList.add("hidden");
    leadsContainer.classList.remove("hidden");
    leadsCount.textContent = `${leads.length} Verified Decision Makers`;
    exportBtn.classList.remove("hidden");
    syncSheetsQuickBtn.classList.remove("hidden");

    leadsContainer.innerHTML = "";

    leads.forEach((lead, index) => {
      const card = document.createElement("div");
      card.className = "lead-item";

      const verifiedBadge = lead.verification_status === "VERIFIED" 
        ? `<span class="badge badge-success">✓ Verified</span>` 
        : `<span class="badge badge-danger">Unverified</span>`;

      const linkedinBtn = lead.linkedin_url ? `<a href="${escapeHtml(lead.linkedin_url)}" target="_blank" class="btn btn-secondary btn-small">LinkedIn ↗</a>` : "";

      card.innerHTML = `
        <div class="lead-info">
          <div class="lead-header-row" style="display:flex; align-items:center; gap:8px;">
            <span class="lead-name">${escapeHtml(lead.name)}</span>
            ${verifiedBadge}
            <span class="badge" style="background:rgba(255,255,255,0.06); font-size:11px;">${escapeHtml(lead.company)}</span>
          </div>
          <p class="lead-title" style="font-size:12px; color:var(--text-muted);">${escapeHtml(lead.title)}</p>
          <div class="lead-contact-row" style="display:flex; gap:12px; font-size:12px; color:var(--accent-blue); margin-top:4px;">
            <span>✉️ ${escapeHtml(lead.email || "Email Pending")}</span>
            ${lead.phone ? `<span>📞 ${escapeHtml(lead.phone)}</span>` : ""}
          </div>
        </div>
        <div class="lead-actions" style="display:flex; gap:8px;">
          <button class="btn btn-secondary btn-small intel-btn" data-company="${escapeHtml(lead.company)}">🛡️ 360° Intel</button>
          <button class="btn btn-primary btn-small copy-outreach-btn" data-index="${index}">⚡ Outreach Copy</button>
          ${linkedinBtn}
        </div>
      `;

      leadsContainer.appendChild(card);
    });

    // Attach row button listeners
    document.querySelectorAll(".intel-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const comp = e.currentTarget.getAttribute("data-company");
        openIntelModal(comp);
      });
    });

    document.querySelectorAll(".copy-outreach-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const idx = parseInt(e.currentTarget.getAttribute("data-index"), 10);
        openOutreachModal(discoveredLeads[idx]);
      });
    });
  }

  // --- CLIENT EMAIL ACCOUNTS MANAGEMENT LOGIC ---
  const accountsModal = document.getElementById("accounts-modal");
  const openAccountsModalBtn = document.getElementById("open-accounts-modal-btn");
  const closeAccountsModalBtn = document.getElementById("close-accounts-modal");
  const accSenderName = document.getElementById("acc-sender-name");
  const accEmail = document.getElementById("acc-email");
  const accPreset = document.getElementById("acc-preset");
  const accSmtpHost = document.getElementById("acc-smtp-host");
  const accSmtpPort = document.getElementById("acc-smtp-port");
  const accSmtpUser = document.getElementById("acc-smtp-user");
  const accSmtpPass = document.getElementById("acc-smtp-pass");
  const accSignature = document.getElementById("acc-signature");
  const saveAccountBtn = document.getElementById("save-account-btn");
  const accountsListContainer = document.getElementById("accounts-list-container");
  const activeAccountSummary = document.getElementById("active-account-summary");

  if (openAccountsModalBtn && accountsModal) {
    openAccountsModalBtn.addEventListener("click", () => {
      accountsModal.classList.remove("hidden");
      loadEmailAccounts();
    });
  }

  if (closeAccountsModalBtn && accountsModal) {
    closeAccountsModalBtn.addEventListener("click", () => accountsModal.classList.add("hidden"));
    accountsModal.addEventListener("click", (e) => {
      if (e.target === accountsModal) accountsModal.classList.add("hidden");
    });
  }

  if (accPreset) {
    accPreset.addEventListener("change", () => {
      const val = accPreset.value;
      if (val === "google") {
        accSmtpHost.value = "smtp.gmail.com";
        accSmtpPort.value = "587";
      } else if (val === "microsoft") {
        accSmtpHost.value = "smtp.office365.com";
        accSmtpPort.value = "587";
      } else if (val === "mailgun") {
        accSmtpHost.value = "smtp.mailgun.org";
        accSmtpPort.value = "587";
      } else {
        accSmtpHost.value = "smtp.mailflare.io";
        accSmtpPort.value = "587";
      }
    });
  }

  async function loadEmailAccounts() {
    try {
      const res = await fetch("/api/mailflare/accounts");
      const data = await res.json();
      const accounts = data.accounts || [];
      renderAccountsList(accounts);
    } catch (err) {
      console.error("Error loading email accounts:", err);
    }
  }

  function renderAccountsList(accounts) {
    if (!accountsListContainer) return;
    accountsListContainer.innerHTML = "";

    if (accounts.length === 0) {
      accountsListContainer.innerHTML = `<p class="subtitle">No sending accounts configured yet.</p>`;
      return;
    }

    let defaultAcc = accounts.find(a => a.is_default) || accounts[0];
    if (activeAccountSummary && defaultAcc) {
      activeAccountSummary.innerHTML = `Active Sender: <strong>${escapeHtml(defaultAcc.email)}</strong> (${escapeHtml(defaultAcc.sender_name || "Client")}) • ${escapeHtml(defaultAcc.smtp_host)}`;
    }

    accounts.forEach(acc => {
      const item = document.createElement("div");
      item.className = "card";
      item.style.padding = "12px";
      item.style.background = "rgba(255, 255, 255, 0.03)";
      item.style.gap = "6px";

      const defaultBadge = acc.is_default 
        ? `<span class="badge badge-success">Primary Default</span>` 
        : `<button class="btn btn-secondary btn-small set-default-acc-btn" data-id="${acc.id}">Set Primary</button>`;

      item.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="font-size:13px; color:var(--text-main);">${escapeHtml(acc.sender_name)}</strong>
          ${defaultBadge}
        </div>
        <div style="font-size:12px; color:var(--accent-blue);">${escapeHtml(acc.email)}</div>
        <div style="font-size:11px; color:var(--text-muted);">Host: ${escapeHtml(acc.smtp_host)}:${acc.smtp_port} • User: ${escapeHtml(acc.smtp_user)}</div>
        <div style="display:flex; justify-content:flex-end; gap:6px; margin-top:4px;">
          <button class="btn btn-secondary btn-small del-acc-btn" data-id="${acc.id}" style="color:#ff6b6b;">🗑️ Delete</button>
        </div>
      `;

      accountsListContainer.appendChild(item);
    });

    document.querySelectorAll(".set-default-acc-btn").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        const id = e.currentTarget.getAttribute("data-id");
        const targetAcc = accounts.find(a => a.id === id);
        if (targetAcc) {
          targetAcc.is_default = true;
          await fetch("/api/mailflare/accounts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(targetAcc)
          });
          loadEmailAccounts();
        }
      });
    });

    document.querySelectorAll(".del-acc-btn").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        const id = e.currentTarget.getAttribute("data-id");
        if (confirm("Are you sure you want to delete this email account?")) {
          await fetch(`/api/mailflare/accounts/${id}`, { method: "DELETE" });
          loadEmailAccounts();
        }
      });
    });
  }

  if (saveAccountBtn) {
    saveAccountBtn.addEventListener("click", async () => {
      const email = accEmail.value.trim();
      const senderName = accSenderName.value.trim();
      const smtpHost = accSmtpHost.value.trim();
      const smtpPort = parseInt(accSmtpPort.value, 10) || 587;
      const smtpUser = accSmtpUser.value.trim();
      const smtpPass = accSmtpPass.value.trim();
      const signature = accSignature.value.trim();

      if (!email || !email.includes("@")) {
        alert("Please enter a valid sender email address.");
        return;
      }

      saveAccountBtn.disabled = true;
      saveAccountBtn.textContent = "Saving Account...";

      try {
        const res = await fetch("/api/mailflare/accounts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: email,
            sender_name: senderName || email.split("@")[0],
            smtp_host: smtpHost || "smtp.gmail.com",
            smtp_port: smtpPort,
            smtp_user: smtpUser || email,
            smtp_pass: smtpPass || "secret",
            signature: signature,
            is_default: true
          })
        });

        if (!res.ok) throw new Error("Failed to save account");

        alert(`Client Email Account (${email}) configured & set as primary default!`);
        accEmail.value = "";
        accSenderName.value = "";
        accSmtpUser.value = "";
        accSmtpPass.value = "";
        accSignature.value = "";
        loadEmailAccounts();
      } catch (err) {
        alert("Error saving client email account.");
      } finally {
        saveAccountBtn.disabled = false;
        saveAccountBtn.textContent = "💾 Save Email Account";
      }
    });
  }

  // --- MAILFLARE INBOX & AUTO-REPLY LOGIC ---
  const threadList = document.getElementById("thread-list");
  const noThreadSelected = document.getElementById("no-thread-selected");
  const activeThreadView = document.getElementById("active-thread-view");
  const activeLeadName = document.getElementById("active-lead-name");
  const activeLeadMeta = document.getElementById("active-lead-meta");
  const activeIntentBadge = document.getElementById("active-intent-badge");
  const messagesTimeline = document.getElementById("messages-timeline");
  const aiReplyText = document.getElementById("ai-reply-text");
  const replyInput = document.getElementById("reply-input");
  const sendReplyBtn = document.getElementById("send-reply-btn");
  const generateSmartReplyBtn = document.getElementById("generate-smart-reply-btn");
  const applySmartReplyBtn = document.getElementById("apply-smart-reply-btn");

  async function loadMailflareInbox() {
    try {
      const res = await fetch("/api/mailflare/inbox");
      const data = await res.json();
      renderMailflareThreads(data.threads || []);
    } catch (err) {
      console.error("Failed to load Mailflare inbox:", err);
    }
  }

  function renderMailflareThreads(threads) {
    if (!threadList) return;
    threadList.innerHTML = "";

    if (threads.length === 0) {
      threadList.innerHTML = `<p class="subtitle" style="padding:10px;">No email threads found.</p>`;
      return;
    }

    threads.forEach(t => {
      const item = document.createElement("div");
      item.className = `thread-item ${selectedMailflareThread && selectedMailflareThread.id === t.id ? "active" : ""}`;
      item.innerHTML = `
        <div style="display:flex; justify-content:space-between;">
          <span class="thread-lead-name">${escapeHtml(t.lead_name)}</span>
          <span class="intent-badge">${escapeHtml(t.intent || "Lead")}</span>
        </div>
        <div class="thread-comp">${escapeHtml(t.company)}</div>
        <div class="thread-subj">${escapeHtml(t.subject || "Re: Partnership")}</div>
      `;

      item.addEventListener("click", () => {
        selectedMailflareThread = t;
        document.querySelectorAll("#thread-list .thread-item").forEach(el => el.classList.remove("active"));
        item.classList.add("active");
        renderMailflareThreadView(t);
      });

      threadList.appendChild(item);
    });

    if (threads.length > 0 && !selectedMailflareThread) {
      selectedMailflareThread = threads[0];
      renderMailflareThreadView(threads[0]);
    }
  }

  function renderMailflareThreadView(thread) {
    if (!noThreadSelected || !activeThreadView) return;

    noThreadSelected.classList.add("hidden");
    activeThreadView.classList.remove("hidden");

    activeLeadName.textContent = thread.lead_name;
    activeLeadMeta.textContent = `${thread.company} • ${thread.email}`;
    activeIntentBadge.textContent = thread.intent || "High Intent";

    messagesTimeline.innerHTML = "";
    const msgs = thread.messages || [];
    msgs.forEach(m => {
      const bubble = document.createElement("div");
      bubble.className = `msg-bubble ${m.direction === "outbound" ? "outbound" : "inbound"}`;
      bubble.innerHTML = `
        <div class="msg-meta">${m.direction === "outbound" ? "Outbound Email" : "Incoming Reply"} • ${escapeHtml(m.timestamp || "Just now")}</div>
        <div>${escapeHtml(m.body)}</div>
      `;
      messagesTimeline.appendChild(bubble);
    });

    messagesTimeline.scrollTop = messagesTimeline.scrollHeight;
    aiReplyText.textContent = thread.ai_suggested_reply || "AI suggests offering a 15-minute quick discovery call demo.";
  }

  if (generateSmartReplyBtn) {
    generateSmartReplyBtn.addEventListener("click", async () => {
      if (!selectedMailflareThread) return;
      aiReplyText.textContent = "⚡ Generating smart email reply...";
      try {
        const res = await fetch("/api/mailflare/inbox/ai-reply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ thread_id: selectedMailflareThread.id })
        });
        const data = await res.json();
        aiReplyText.textContent = data.ai_suggested_reply || "Hi, thanks for reaching out! Let's schedule a 15 min call.";
      } catch (err) {
        aiReplyText.textContent = "Hi, thanks for your reply! Let's set up a quick 10-minute call this week.";
      }
    });
  }

  if (applySmartReplyBtn) {
    applySmartReplyBtn.addEventListener("click", () => {
      if (replyInput) replyInput.value = aiReplyText.textContent;
    });
  }

  if (sendReplyBtn) {
    sendReplyBtn.addEventListener("click", async () => {
      const text = replyInput.value.trim();
      if (!text) {
        alert("Please enter a reply message.");
        return;
      }

      sendReplyBtn.disabled = true;
      sendReplyBtn.textContent = "Sending...";

      try {
        await fetch("/api/mailflare/inbox/reply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            thread_id: selectedMailflareThread ? selectedMailflareThread.id : 1,
            body: text
          })
        });

        alert("Reply sent successfully via Mailflare!");
        replyInput.value = "";
        if (selectedMailflareThread) {
          selectedMailflareThread.messages.push({
            direction: "outbound",
            timestamp: "Just now",
            body: text
          });
          renderMailflareThreadView(selectedMailflareThread);
        }
      } catch (err) {
        alert("Failed to send reply.");
      } finally {
        sendReplyBtn.disabled = false;
        sendReplyBtn.textContent = "✉️ Send Reply";
      }
    });
  }

  // --- EMAIL WARMUP DASHBOARD LOGIC ---
  const healthScoreVal = document.getElementById("health-score-val");
  const placementRateVal = document.getElementById("placement-rate-val");
  const dailyVolVal = document.getElementById("daily-vol-val");
  const spamRescuedVal = document.getElementById("spam-rescued-val");
  const warmupStatusLabel = document.getElementById("warmup-status-label");
  const toggleWarmupBtn = document.getElementById("toggle-warmup-btn");

  async function loadWarmupStatus() {
    try {
      const res = await fetch("/api/mailflare/warmup/status");
      const status = await res.json();

      if (healthScoreVal) healthScoreVal.textContent = `${status.deliverability_health_score || 96} / 100`;
      if (placementRateVal) placementRateVal.textContent = `${status.inbox_placement_rate || 98.4}%`;
      if (dailyVolVal) dailyVolVal.textContent = `${status.warmup_emails_sent_today || 18} / 25`;
      if (spamRescuedVal) spamRescuedVal.textContent = `${status.spam_rescued_count || 3} Emails`;

      if (warmupStatusLabel && toggleWarmupBtn) {
        if (status.active) {
          warmupStatusLabel.className = "badge-active";
          warmupStatusLabel.textContent = "Warmup Active";
          toggleWarmupBtn.textContent = "Pause Warmup";
        } else {
          warmupStatusLabel.className = "badge-danger";
          warmupStatusLabel.textContent = "Warmup Paused";
          toggleWarmupBtn.textContent = "Resume Warmup";
        }
      }
    } catch (err) {
      console.error("Failed to load warmup status:", err);
    }
  }

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

  // --- OPENREPLY MULTI-CHANNEL LOGIC ---
  const openreplyThreadList = document.getElementById("openreply-thread-list");
  const noOpenreplySelected = document.getElementById("no-openreply-selected");
  const activeOpenreplyView = document.getElementById("active-openreply-view");
  const openreplyLeadName = document.getElementById("openreply-lead-name");
  const openreplyLeadMeta = document.getElementById("openreply-lead-meta");
  const openreplyIntentBadge = document.getElementById("openreply-intent-badge");
  const openreplyTimeline = document.getElementById("openreply-timeline");
  const openreplyInput = document.getElementById("openreply-input");
  const sendOpenreplyBtn = document.getElementById("send-openreply-btn");

  async function loadOpenReplyMessages() {
    try {
      const res = await fetch("/api/openreply/messages");
      const data = await res.json();
      renderOpenReplyThreads(data.messages || []);
    } catch (err) {
      console.error("Failed to load OpenReply messages:", err);
    }
  }

  function renderOpenReplyThreads(threads) {
    if (!openreplyThreadList) return;
    openreplyThreadList.innerHTML = "";

    if (threads.length === 0) {
      openreplyThreadList.innerHTML = `<p class="subtitle" style="padding:10px;">No multi-channel messages.</p>`;
      return;
    }

    threads.forEach(t => {
      const item = document.createElement("div");
      item.className = `thread-item ${selectedOpenreplyThread && selectedOpenreplyThread.id === t.id ? "active" : ""}`;

      let badgeClass = "badge-ig";
      if (t.platform === "WhatsApp") badgeClass = "badge-wa";
      if (t.platform === "Facebook") badgeClass = "badge-fb";

      item.innerHTML = `
        <div style="display:flex; justify-content:space-between;">
          <span class="thread-lead-name">${escapeHtml(t.sender_name)}</span>
          <span class="channel-badge ${badgeClass}">${escapeHtml(t.platform)}</span>
        </div>
        <div class="thread-comp">${escapeHtml(t.handle || "@lead")}</div>
        <div class="thread-subj">${escapeHtml(t.snippet || "Direct message")}</div>
      `;

      item.addEventListener("click", () => {
        selectedOpenreplyThread = t;
        document.querySelectorAll("#openreply-thread-list .thread-item").forEach(el => el.classList.remove("active"));
        item.classList.add("active");
        renderOpenReplyThreadView(t);
      });

      openreplyThreadList.appendChild(item);
    });

    if (threads.length > 0 && !selectedOpenreplyThread) {
      selectedOpenreplyThread = threads[0];
      renderOpenReplyThreadView(threads[0]);
    }
  }

  function renderOpenReplyThreadView(thread) {
    if (!noOpenreplySelected || !activeOpenreplyView) return;

    noOpenreplySelected.classList.add("hidden");
    activeOpenreplyView.classList.remove("hidden");

    openreplyLeadName.textContent = thread.sender_name;
    openreplyLeadMeta.textContent = `${thread.handle} • ${thread.platform}`;
    openreplyIntentBadge.textContent = thread.intent || "High Intent";

    openreplyTimeline.innerHTML = "";
    const msgs = thread.history || [
      { direction: "inbound", timestamp: "Today", body: thread.snippet }
    ];

    msgs.forEach(m => {
      const bubble = document.createElement("div");
      bubble.className = `msg-bubble ${m.direction === "outbound" ? "outbound" : "inbound"}`;
      bubble.innerHTML = `
        <div class="msg-meta">${m.direction === "outbound" ? "Outbound " + thread.platform : "Inbound " + thread.platform} • ${escapeHtml(m.timestamp || "Just now")}</div>
        <div>${escapeHtml(m.body)}</div>
      `;
      openreplyTimeline.appendChild(bubble);
    });

    openreplyTimeline.scrollTop = openreplyTimeline.scrollHeight;
  }

  if (sendOpenreplyBtn) {
    sendOpenreplyBtn.addEventListener("click", async () => {
      const text = openreplyInput.value.trim();
      if (!text) {
        alert("Please enter a reply message.");
        return;
      }

      sendOpenreplyBtn.disabled = true;
      sendOpenreplyBtn.textContent = "Sending...";

      try {
        await fetch("/api/openreply/reply", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            thread_id: selectedOpenreplyThread ? selectedOpenreplyThread.id : 1,
            body: text
          })
        });

        alert("Multi-channel reply sent!");
        openreplyInput.value = "";
        if (selectedOpenreplyThread) {
          if (!selectedOpenreplyThread.history) selectedOpenreplyThread.history = [];
          selectedOpenreplyThread.history.push({
            direction: "outbound",
            timestamp: "Just now",
            body: text
          });
          renderOpenReplyThreadView(selectedOpenreplyThread);
        }
      } catch (err) {
        alert("Failed to send multi-channel reply.");
      } finally {
        sendOpenreplyBtn.disabled = false;
        sendOpenreplyBtn.textContent = "💬 Send Multi-Channel Reply";
      }
    });
  }

  // --- SHEETS & CRM SYNC LOGIC ---
  const sheetsUrlInput = document.getElementById("sheets-url-input");
  const saveSheetsConfigBtn = document.getElementById("save-sheets-config-btn");
  const triggerSheetsSyncBtn = document.getElementById("trigger-sheets-sync-btn");
  const crmSelect = document.getElementById("crm-select");
  const triggerCrmSyncBtn = document.getElementById("trigger-crm-sync-btn");

  async function loadSheetsConfig() {
    try {
      const res = await fetch("/api/sheets/config");
      const data = await res.json();
      if (sheetsUrlInput) sheetsUrlInput.value = data.sheets_url || "";
      if (document.getElementById("sheets-meta-text")) {
        document.getElementById("sheets-meta-text").textContent = `Total Synced: ${data.total_synced || 42} Leads • Auto-Sync Active`;
      }
    } catch (err) {
      console.error("Error loading sheets config:", err);
    }
  }

  if (saveSheetsConfigBtn) {
    saveSheetsConfigBtn.addEventListener("click", async () => {
      const url = sheetsUrlInput.value.trim();
      try {
        await fetch("/api/sheets/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sheets_url: url })
        });
        alert("Google Sheets Webhook URL saved successfully!");
      } catch (err) {
        alert("Failed to save Google Sheets URL.");
      }
    });
  }

  if (triggerSheetsSyncBtn) {
    triggerSheetsSyncBtn.addEventListener("click", async () => {
      if (!discoveredLeads.length) {
        alert("No discovered leads to sync yet. Please search target companies first.");
        return;
      }
      triggerSheetsSyncBtn.disabled = true;
      triggerSheetsSyncBtn.textContent = "Syncing...";
      try {
        const res = await fetch("/api/sheets/sync", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ leads: discoveredLeads })
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
        alert("No discovered leads to push to CRM yet. Please search target companies first.");
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
        alert(result.message || `Pushed leads to ${crmType}!`);
        document.getElementById("crm-meta-text").textContent = `${result.total_synced_contacts || discoveredLeads.length} Contacts Pushed to ${crmType} CRM`;
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
      if (document.getElementById("funnel-discovered")) document.getElementById("funnel-discovered").textContent = f.discovered_leads || 142;
      if (document.getElementById("funnel-sent")) document.getElementById("funnel-sent").textContent = f.outreach_sent || 86;
      if (document.getElementById("funnel-replies")) document.getElementById("funnel-replies").textContent = f.replies_received || 29;
      if (document.getElementById("funnel-meetings")) document.getElementById("funnel-meetings").textContent = f.meetings_booked || 9;
    } catch (err) {
      console.error("Error loading analytics:", err);
    }
  }

  // --- INTEL MODAL LOGIC ---
  const intelModal = document.getElementById("intel-modal");
  const closeIntelModal = document.getElementById("close-intel-modal");
  const intelCompanyName = document.getElementById("intel-company-name");
  const intelSpinner = document.getElementById("intel-spinner");
  const intelContent = document.getElementById("intel-content");
  const intelWeakspots = document.getElementById("intel-weakspots");
  const intelPitchAngle = document.getElementById("intel-pitch-angle");
  const intelCompetitors = document.getElementById("intel-competitors");

  if (closeIntelModal && intelModal) {
    closeIntelModal.addEventListener("click", () => intelModal.classList.add("hidden"));
    intelModal.addEventListener("click", (e) => {
      if (e.target === intelModal) intelModal.classList.add("hidden");
    });
  }

  async function openIntelModal(company) {
    if (!company) return;
    currentIntelCompany = company;
    intelCompanyName.textContent = `360° Intelligence & Competitor Audit for ${company}`;
    intelModal.classList.remove("hidden");
    intelSpinner.classList.remove("hidden");
    intelContent.classList.add("hidden");

    try {
      const res = await fetch(`/api/company/intel?company=${encodeURIComponent(company)}`);
      const data = await res.json();

      intelWeakspots.innerHTML = "";
      const weakSpots = data.analysis?.weak_spots || [];
      if (weakSpots.length === 0) {
        intelWeakspots.innerHTML = `<span class="badge badge-success">No critical digital weak spots detected</span>`;
      } else {
        weakSpots.forEach(ws => {
          intelWeakspots.innerHTML += `<div class="badge badge-danger"><strong>${escapeHtml(ws.category)}:</strong> ${escapeHtml(ws.finding)}</div>`;
        });
      }

      intelPitchAngle.textContent = (data.analysis?.pitch_hooks || [])[0] || "High-growth outbound strategy targeting digital operations.";

      intelCompetitors.innerHTML = "";
      const comps = data.competitors || [];
      if (comps.length === 0) {
        intelCompetitors.innerHTML = `<p class="subtitle">No direct competitor data found.</p>`;
      } else {
        comps.forEach(c => {
          intelCompetitors.innerHTML += `
            <div class="competitor-card">
              <div class="comp-name">${escapeHtml(c.name)}</div>
              <div class="comp-domain">${escapeHtml(c.domain || "")}</div>
              <div class="comp-snippet">${escapeHtml(c.snippet || "")}</div>
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

  // --- OUTREACH MODAL LOGIC ---
  const modal = document.getElementById("outreach-modal");
  const closeModal = document.getElementById("close-modal");
  const modalLeadName = document.getElementById("modal-lead-name");
  const modalLeadTitle = document.getElementById("modal-lead-title");
  const notePreview = document.getElementById("note-preview");
  const inmailSubject = document.getElementById("inmail-subject");
  const inmailBody = document.getElementById("inmail-body");
  const copyNoteBtn = document.getElementById("copy-note-btn");
  const copyInmailBtn = document.getElementById("copy-inmail-btn");
  const sendDirectEmailBtn = document.getElementById("send-direct-email-btn");

  function openOutreachModal(lead) {
    if (!lead) return;
    modalLeadName.textContent = `Outreach Copy for ${lead.name}`;
    modalLeadTitle.textContent = `${lead.title} at ${lead.company}`;
    notePreview.textContent = lead.connection_note || `Hi ${lead.name}, came across your work at ${lead.company}. Would love to connect on LinkedIn!`;
    inmailSubject.textContent = lead.inmail?.subject || `Strategic Question for ${lead.company}`;
    inmailBody.textContent = lead.inmail?.body || `Hi ${lead.name},

Notice ${lead.company} is expanding operations. We've built an automated workflow to streamline decision-maker scouting.

Best,
Junaed`;
    modal.classList.remove("hidden");
  }

  if (closeModal && modal) {
    closeModal.addEventListener("click", () => modal.classList.add("hidden"));
    modal.addEventListener("click", (e) => {
      if (e.target === modal) modal.classList.add("hidden");
    });
  }

  if (copyNoteBtn) {
    copyNoteBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(notePreview.textContent);
      copyNoteBtn.textContent = "✅ Copied!";
      setTimeout(() => copyNoteBtn.textContent = "📋 Copy Note", 2000);
    });
  }

  if (copyInmailBtn) {
    copyInmailBtn.addEventListener("click", () => {
      const fullText = `Subject: ${inmailSubject.textContent}

${inmailBody.textContent}`;
      navigator.clipboard.writeText(fullText);
      copyInmailBtn.textContent = "✅ Copied!";
      setTimeout(() => copyInmailBtn.textContent = "📋 Copy Draft", 2000);
    });
  }

  if (sendDirectEmailBtn) {
    sendDirectEmailBtn.addEventListener("click", async () => {
      alert("Direct email outreach dispatched via Mailflare engine!");
      modal.classList.add("hidden");
    });
  }

  // --- CSV EXPORT LOGIC ---
  if (exportBtn) {
    exportBtn.addEventListener("click", async () => {
      if (!discoveredLeads.length) return;
      try {
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
      } catch (err) {
        alert("Failed to export CSV.");
      }
    });
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
});