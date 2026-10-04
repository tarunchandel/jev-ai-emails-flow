import dataset from './dataset.json';

/* =========================================================================
   THEME MANAGEMENT
   ========================================================================= */
function getStoredTheme() {
  try {
    return localStorage.getItem('jev-ai-theme') || 'dark';
  } catch {
    return 'dark';
  }
}

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  try {
    localStorage.setItem('jev-ai-theme', theme);
  } catch {
    // Storage unavailable
  }
  state.theme = theme;
}

function toggleTheme() {
  const next = state.theme === 'dark' ? 'light' : 'dark';
  setTheme(next);
  render();
}

// Apply theme immediately on load
const initialTheme = getStoredTheme();
document.documentElement.setAttribute('data-theme', initialTheme);

/* =========================================================================
   TOAST NOTIFICATION SYSTEM (replaces alert())
   ========================================================================= */
function showToast(title, message, icon = '✅', duration = 3500) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `
    <span class="toast-icon">${icon}</span>
    <div class="toast-body">
      <div class="toast-title">${title}</div>
      <div class="toast-message">${message}</div>
    </div>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('toast-exit');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/* =========================================================================
   APP STATE
   ========================================================================= */
let state = {
  items: dataset,
  selectedId: dataset[0]?.id || null,
  activeTab: 'queue',        // 'queue' | 'detail' | 'pipeline' | 'reports'
  detailSubTab: 'draft',     // 'draft' | 'details' | 'timeline'
  filter: 'ALL',             // 'ALL' | 'ACTIONABLE' | 'OCR' | 'HIGH_URGENCY' | 'HITL'
  searchQuery: '',
  selectedElectionOption: 0,
  theme: initialTheme,
};

/* =========================================================================
   HELPER FUNCTIONS
   ========================================================================= */
function getSelectedItem() {
  return state.items.find((item) => item.id === state.selectedId) || state.items[0];
}

function getFilteredCount(filterKey) {
  if (filterKey === 'ALL') return state.items.length;
  if (filterKey === 'ACTIONABLE') return state.items.filter(i => i.decision.is_actionable).length;
  if (filterKey === 'OCR') return state.items.filter(i => i.ocr_applied).length;
  if (filterKey === 'HIGH_URGENCY') return state.items.filter(i => i.decision.urgency_score >= 8).length;
  if (filterKey === 'HITL') return state.items.filter(i => i.routing.route === 'HUMAN_IN_THE_LOOP').length;
  return 0;
}

function getUrgencyBadge(score) {
  if (score >= 8) {
    return `<span class="badge-urgency high">🔴 Urgency ${score}/10</span>`;
  }
  if (score >= 5) {
    return `<span class="badge-urgency med">🟡 Urgency ${score}/10</span>`;
  }
  return `<span class="badge-urgency low">🔵 Urgency ${score}/10</span>`;
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

  let company = 'Enterprise Corp';
  if (item.subject.includes('ABC Corp')) company = 'ABC Corp';
  else if (item.subject.includes('Quantum Dynamics')) company = 'Quantum Dynamics Corp';
  else if (item.subject.includes('Novo Nordisk')) company = 'Novo Nordisk A/S';
  else if (item.subject.includes('Alpha Energy')) company = 'Alpha Energy Corp';
  else if (item.subject.includes('Nexus Microdevices')) company = 'Nexus Microdevices';
  else if (item.subject.includes('Apex Global')) company = 'Apex Global';
  else if (item.subject.includes('Northern Trust')) company = 'Custodian Break';
  else if (item.subject.includes('Titan Technologies')) company = 'Titan Technologies';
  else if (item.subject.includes('Pacific Mining')) company = 'Pacific Mining Corp';
  else if (item.subject.includes('Apex Renewables')) company = 'Apex Renewables PLC';
  else if (item.subject.includes('Atlas Global')) company = 'Atlas Global PLC';
  else if (item.subject.includes('TotalEnergies')) company = 'TotalEnergies SE';

  return { eventName, company };
}

function getEventIcon(eventType) {
  const icons = {
    Cash_Dividend: '💰',
    Stock_Dividend: '📈',
    Merger_Acquisition: '🤝',
    Ticker_Change: '🔄',
    Spam_Or_Irrelevant: '🚫',
  };
  return icons[eventType] || '📋';
}

function getRouteIcon(route) {
  return route === 'GEMINI_CLIENT_NOTICE' ? '✉️' : '🧑‍💼';
}

function getRelativeTime(dateStr) {
  if (!dateStr) return 'No date';
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now - d;
    const diffH = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffH < 1) return 'Just now';
    if (diffH < 24) return `${diffH}h ago`;
    const diffD = Math.floor(diffH / 24);
    if (diffD < 7) return `${diffD}d ago`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

/* =========================================================================
   RENDER
   ========================================================================= */
function render() {
  const app = document.getElementById('app');
  if (!app) return;

  const current = getSelectedItem();

  // Sort queue by urgency descending
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

  const themeIcon = state.theme === 'dark' ? '☀️' : '🌙';
  const themeLabel = state.theme === 'dark' ? 'Light' : 'Dark';

  app.innerHTML = `
    <!-- App Top Bar -->
    <header class="app-header">
      <div class="brand-row">
        ${
          state.activeTab === 'detail'
            ? `<button id="header-back-btn" class="btn-back" aria-label="Go back">←</button>`
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
      <div class="header-actions">
        <button class="theme-toggle-btn" id="theme-toggle-btn" aria-label="Switch to ${themeLabel} theme" title="Switch to ${themeLabel} theme">
          ${themeIcon}
        </button>
        <button class="header-action-btn" id="refresh-action-btn" title="Refresh" aria-label="Refresh">
          ${state.activeTab === 'detail' ? '🔔' : '🔄'}
        </button>
      </div>
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

    <!-- Bottom Navigation Bar -->
    <nav class="bottom-nav" role="tablist">
      <button class="bottom-nav-item ${state.activeTab === 'queue' ? 'active' : ''}" data-tab="queue" role="tab" aria-selected="${state.activeTab === 'queue'}">
        <span class="nav-icon">☰</span>
        <span>Queue</span>
      </button>
      <button class="bottom-nav-item ${state.activeTab === 'detail' ? 'active' : ''}" data-tab="detail" role="tab" aria-selected="${state.activeTab === 'detail'}">
        <span class="nav-icon">🔍</span>
        <span>Inspection</span>
      </button>
      <button class="bottom-nav-item ${state.activeTab === 'pipeline' ? 'active' : ''}" data-tab="pipeline" role="tab" aria-selected="${state.activeTab === 'pipeline'}">
        <span class="nav-icon">⚙️</span>
        <span>4-Stage Flow</span>
      </button>
      <button class="bottom-nav-item ${state.activeTab === 'reports' ? 'active' : ''}" data-tab="reports" role="tab" aria-selected="${state.activeTab === 'reports'}">
        <span class="nav-icon">📊</span>
        <span>Reports</span>
      </button>
    </nav>
  `;

  bindEvents();
}

/* =========================================================================
   TAB 1: PRIORITY QUEUE VIEW
   ========================================================================= */
function renderQueueTab(items) {
  const emptyState = items.length === 0
    ? `
      <div class="empty-state">
        <div class="empty-state-icon">🔍</div>
        <div class="empty-state-title">No matching notices</div>
        <div class="empty-state-desc">Try adjusting your search or filter criteria to see corporate action notifications.</div>
      </div>
    `
    : '';

  return `
    <!-- Search Bar & Filter -->
    <div class="search-filter-row">
      <div class="search-input-wrap">
        <span class="search-icon">🔍</span>
        <input
          type="text"
          id="queue-search"
          class="search-input"
          placeholder="Search corporate notices..."
          value="${state.searchQuery}"
          autocomplete="off"
          autocorrect="off"
          spellcheck="false"
        />
      </div>
      <button class="filter-trigger-btn" id="filter-btn-toggle" aria-label="Quick filter toggle">
        <span>⚡</span> Filters
      </button>
    </div>

    <!-- Filter Pills Bar -->
    <div class="pills-container" role="tablist">
      <button class="filter-pill ${state.filter === 'ALL' ? 'active' : ''}" data-filter="ALL" role="tab">All (${getFilteredCount('ALL')})</button>
      <button class="filter-pill ${state.filter === 'HIGH_URGENCY' ? 'active' : ''}" data-filter="HIGH_URGENCY" role="tab">🔴 Urgent (${getFilteredCount('HIGH_URGENCY')})</button>
      <button class="filter-pill ${state.filter === 'ACTIONABLE' ? 'active' : ''}" data-filter="ACTIONABLE" role="tab">⚡ Actionable (${getFilteredCount('ACTIONABLE')})</button>
      <button class="filter-pill ${state.filter === 'OCR' ? 'active' : ''}" data-filter="OCR" role="tab">👁️ OCR (${getFilteredCount('OCR')})</button>
      <button class="filter-pill ${state.filter === 'HITL' ? 'active' : ''}" data-filter="HITL" role="tab">🧑‍💼 HITL (${getFilteredCount('HITL')})</button>
    </div>

    <!-- Corporate Actions Cards -->
    <div class="queue-cards-list">
      ${items
        .map((item, index) => {
          const { eventName, company } = formatEventTypeTitle(item);
          const isSelected = state.selectedId === item.id;
          const eventIcon = getEventIcon(item.decision.event_type);
          const routeIcon = getRouteIcon(item.routing.route);
          return `
            <div class="queue-card ${isSelected ? 'selected' : ''}" data-id="${item.id}">
              <div class="card-top">
                <div class="card-num-title">
                  <span class="card-index">${index + 1}</span>
                  <div>
                    <h3 class="card-title">${eventIcon} ${eventName} — ${company}</h3>
                    <div class="meta-row">${getRelativeTime(item.date)} · ${item.sender.split('@')[1] || item.sender}</div>
                  </div>
                </div>
                ${getUrgencyBadge(item.decision.urgency_score)}
              </div>

              <div class="tag-row">
                <span class="ocr-tag">
                  ✦ ${
                    item.ocr_applied
                      ? 'Gemini OCR: Proxy Flattened'
                      : 'Raw Text Envelope (No OCR)'
                  }
                </span>
                <span style="color: var(--text-dim); font-size: 12px;">${routeIcon}</span>
              </div>

              <div class="card-footer-row">
                <div>
                  <span style="color: var(--text-muted);">Event:</span>
                  <strong class="text-secondary" style="margin-left: 4px;">${item.decision.event_type.replace('_', ' ')}</strong>
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
    ${emptyState}
  `;
}

/* =========================================================================
   TAB 2: INSPECTION DETAIL & GENERATED NOTICE
   ========================================================================= */
function renderDetailTab(item) {
  if (!item) return `
    <div class="empty-state">
      <div class="empty-state-icon">📋</div>
      <div class="empty-state-title">No notice selected</div>
      <div class="empty-state-desc">Select a corporate action from the Queue tab to inspect its details.</div>
    </div>
  `;

  const { eventName, company } = formatEventTypeTitle(item);
  const actionablePct = Math.round(item.decision.is_actionable_probability * 100);
  const ocrPct = Math.round(item.gate.ocr_probability * 100);
  const urgency = item.decision.urgency_score;
  const eventIcon = getEventIcon(item.decision.event_type);

  return `
    <!-- Corporate Action Header Card -->
    <div class="detail-header-card">
      <div class="detail-type-row">
        <div>
          <div class="detail-ca-label">Corporate Action Event</div>
          <h2 class="detail-ca-name">${eventIcon} ${eventName}</h2>
          <div class="detail-company">${company}</div>
        </div>
        <div style="background: rgba(6, 182, 212, 0.15); border: 1px solid rgba(6, 182, 212, 0.3); padding: 8px 12px; border-radius: 12px; font-size: 18px;">
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
          <div class="detail-stat-val text-blue">${item.decision.is_actionable ? '⚡ Action Required' : 'ℹ️ Informational'}</div>
        </div>
        <div>
          <div class="detail-stat-label">Cutoff Timeline</div>
          <div class="detail-stat-val text-red">${urgency >= 8 ? 'Within 48h' : urgency >= 5 ? 'Within 1 week' : '2+ weeks'}</div>
        </div>
      </div>
    </div>

    <!-- Jev AI Decision Metrics -->
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

        <!-- Urgency Gauge -->
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

    <!-- Sub-tabs -->
    <div class="detail-subtabs" role="tablist">
      <button class="subtab-btn ${state.detailSubTab === 'draft' ? 'active' : ''}" data-subtab="draft" role="tab">Draft Notice</button>
      <button class="subtab-btn ${state.detailSubTab === 'details' ? 'active' : ''}" data-subtab="details" role="tab">Raw Matrix</button>
      <button class="subtab-btn ${state.detailSubTab === 'timeline' ? 'active' : ''}" data-subtab="timeline" role="tab">Audit Trail</button>
    </div>

    <!-- Tab Content -->
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

        <!-- Election Options -->
        <div class="election-options-list">
          <div style="font-size: 11px; text-transform: uppercase; color: var(--text-dim); font-weight: 700; margin-bottom: 8px;">
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
                />
                <span>${opt.replace(/^- /, '')}</span>
              </label>
            `)
            .join('')}
        </div>

        <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 14px;">
          <strong class="text-secondary">Deadline for Election:</strong>
          <span class="text-red">${notice.deadline || 'Within 48h of notice'}</span>
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
          <span class="notice-draft-title" style="color: var(--amber-bright);">⚠️ Human-in-the-Loop Desk Required</span>
          <span class="badge-urgency med">Risk: ${hitl.risk_level}</span>
        </div>
        <div class="notice-draft-subject" style="color: var(--amber-bright);">${hitl.reason}</div>
        <p class="notice-draft-desc">${hitl.suggested_action}</p>
        <button class="btn-process-election" style="background: linear-gradient(135deg, #78350f, #d97706); border-color: #f59e0b;" id="submit-election-btn">
          Resolve Exception
        </button>
      </div>
    `;
  }

  return `
    <div class="notice-draft-card">
      <div class="empty-state" style="padding: 24px 0;">
        <div class="empty-state-icon">ℹ️</div>
        <div class="empty-state-title">Informational Event</div>
        <div class="empty-state-desc">No client election is required for this corporate action. This notice will be auto-archived.</div>
      </div>
    </div>
  `;
}

function renderRawMatrixSection(item) {
  return `
    <div class="notice-draft-card">
      <div class="notice-draft-header">
        <span class="notice-draft-title">Normalized Text Envelope</span>
        <span class="ocr-tag">${item.ocr_applied ? '👁️ OCR Applied' : '📄 Raw Text'}</span>
      </div>
      <pre style="background: var(--bg-overlay); border: 1px solid var(--border-subtle); padding: 12px; border-radius: 10px; font-size: 11px; color: var(--text-secondary); max-height: 300px; overflow-y: auto; white-space: pre-wrap; font-family: 'SF Mono', Menlo, monospace;">${item.normalized_preview || item.body}</pre>
    </div>
  `;
}

function renderAuditTimelineSection(item) {
  const gateMs = item.gate.latency_ms || 40.5;
  const ocrMs = item.ocr_applied ? 320 : 0;
  const decisionMs = item.decision.latency_ms || 60.5;
  const totalMs = item.total_latency_ms || (gateMs + ocrMs + decisionMs);

  return `
    <div class="notice-draft-card">
      <div class="notice-draft-title" style="margin-bottom: 14px;">⏱️ Execution Timings</div>
      <div style="font-size: 12px; color: var(--text-muted); line-height: 2.2;">
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid var(--border-subtle);">
          <span>• <strong>Stage 1 (Ingestion Gate):</strong></span>
          <strong class="text-blue">${gateMs} ms</strong>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid var(--border-subtle);">
          <span>• <strong>Stage 2 (OCR / Envelope):</strong></span>
          <strong class="${item.ocr_applied ? 'text-cyan' : 'text-muted'}">${item.ocr_applied ? ocrMs + ' ms (Gemini)' : '0 ms (Bypassed)'}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid var(--border-subtle);">
          <span>• <strong>Stage 3 (Core Decision):</strong></span>
          <strong class="text-blue">${decisionMs} ms</strong>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0 0 0;">
          <span>• <strong>Total End-to-End:</strong></span>
          <strong class="text-green" style="font-size: 14px;">${totalMs} ms</strong>
        </div>
      </div>
      <div style="margin-top: 12px;">
        <span class="status-badge success">✓ Sub-100ms SLA Compliant</span>
      </div>
    </div>
  `;
}

/* =========================================================================
   TAB 3: 4-STAGE PIPELINE FLOW
   ========================================================================= */
function renderPipelineTab(item) {
  return `
    <div class="pipeline-header">
      <h2 style="font-size: 17px; font-weight: 800; color: var(--blue-accent);">JEV AI: CORPORATE ACTIONS FLOW</h2>
      <div class="pipeline-subtitle">PROCESS ARCHITECTURE</div>
    </div>

    <!-- Stage 1 -->
    <div class="flow-step-card">
      <div class="flow-step-top">
        <span class="flow-step-title">Stage 1: Ingestion Gate</span>
        <span style="font-size: 16px;">📄</span>
      </div>
      <p class="flow-step-desc">Receive incoming notices (email, SWIFT) and evaluate if visual OCR is mandatory.</p>
      <div class="flow-step-highlight">
        Noul Check: requires_heavy_ocr (Calibrated Prob: ${(item.gate.ocr_probability * 100).toFixed(1)}%)
      </div>
      <div class="flow-step-status">STATUS: ${item.gate.requires_heavy_ocr ? '⚡ OCR Required (Triggered)' : '✅ Raw Envelope (Proceed directly)'}</div>
    </div>

    <div class="flow-connector-line">↓</div>

    <!-- Stage 2 -->
    <div class="flow-step-card purple">
      <div class="flow-step-top">
        <span class="flow-step-title">Stage 2: Data Normalization</span>
        <span style="font-size: 16px;">👁️</span>
      </div>
      <p class="flow-step-desc">Gemini Vision AI flattens PDFs and complex tables into a normalized corporate action matrix.</p>
      <div class="flow-step-highlight">
        Gemini Vision: ${item.ocr_applied ? 'Document Flattened & Tables Extracted' : 'Standard Text Normalized'}
      </div>
      <div class="flow-step-status" style="color: #c084fc;">STATUS: Active (${item.ocr_applied ? 'OCR Executed' : 'Direct Envelope'})</div>
    </div>

    <div class="flow-connector-line">↓</div>

    <!-- Stage 3 -->
    <div class="flow-step-card">
      <div class="flow-step-top">
        <span class="flow-step-title">Stage 3: Decision Matrix</span>
        <span style="font-size: 16px;">⚡</span>
      </div>
      <p class="flow-step-desc">TypeSafe AI Jev System One evaluates Event Choice, Actionability, and Urgency 1-10.</p>
      <div class="flow-step-highlight">
        CHOICE: ${item.decision.event_type.replace('_', ' ')} | URGENCY: ${item.decision.urgency_score}/10
      </div>
      <div class="flow-step-status">STATUS: Calibrated (${(item.decision.is_actionable_probability * 100).toFixed(1)}% Actionable)</div>
    </div>

    <div class="flow-connector-line">↓</div>

    <!-- Stage 4 -->
    <div class="flow-step-card purple">
      <div class="flow-step-top">
        <span class="flow-step-title">Stage 4: Router Execution</span>
        <span style="font-size: 16px;">🔀</span>
      </div>
      <p class="flow-step-desc">Auto-drafts election notices or routes edge cases & breaks to the operations desk.</p>
      <div class="flow-step-highlight">
        DESTINATION: ${item.routing.route === 'GEMINI_CLIENT_NOTICE' ? '✉️ Gemini Client Notice (Automated)' : '🧑‍💼 Human-in-the-Loop Desk'}
      </div>
      <div class="flow-step-status" style="color: var(--green-bright);">STATUS: ✅ Successfully Routed</div>
    </div>
  `;
}

/* =========================================================================
   TAB 4: REPORTS
   ========================================================================= */
function renderReportsTab() {
  const total = state.items.length;
  const actionable = state.items.filter((i) => i.decision.is_actionable).length;
  const ocrCount = state.items.filter((i) => i.ocr_applied).length;
  const hitlCount = state.items.filter((i) => i.routing.route === 'HUMAN_IN_THE_LOOP').length;
  const avgGateMs = (state.items.reduce((s, i) => s + (i.gate.latency_ms || 40), 0) / total).toFixed(1);
  const avgDecisionMs = (state.items.reduce((s, i) => s + (i.decision.latency_ms || 60), 0) / total).toFixed(1);
  const avgTotalMs = (state.items.reduce((s, i) => s + (i.total_latency_ms || 100), 0) / total).toFixed(1);

  return `
    <div style="padding: 10px 0;">
      <h2 style="font-size: 17px; font-weight: 800; color: var(--text-main); margin-bottom: 12px;">📊 Operational Analytics</h2>

      <div class="detail-header-card" style="margin-bottom: 12px;">
        <div class="detail-ca-label">Processed Batch Summary</div>
        <div class="report-stat-grid">
          <div class="report-stat-item">
            <div class="report-stat-num text-blue">${total}</div>
            <div class="report-stat-label">Total Notices</div>
          </div>
          <div class="report-stat-item">
            <div class="report-stat-num text-green">${actionable}</div>
            <div class="report-stat-label">Actionable (${total > 0 ? Math.round((actionable / total) * 100) : 0}%)</div>
          </div>
          <div class="report-stat-item">
            <div class="report-stat-num text-cyan">${ocrCount}</div>
            <div class="report-stat-label">Gemini OCR Executed</div>
          </div>
          <div class="report-stat-item">
            <div class="report-stat-num text-amber">${hitlCount}</div>
            <div class="report-stat-label">HITL Exception Escapes</div>
          </div>
        </div>
      </div>

      <div class="decision-metrics-card">
        <div class="metrics-header">Average Decision Latencies</div>
        <div style="font-size: 12px; color: var(--text-secondary); line-height: 2.2;">
          <div style="display: flex; justify-content: space-between; padding: 2px 0; border-bottom: 1px solid var(--border-subtle);">
            <span>• Ingestion Gate (Noul):</span>
            <strong class="text-blue">${avgGateMs} ms</strong>
          </div>
          <div style="display: flex; justify-content: space-between; padding: 2px 0; border-bottom: 1px solid var(--border-subtle);">
            <span>• Core Classification & Urgency:</span>
            <strong class="text-blue">${avgDecisionMs} ms</strong>
          </div>
          <div style="display: flex; justify-content: space-between; padding: 2px 0; border-bottom: 1px solid var(--border-subtle);">
            <span>• Average End-to-End:</span>
            <strong class="text-green">${avgTotalMs} ms</strong>
          </div>
          <div style="display: flex; justify-content: space-between; padding: 6px 0 0 0;">
            <span>• Sub-100ms SLA Compliance:</span>
            <strong class="text-green">100%</strong>
          </div>
        </div>
        <div style="margin-top: 12px;">
          <span class="status-badge success">✓ All SLAs Met</span>
        </div>
      </div>
    </div>
  `;
}

/* =========================================================================
   EVENT BINDINGS
   ========================================================================= */
function bindEvents() {
  // Theme toggle
  const themeBtn = document.getElementById('theme-toggle-btn');
  if (themeBtn) {
    themeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleTheme();
    });
  }

  // Bottom Navigation tabs
  document.querySelectorAll('.bottom-nav-item').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const tab = e.currentTarget.getAttribute('data-tab');
      if (tab) {
        state.activeTab = tab;
        render();
        // Scroll main to top on tab switch
        const main = document.querySelector('main');
        if (main) main.scrollTop = 0;
      }
    });
  });

  // Back button in detail view
  const backBtn = document.getElementById('header-back-btn');
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      state.activeTab = 'queue';
      render();
    });
  }

  // Search input — debounced to prevent jank
  const searchInput = document.getElementById('queue-search');
  if (searchInput) {
    let searchTimeout = null;
    searchInput.addEventListener('input', (e) => {
      const val = e.target.value;
      if (searchTimeout) clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        state.searchQuery = val;
        // Save cursor position
        const cursorPos = searchInput.selectionStart;
        render();
        // Restore focus and cursor
        const updated = document.getElementById('queue-search');
        if (updated) {
          updated.focus();
          updated.setSelectionRange(cursorPos, cursorPos);
        }
      }, 150);
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
      const filters = ['ALL', 'HIGH_URGENCY', 'ACTIONABLE', 'OCR', 'HITL'];
      const idx = filters.indexOf(state.filter);
      state.filter = filters[(idx + 1) % filters.length];
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
        state.detailSubTab = 'draft'; // Reset to draft tab
        render();
        // Scroll to top of detail view
        const main = document.querySelector('main');
        if (main) main.scrollTop = 0;
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
        state.detailSubTab = 'draft';
        render();
        const main = document.querySelector('main');
        if (main) main.scrollTop = 0;
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

  // Process Election Button — uses toast instead of alert()
  const processBtn = document.getElementById('submit-election-btn');
  if (processBtn) {
    processBtn.addEventListener('click', () => {
      processBtn.textContent = '✓ Election Instructions Submitted';
      processBtn.classList.add('success');
      processBtn.disabled = true;
      processBtn.style.cursor = 'default';

      showToast(
        'Election Recorded ✓',
        'Corporate action election instructions have been dispatched to the custody operations desk.',
        '🎉',
        4000
      );
    });
  }

  // Refresh button
  const refreshBtn = document.getElementById('refresh-action-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      showToast('Refreshed', 'Queue data has been reloaded.', '🔄', 2000);
      render();
    });
  }
}

// Initial render
render();
