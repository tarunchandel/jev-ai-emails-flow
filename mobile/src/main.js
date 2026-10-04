import dataset from './dataset.json';

// Mobile App State
let state = {
  items: dataset,
  selectedId: dataset[0]?.id || null,
  activeTab: 'queue', // 'queue' | 'detail' | 'pipeline' | 'reports'
  detailSubTab: 'draft', // 'draft' | 'details' | 'timeline'
  filter: 'ALL',      // 'ALL' | 'ACTIONABLE' | 'OCR' | 'HIGH_URGENCY' | 'HITL'
  searchQuery: '',
  selectedElectionOption: 0,
};

function getSelectedItem() {
  return state.items.find((item) => item.id === state.selectedId) || state.items[0];
}

function getUrgencyBadge(score) {
  if (score >= 8) {
    return `<span class="badge-urgency high">Urgency ${score}/10</span>`;
  }
  if (score >= 5) {
    return `<span class="badge-urgency med">Urgency ${score}/10</span>`;
  }
  return `<span class="badge-urgency low">Urgency ${score}/10</span>`;
}

function formatEventTypeTitle(item) {
  const typeMap = {
    Cash_Dividend: 'Cash Dividend',
    Stock_Dividend: 'Stock Dividend',
    Merger_Acquisition: 'Tender Offer / M&A',
    Ticker_Change: 'Ticker Change',
    Spam_Or_Irrelevant: 'Non-CA Notification',
  };
  const eventName = typeMap[item.decision.event_type] || item.decision.event_type;
  
  // Extract clean company name or use subject
  let company = 'Enterprise Corp';
  if (item.subject.includes('ABC Corp')) company = 'ABC Corp';
  else if (item.subject.includes('Quantum Dynamics')) company = 'Quantum Dynamics Corp';
  else if (item.subject.includes('Novo Nordisk')) company = 'Novo Nordisk A/S';
  else if (item.subject.includes('Alpha Energy')) company = 'Alpha Energy Corp';
  else if (item.subject.includes('Nexus Microdevices')) company = 'Nexus Microdevices';
  else if (item.subject.includes('Apex Global')) company = 'Apex Global';
  else if (item.subject.includes('Northern Trust')) company = 'Custodian Break';
  
  return { eventName, company };
}

function render() {
  const app = document.getElementById('app');
  if (!app) return;

  const current = getSelectedItem();

  // Sort queue by Urgency Score 1-10 descending (High Urgency shifts to top)
  let sortedItems = [...state.items].sort((a, b) => b.decision.urgency_score - a.decision.urgency_score);

  // Search filter
  if (state.searchQuery.trim()) {
    const q = state.searchQuery.toLowerCase();
    sortedItems = sortedItems.filter(
      (item) => item.subject.toLowerCase().includes(q) || item.body.toLowerCase().includes(q)
    );
  }

  // Pill filter
  const filteredItems = sortedItems.filter((item) => {
    if (state.filter === 'ACTIONABLE') return item.decision.is_actionable;
    if (state.filter === 'OCR') return item.ocr_applied;
    if (state.filter === 'HIGH_URGENCY') return item.decision.urgency_score >= 8;
    if (state.filter === 'HITL') return item.routing.route === 'HUMAN_IN_THE_LOOP';
    return true;
  });

  app.innerHTML = `
    <!-- App Top Bar (Matches Screenshot 1 & 2) -->
    <header class="app-header">
      <div class="brand-row">
        ${
          state.activeTab === 'detail'
            ? `<button id="header-back-btn" class="btn-back">←</button>`
            : `<span class="brand-bolt">⚡</span>`
        }
        <h1 class="brand-title">
          ${
            state.activeTab === 'detail'
              ? 'Inspection Detail'
              : state.activeTab === 'pipeline'
              ? 'Jev AI Architecture'
              : 'Jev AI <span>Corporate Actions</span>'
          }
        </h1>
      </div>
      <button class="header-action-btn" id="refresh-action-btn" title="Refresh">
        ${state.activeTab === 'detail' ? '🔔' : '🔄'}
      </button>
    </header>

    <!-- Main Dynamic Screen Content -->
    <main>
      ${
        state.activeTab === 'queue'
          ? renderQueueTab(filteredItems)
          : state.activeTab === 'detail'
          ? renderDetailTab(current)
          : state.activeTab === 'pipeline'
          ? renderPipelineTab(current)
          : renderReportsTab()
      }
    </main>

    <!-- Bottom Navigation Bar (Matches Screenshots 1, 2, 3 Tabs) -->
    <nav class="bottom-nav">
      <button class="bottom-nav-item ${state.activeTab === 'queue' ? 'active' : ''}" data-tab="queue">
        <span class="nav-icon">☰</span>
        <span>Queue</span>
      </button>
      <button class="bottom-nav-item ${state.activeTab === 'detail' ? 'active' : ''}" data-tab="detail">
        <span class="nav-icon">🔍</span>
        <span>Inspection</span>
      </button>
      <button class="bottom-nav-item ${state.activeTab === 'pipeline' ? 'active' : ''}" data-tab="pipeline">
        <span class="nav-icon">⚯</span>
        <span>4-Stage Flow</span>
      </button>
      <button class="bottom-nav-item ${state.activeTab === 'reports' ? 'active' : ''}" data-tab="reports">
        <span class="nav-icon">📊</span>
        <span>Reports</span>
      </button>
    </nav>
  `;

  bindEvents();
}

/* =========================================================================
   SCREENSHOT 1: PRIORITY QUEUE VIEW
   ========================================================================= */
function renderQueueTab(items) {
  return `
    <!-- Search Bar & Filter trigger (Screenshot 1) -->
    <div class="search-filter-row">
      <div class="search-input-wrap">
        <span class="search-icon">🔍</span>
        <input 
          type="text" 
          id="queue-search" 
          class="search-input" 
          placeholder="Search corporate notices..." 
          value="${state.searchQuery}"
        />
      </div>
      <button class="filter-trigger-btn" id="filter-btn-toggle">
        <span>⚡</span> Filters
      </button>
    </div>

    <!-- Filter Pills Bar (Quick filtering) -->
    <div class="pills-container">
      <button class="filter-pill ${state.filter === 'ALL' ? 'active' : ''}" data-filter="ALL">All Notices (${state.items.length})</button>
      <button class="filter-pill ${state.filter === 'HIGH_URGENCY' ? 'active' : ''}" data-filter="HIGH_URGENCY">Urgent (8-10)</button>
      <button class="filter-pill ${state.filter === 'ACTIONABLE' ? 'active' : ''}" data-filter="ACTIONABLE">Actionable</button>
      <button class="filter-pill ${state.filter === 'OCR' ? 'active' : ''}" data-filter="OCR">Gemini OCR</button>
      <button class="filter-pill ${state.filter === 'HITL' ? 'active' : ''}" data-filter="HITL">HITL Exceptions</button>
    </div>

    <!-- Corporate Actions Notification Cards (Screenshot 1 layout) -->
    <div class="queue-cards-list">
      ${items
        .map((item, index) => {
          const { eventName, company } = formatEventTypeTitle(item);
          const isSelected = state.selectedId === item.id;
          return `
            <div class="queue-card ${isSelected ? 'selected' : ''}" data-id="${item.id}">
              <div class="card-top">
                <div class="card-num-title">
                  <span class="card-index">${index + 1}</span>
                  <div>
                    <h3 class="card-title">${eventName} - ${company}</h3>
                    <div class="meta-row">Ex-Date / Notice: ${item.date || 'Immediate'}</div>
                  </div>
                </div>
                ${getUrgencyBadge(item.decision.urgency_score)}
              </div>

              <!-- OCR & Event Tags Row -->
              <div class="tag-row">
                <span class="ocr-tag">
                  ✦ ${
                    item.ocr_applied
                      ? 'Gemini OCR: Proxy Flattened'
                      : 'Raw Text Envelope (No OCR)'
                  }
                </span>
                <span style="color: #64748b; font-size: 13px;">•••</span>
              </div>

              <!-- Bottom Stats & Action Button -->
              <div class="card-footer-row">
                <div>
                  <span style="color: #94a3b8;">Event Type:</span>
                  <strong style="color: #f1f5f9; margin-left: 4px;">${item.decision.event_type.replace('_', ' ')}</strong>
                </div>
                <button class="btn-action-primary queue-inspect-btn" data-id="${item.id}">
                  ${item.routing.route === 'GEMINI_CLIENT_NOTICE' ? 'View Action' : 'Inspect'}
                </button>
              </div>
            </div>
          `;
        })
        .join('')}
    </div>
  `;
}

/* =========================================================================
   SCREENSHOT 2: INSPECTION DETAIL & GENERATED NOTICE
   ========================================================================= */
function renderDetailTab(item) {
  if (!item) return `<div style="padding: 30px; text-align: center; color: #94a3b8;">No corporate action selected</div>`;

  const { eventName, company } = formatEventTypeTitle(item);
  const actionablePct = Math.round(item.decision.is_actionable_probability * 100);
  const ocrPct = Math.round(item.gate.ocr_probability * 100);
  const urgency = item.decision.urgency_score;

  return `
    <!-- Top Corporate Action Header Card (Screenshot 2) -->
    <div class="detail-header-card">
      <div class="detail-type-row">
        <div>
          <div class="detail-ca-label">Corporate Action Event</div>
          <h2 class="detail-ca-name">${eventName}</h2>
          <div class="detail-company">${company}</div>
        </div>
        <div style="background: rgba(6, 182, 212, 0.15); border: 1px solid rgba(6, 182, 212, 0.4); padding: 8px 12px; border-radius: 12px; font-size: 18px;">
          📊
        </div>
      </div>

      <div class="detail-grid-3">
        <div>
          <div class="detail-stat-label">Source / Sender</div>
          <div class="detail-stat-val" style="word-break: break-all; font-size: 11px;">${item.sender.split('@')[1] || item.sender}</div>
        </div>
        <div>
          <div class="detail-stat-label">Event Status</div>
          <div class="detail-stat-val" style="color: #38bdf8;">${item.decision.is_actionable ? 'Action Required' : 'Informational'}</div>
        </div>
        <div>
          <div class="detail-stat-label">Cutoff Timeline</div>
          <div class="detail-stat-val" style="color: #f87171;">Within 48h</div>
        </div>
      </div>
    </div>

    <!-- Jev AI Decision Metrics Card with Circular Urgency & Green Actionable (Screenshot 2) -->
    <div class="decision-metrics-card">
      <div class="metrics-header">Jev AI Decision Metrics</div>
      
      <div class="metrics-visual-row">
        <div class="actionable-left">
          <span class="actionable-label">Is Actionable Decision (Noul)</span>
          <div class="actionable-pct-badge">
            <span class="actionable-pct">${actionablePct}%</span>
            <span class="badge-actionable-pill">${item.decision.is_actionable ? 'ACTIONABLE' : 'INFORMATIONAL'}</span>
          </div>
        </div>

        <!-- Radial Urgency Gauge Ring -->
        <div class="urgency-gauge">
          <span class="urgency-gauge-num">${urgency}</span>
          <span class="urgency-gauge-max">/10 Urgency</span>
        </div>
      </div>

      <!-- Ingestion Gate Progress Bar -->
      <div class="gate-progress-wrap">
        <div class="gate-progress-header">
          <span>Ingestion Gate OCR Probability:</span>
          <strong>${ocrPct}%</strong>
        </div>
        <div class="gate-progress-bar-bg">
          <div class="gate-progress-bar-fill" style="width: ${ocrPct}%;"></div>
        </div>
      </div>
    </div>

    <!-- Sub-tabs: Draft / Details / Timeline (Screenshot 2) -->
    <div class="detail-subtabs">
      <button class="subtab-btn ${state.detailSubTab === 'draft' ? 'active' : ''}" data-subtab="draft">Draft Notice</button>
      <button class="subtab-btn ${state.detailSubTab === 'details' ? 'active' : ''}" data-subtab="details">Raw Matrix</button>
      <button class="subtab-btn ${state.detailSubTab === 'timeline' ? 'active' : ''}" data-subtab="timeline">Audit Trail</button>
    </div>

    <!-- Generated Client Notice Card (Screenshot 2) -->
    ${
      state.detailSubTab === 'draft'
        ? renderDraftNoticeSection(item)
        : state.detailSubTab === 'details'
        ? renderRawMatrixSection(item)
        : renderAuditTimelineSection(item)
    }
  `;
}

function renderDraftNoticeSection(item) {
  if (item.routing.client_notice) {
    const notice = item.routing.client_notice;
    return `
      <div class="notice-draft-card">
        <div class="notice-draft-header">
          <span class="notice-draft-title">Generated Client Notice</span>
          <span class="ai-tag">✦ Gemini Vision AI</span>
        </div>

        <div class="notice-draft-subject">${notice.subject}</div>
        <p class="notice-draft-desc">
          ${notice.event_summary || 'Please review the election terms below and designate your election instructions prior to the designated deadline.'}
        </p>

        <!-- Election Options Radio List (Screenshot 2 style) -->
        <div class="election-options-list">
          <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700; margin-bottom: 8px;">
            Election Choices:
          </div>
          ${(notice.election_options || [
            'Option 1: Cash Option (Full Cash Payout)',
            'Option 2: Stock Alternative (Share Reinvestment)',
            'Option 3: Default / Take No Action'
          ])
            .map((opt, i) => `
              <label class="election-option-item">
                <input 
                  type="radio" 
                  name="election-choice" 
                  value="${i}" 
                  ${state.selectedElectionOption === i ? 'checked' : ''}
                  style="accent-color: #38bdf8;"
                />
                <span>${opt.replace(/^- /, '')}</span>
              </label>
            `)
            .join('')}
        </div>

        <div style="font-size: 12px; color: #94a3b8; margin-bottom: 14px;">
          <strong style="color: #e2e8f0;">Deadline for Election:</strong> 
          <span style="color: #f87171;">${notice.deadline || 'Within 48h of notice'}</span>
        </div>

        <button class="btn-process-election" id="submit-election-btn">
          Process Election
        </button>
      </div>
    `;
  }

  // HITL Exception fallback card
  if (item.routing.hitl_item) {
    const hitl = item.routing.hitl_item;
    return `
      <div class="notice-draft-card" style="border-color: rgba(245, 158, 11, 0.5);">
        <div class="notice-draft-header">
          <span class="notice-draft-title" style="color: #fbbf24;">⚠️ Human-in-the-Loop Desk Required</span>
          <span class="badge-urgency med">Risk: ${hitl.risk_level}</span>
        </div>
        <div class="notice-draft-subject" style="color: #fde68a;">${hitl.reason}</div>
        <p class="notice-draft-desc">${hitl.suggested_action}</p>
        <button class="btn-process-election" style="background: linear-gradient(135deg, #78350f, #d97706); border-color: #f59e0b;" id="submit-election-btn">
          Resolve Exception
        </button>
      </div>
    `;
  }

  return `<div class="notice-draft-card"><p class="notice-draft-desc">Informational event; no client action required.</p></div>`;
}

function renderRawMatrixSection(item) {
  return `
    <div class="notice-draft-card">
      <div class="notice-draft-header">
        <span class="notice-draft-title">Normalized Text Envelope</span>
        <span class="ocr-tag">${item.ocr_applied ? 'OCR Applied' : 'Raw Text'}</span>
      </div>
      <pre style="background: #020617; border: 1px solid #1e293b; padding: 12px; border-radius: 10px; font-size: 11px; color: #cbd5e1; max-height: 240px; overflow-y: auto; white-space: pre-wrap;">${item.normalized_preview || item.body}</pre>
    </div>
  `;
}

function renderAuditTimelineSection(item) {
  return `
    <div class="notice-draft-card">
      <div class="notice-draft-title" style="margin-bottom: 10px;">Execution Timings</div>
      <div style="font-size: 12px; color: #94a3b8; line-height: 1.8;">
        <div>• <strong>Stage 1 (Ingestion Gate):</strong> ${item.gate.latency_ms || 40.5} ms</div>
        <div>• <strong>Stage 2 (OCR / Envelope):</strong> ${item.ocr_applied ? '320 ms (Gemini)' : '0 ms (Bypassed)'}</div>
        <div>• <strong>Stage 3 (Core Decision):</strong> ${item.decision.latency_ms || 60.5} ms</div>
        <div>• <strong>Total End-to-End Latency:</strong> ${item.total_latency_ms || 105.0} ms</div>
      </div>
    </div>
  `;
}

/* =========================================================================
   SCREENSHOT 3: 4-STAGE PIPELINE FLOW ARCHITECTURE
   ========================================================================= */
function renderPipelineTab(item) {
  return `
    <div class="pipeline-header">
      <h2 style="font-size: 17px; font-weight: 800; color: #38bdf8;">JEV AI: CORPORATE ACTIONS FLOW</h2>
      <div class="pipeline-subtitle">PROCESS ARCHITECTURE</div>
    </div>

    <!-- Stage 1 Card (Blue Neon) -->
    <div class="flow-step-card">
      <div class="flow-step-top">
        <span class="flow-step-title">Stage 1: Ingestion Gate</span>
        <span style="font-size: 16px; color: #38bdf8;">📄</span>
      </div>
      <p class="flow-step-desc">Receive incoming notices (email, SWIFT) and evaluate if visual OCR is mandatory.</p>
      <div class="flow-step-highlight">
        Noul Check: requires_heavy_ocr (Calibrated Prob: ${(item.gate.ocr_probability * 100).toFixed(1)}%)
      </div>
      <div class="flow-step-status">STATUS: ${item.gate.requires_heavy_ocr ? 'OCR Required (Triggered)' : 'Raw Envelope (Proceed directly)'}</div>
    </div>

    <div class="flow-connector-line">↓</div>

    <!-- Stage 2 Card (Purple Neon) -->
    <div class="flow-step-card purple">
      <div class="flow-step-top">
        <span class="flow-step-title">Stage 2: Data Normalization</span>
        <span style="font-size: 16px; color: #c084fc;">👁️</span>
      </div>
      <p class="flow-step-desc">Gemini Vision AI flattens PDFs and complex tables into a normalized corporate action matrix.</p>
      <div class="flow-step-highlight">
        Gemini Vision: ${item.ocr_applied ? 'Document Flattened & Tables Extracted' : 'Standard Text Normalized'}
      </div>
      <div class="flow-step-status" style="color: #c084fc;">STATUS: Active (${item.ocr_applied ? 'OCR Executed' : 'Direct Envelope'})</div>
    </div>

    <div class="flow-connector-line">↓</div>

    <!-- Stage 3 Card (Blue Neon) -->
    <div class="flow-step-card">
      <div class="flow-step-top">
        <span class="flow-step-title">Stage 3: Decision Matrix</span>
        <span style="font-size: 16px; color: #38bdf8;">⚡</span>
      </div>
      <p class="flow-step-desc">TypeSafe AI Jev System One evaluates Event Choice, Actionability, and Urgency 1-10.</p>
      <div class="flow-step-highlight">
        CHOICE: ${item.decision.event_type.replace('_', ' ')} | URGENCY: ${item.decision.urgency_score}/10
      </div>
      <div class="flow-step-status">STATUS: Calibrated (${(item.decision.is_actionable_probability * 100).toFixed(1)}% Actionable)</div>
    </div>

    <div class="flow-connector-line">↓</div>

    <!-- Stage 4 Card (Purple Neon) -->
    <div class="flow-step-card purple">
      <div class="flow-step-top">
        <span class="flow-step-title">Stage 4: Router Execution</span>
        <span style="font-size: 16px; color: #c084fc;">🔀</span>
      </div>
      <p class="flow-step-desc">Auto-drafts election notices or routes edge cases & breaks to the operations desk.</p>
      <div class="flow-step-highlight">
        DESTINATION: ${item.routing.route === 'GEMINI_CLIENT_NOTICE' ? 'Gemini Client Notice (Automated)' : 'Human-in-the-Loop Desk'}
      </div>
      <div class="flow-step-status" style="color: #34d399;">STATUS: Successfully Routed</div>
    </div>
  `;
}

function renderReportsTab() {
  const total = state.items.length;
  const actionable = state.items.filter((i) => i.decision.is_actionable).length;
  const ocrCount = state.items.filter((i) => i.ocr_applied).length;
  const hitlCount = state.items.filter((i) => i.routing.route === 'HUMAN_IN_THE_LOOP').length;

  return `
    <div style="padding: 10px 0;">
      <h2 style="font-size: 17px; font-weight: 800; color: #ffffff; margin-bottom: 12px;">Operational Analytics</h2>
      
      <div class="detail-header-card" style="margin-bottom: 12px;">
        <div class="detail-ca-label">Processed Batch Summary</div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 10px;">
          <div style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 12px;">
            <div style="font-size: 26px; font-weight: 800; color: #38bdf8;">${total}</div>
            <div style="font-size: 11px; color: #94a3b8;">Total Notices</div>
          </div>
          <div style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 12px;">
            <div style="font-size: 26px; font-weight: 800; color: #10b981;">${actionable}</div>
            <div style="font-size: 11px; color: #94a3b8;">Actionable (${Math.round((actionable / total) * 100)}%)</div>
          </div>
          <div style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 12px;">
            <div style="font-size: 26px; font-weight: 800; color: #22d3ee;">${ocrCount}</div>
            <div style="font-size: 11px; color: #94a3b8;">Gemini OCR Executed</div>
          </div>
          <div style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 12px;">
            <div style="font-size: 26px; font-weight: 800; color: #fbbf24;">${hitlCount}</div>
            <div style="font-size: 11px; color: #94a3b8;">HITL Exception Escapes</div>
          </div>
        </div>
      </div>

      <div class="decision-metrics-card">
        <div class="metrics-header">Average Decision Latencies</div>
        <div style="font-size: 12px; color: #cbd5e1; line-height: 2;">
          <div>• Ingestion Gate (Noul): <strong style="color: #38bdf8;">41 ms</strong></div>
          <div>• Core Classification & Urgency: <strong style="color: #38bdf8;">62 ms</strong></div>
          <div>• Sub-100ms SLA Compliance: <strong style="color: #10b981;">100%</strong></div>
        </div>
      </div>
    </div>
  `;
}

/* =========================================================================
   INTERACTION BINDINGS
   ========================================================================= */
function bindEvents() {
  // Bottom Navigation tabs
  document.querySelectorAll('.bottom-nav-item').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const tab = e.currentTarget.getAttribute('data-tab');
      if (tab) {
        state.activeTab = tab;
        render();
      }
    });
  });

  // Top header back button in detail view
  const backBtn = document.getElementById('header-back-btn');
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      state.activeTab = 'queue';
      render();
    });
  }

  // Search input
  const searchInput = document.getElementById('queue-search');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value;
      render();
      const updated = document.getElementById('queue-search');
      if (updated) {
        updated.focus();
        updated.setSelectionRange(state.searchQuery.length, state.searchQuery.length);
      }
    });
  }

  // Filter pills
  document.querySelectorAll('.filter-pill').forEach((pill) => {
    pill.addEventListener('click', (e) => {
      const filter = e.currentTarget.getAttribute('data-filter');
      if (filter) {
        state.filter = filter;
        render();
      }
    });
  });

  // Filter trigger toggle
  const filterBtnToggle = document.getElementById('filter-btn-toggle');
  if (filterBtnToggle) {
    filterBtnToggle.addEventListener('click', () => {
      state.filter = state.filter === 'ALL' ? 'HIGH_URGENCY' : 'ALL';
      render();
    });
  }

  // Selecting queue cards
  document.querySelectorAll('.queue-card').forEach((card) => {
    card.addEventListener('click', (e) => {
      const id = e.currentTarget.getAttribute('data-id');
      if (id) {
        state.selectedId = id;
        state.activeTab = 'detail';
        render();
      }
    });
  });

  // Inspect button inside cards
  document.querySelectorAll('.queue-inspect-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const id = e.currentTarget.getAttribute('data-id');
      if (id) {
        state.selectedId = id;
        state.activeTab = 'detail';
        render();
      }
    });
  });

  // Detail sub-tabs
  document.querySelectorAll('.subtab-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const sub = e.currentTarget.getAttribute('data-subtab');
      if (sub) {
        state.detailSubTab = sub;
        render();
      }
    });
  });

  // Radio election selection
  document.querySelectorAll('input[name="election-choice"]').forEach((radio) => {
    radio.addEventListener('change', (e) => {
      state.selectedElectionOption = parseInt(e.target.value, 10);
    });
  });

  // Process Election Button
  const processBtn = document.getElementById('submit-election-btn');
  if (processBtn) {
    processBtn.addEventListener('click', () => {
      processBtn.textContent = '✓ Election Instructions Submitted';
      processBtn.style.background = '#059669';
      setTimeout(() => {
        alert('Corporate action election recorded and dispatched to custody desk.');
      }, 300);
    });
  }

  // Refresh button
  const refreshBtn = document.getElementById('refresh-action-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      render();
    });
  }
}

// Initial render
render();
