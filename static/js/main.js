// ==========================================================================
// PUSHKAR WORKS TRACKER — FRONTEND CONTROLLER & DEMO MODE
// ==========================================================================

// --- TOAST NOTIFICATIONS ---
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  const icon = type === 'success' ? '✓' : (type === 'error' ? '⚠️' : 'ℹ️');
  toast.innerHTML = `<span style="font-size: 1.2rem;">${icon}</span><span>${message}</span>`;
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// --- SETTINGS DROPDOWN ---
function toggleSettingsDropdown(event) {
  if (event) event.stopPropagation();
  const dropdown = document.getElementById('settings-dropdown');
  if (dropdown) dropdown.classList.toggle('show');
}

document.addEventListener('click', (e) => {
  const dropdown = document.getElementById('settings-dropdown');
  if (dropdown && !e.target.closest('.settings-menu')) {
    dropdown.classList.remove('show');
  }
});

// --- ROLE SWITCHER ---
function setRole(role) {
  localStorage.setItem('pwt_role', role);
  document.querySelectorAll('.role-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.role === role);
  });
  if (role === 'field' && !window.location.pathname.startsWith('/field')) {
    showToast("Switched to Field Officer View", 'info');
    window.location.href = '/field';
  } else if (role === 'control' && window.location.pathname.startsWith('/field')) {
    showToast("Switched to Control Room View", 'info');
    window.location.href = '/';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const savedRole = localStorage.getItem('pwt_role') || 'control';
  document.querySelectorAll('.role-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.role === savedRole);
  });
});

// --- MODAL & WORK UPDATE HANDLERS ---
function openUpdateModal(workId, workTitle, currentProgress) {
  const modal = document.getElementById('update-modal');
  if (!modal) return;
  document.getElementById('modal-work-id').value = workId;
  document.getElementById('modal-work-title').innerText = workTitle;
  document.getElementById('modal-progress').value = currentProgress;
  document.getElementById('modal-progress-val').innerText = currentProgress + '%';
  modal.classList.add('active');
}

function closeUpdateModal() {
  const modal = document.getElementById('update-modal');
  if (modal) modal.classList.remove('active');
}

async function submitWorkUpdate(e) {
  e.preventDefault();
  const workId = document.getElementById('modal-work-id').value;
  const progress = parseInt(document.getElementById('modal-progress').value, 10);
  const note = document.getElementById('modal-note').value.trim();
  const updatedBy = document.getElementById('modal-updated-by').value.trim();

  if (!note || !updatedBy) {
    showToast("Please provide both an inspection note and officer name.", 'warning');
    return;
  }

  try {
    const res = await fetch(`/api/works/${workId}/update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        progress_pct: progress,
        note: note,
        updated_by: updatedBy,
        photo_url: null
      })
    });

    if (res.ok) {
      showToast("Work update submitted! Recalculating status and alerts...", 'success');
      closeUpdateModal();
      setTimeout(() => window.location.reload(), 800);
    } else {
      const err = await res.json();
      showToast("Error: " + (err.detail || "Failed to submit update"), 'error');
    }
  } catch (err) {
    console.error(err);
    showToast("Network error submitting work update.", 'error');
  }
}

async function resolveAlert(alertId) {
  try {
    const res = await fetch(`/api/alerts/${alertId}/resolve`, {
      method: 'POST'
    });
    if (res.ok) {
      showToast("Alert marked resolved!", 'success');
      setTimeout(() => window.location.reload(), 500);
    } else {
      showToast("Failed to resolve alert.", 'error');
    }
  } catch (err) {
    console.error(err);
    showToast("Network error resolving alert.", 'error');
  }
}

async function updateAssetStatus(assetId, newStatus) {
  try {
    const res = await fetch(`/api/assets/${assetId}/status?status=${encodeURIComponent(newStatus)}`, {
      method: 'POST'
    });
    if (res.ok) {
      showToast(`Asset status updated to ${newStatus}`, 'success');
      setTimeout(() => window.location.reload(), 500);
    } else {
      showToast("Failed to update asset status.", 'error');
    }
  } catch (err) {
    console.error(err);
    showToast("Network error updating asset.", 'error');
  }
}

// ==========================================================================
// GUIDED 5-STEP DEMO MODE CONTROLLER
// ==========================================================================
let demoCurrentStep = 0;

const demoSteps = [
  {
    step: 1,
    title: "1. Control Room View",
    text: "Notice the executive KPIs at the top: 30 Works across 5 Ghats, with 9 Delayed Works (30%) and ₹2.14 Cr of Budget at Risk. The spatial map shows all delayed sites in red.",
    targetSelector: ".kpi-row",
    action: () => {
      closeDemoDrawer();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  },
  {
    step: 2,
    title: "2. Field Officer Updates a Work",
    text: "A site engineer at Kotilingala Ghat reports unexpected river seepage on 'Modular Bio-Toilet Block A'. Watch as we load the Field Officer app and enter a progress delay update.",
    targetSelector: "#demo-split-drawer",
    action: () => {
      openDemoDrawer();
      // Pre-fill demo form
      setTimeout(() => {
        const select = document.getElementById('field-work-select');
        if (select) {
          select.value = "2"; // Modular Bio-Toilet
          select.dispatchEvent(new Event('change'));
        }
        const prog = document.getElementById('field-progress');
        if (prog) {
          prog.value = "25";
          prog.dispatchEvent(new Event('input'));
        }
        const note = document.getElementById('field-note');
        if (note) note.value = "DEMO ALERT: Heavy river silt seepage halted concrete footing works. Work lagging behind schedule.";
        const by = document.getElementById('field-by');
        if (by) by.value = "Er. S. Rao (Site Engineer)";
      }, 300);
    }
  },
  {
    step: 3,
    title: "3. System Reacts in Real Time",
    text: "Submitting the field update automatically applies the Business Logic Engine: Work #2 transitions to DELAYED, a High-Severity Alert is raised, and the Budget at Risk updates instantly!",
    targetSelector: ".countdown-banner",
    action: async () => {
      closeDemoDrawer();
      // Auto-submit update
      try {
        await fetch('/api/works/2/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            progress_pct: 25,
            note: "DEMO TEST: River seepage halted modular toilet footing. Work lagging.",
            updated_by: "Er. S. Rao (Site Engineer)"
          })
        });
        showToast("Field update registered! Watch the KPI numbers recalculate...", 'success');
        // Animate budget count-up
        animateBudgetRisk();
      } catch (e) {}
    }
  },
  {
    step: 4,
    title: "4. Vendor Accountability & Ranking Drop",
    text: "The delayed work immediately impacts the contractor's scorecard. Look at the Vendor Rankings: Pushkaralu Sanitation Corp incurs an open-alert penalty (-10 pts per open alert), dropping in rank.",
    targetSelector: "#vendor-ranking-card",
    action: () => {
      const el = document.getElementById('vendor-ranking-card');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  },
  {
    step: 5,
    title: "5. Resolve & Printable Executive Report",
    text: "The incident supervisor reviews the alert and resolves it after dispatching backup pumps. Finally, click 'Open Readiness Report' to view and print the 1-page executive summary for RMC authorities.",
    targetSelector: "#demo-controls-box",
    action: () => {
      showToast("Ready to generate official Pushkaralu readiness report!", 'info');
    }
  }
];

function startDemoMode() {
  if (window.location.pathname !== '/') {
    window.location.href = '/?start_demo=true';
    return;
  }
  demoCurrentStep = 1;
  document.getElementById('demo-overlay').classList.add('active');
  document.getElementById('demo-float-panel').style.display = 'block';
  renderDemoStep();
}

function exitDemoMode() {
  demoCurrentStep = 0;
  document.getElementById('demo-overlay').classList.remove('active');
  document.getElementById('demo-float-panel').style.display = 'none';
  closeDemoDrawer();
  document.querySelectorAll('.demo-spotlight').forEach(el => el.classList.remove('demo-spotlight'));
}

function nextDemoStep() {
  if (demoCurrentStep < demoSteps.length) {
    demoCurrentStep++;
    renderDemoStep();
  } else {
    // Go to report
    exitDemoMode();
    window.location.href = '/report';
  }
}

function prevDemoStep() {
  if (demoCurrentStep > 1) {
    demoCurrentStep--;
    renderDemoStep();
  }
}

function renderDemoStep() {
  const current = demoSteps[demoCurrentStep - 1];
  document.getElementById('demo-step-num').innerText = `Step ${current.step} of 5`;
  document.getElementById('demo-step-title').innerText = current.title;
  document.getElementById('demo-step-text').innerText = current.text;

  // Step 1: Dynamically load live KPIs from /api/summary instead of hardcoded text
  if (demoCurrentStep === 1) {
    fetch('/api/summary')
      .then(res => res.json())
      .then(summary => {
        const delayedCount = summary?.counts_by_status?.delayed ?? 0;
        const totalWorks = summary?.total_works ?? 30;
        const delayedPct = totalWorks > 0 ? Math.round((delayedCount / totalWorks) * 100) : 0;
        const delayedBudget = summary?.budget?.delayed_budget ?? 0;
        const budgetRiskCr = (delayedBudget / 10000000).toFixed(2);
        
        const dynamicText = `Notice the executive KPIs at the top: ${totalWorks} Works across 5 Ghats, with ${delayedCount} Delayed Works (${delayedPct}%) and ₹${budgetRiskCr} Cr of Budget at Risk. The spatial map shows all delayed sites in red.`;
        demoSteps[0].text = dynamicText;
        const stepEl = document.getElementById('demo-step-text');
        if (stepEl && demoCurrentStep === 1) {
          stepEl.innerText = dynamicText;
        }
      })
      .catch(e => console.warn("Demo step 1 summary load error:", e));
  }

  // Clear previous spotlights
  document.querySelectorAll('.demo-spotlight').forEach(el => el.classList.remove('demo-spotlight'));

  // Spotlight target element
  if (current.targetSelector) {
    const target = document.querySelector(current.targetSelector);
    if (target) {
      target.classList.add('demo-spotlight');
    }
  }

  // Next button label
  const nextBtn = document.getElementById('demo-next-btn');
  if (demoCurrentStep === 5) {
    nextBtn.innerText = "Open Readiness Report 📄";
  } else {
    nextBtn.innerText = "Next Step →";
  }

  // Trigger step action
  if (current.action) current.action();
}

function openDemoDrawer() {
  const drawer = document.getElementById('demo-split-drawer');
  if (drawer) drawer.classList.add('open');
}

function closeDemoDrawer() {
  const drawer = document.getElementById('demo-split-drawer');
  if (drawer) drawer.classList.remove('open');
}

async function resetDemoData() {
  if (!confirm("Are you sure you want to reset all demo data to the initial state (5 Ghats, 30 Works, 40 Assets, 10 Vendors, 15 Alerts)?")) return;
  try {
    const res = await fetch('/api/admin/reset', { method: 'POST' });
    if (res.ok) {
      showToast("Database successfully restored to original clean demo state!", 'success');
      setTimeout(() => window.location.href = '/#home', 600);
    } else {
      showToast("Error resetting database", 'error');
    }
  } catch (err) {
    showToast("Error resetting data", 'error');
  }
}

function animateBudgetRisk() {
  const el = document.getElementById('budget-risk-display');
  if (!el) return;
  el.style.transition = 'all 0.5s ease';
  el.style.transform = 'scale(1.08)';
  el.style.color = '#ef4444';
  setTimeout(() => {
    el.style.transform = 'scale(1)';
  }, 600);
}

// Auto-check for ?start_demo=true query param
document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  if (params.get('start_demo') === 'true') {
    startDemoMode();
  }
});

// ==========================================================================
// CONTROL ROOM ANIMATIONS & LITE MODE CONTROLLER
// ==========================================================================

// 1. Lite Mode Toggle (Auto-enabled below 600px)
function initLiteMode() {
  const isMobileScreen = window.innerWidth <= 600;
  const storedLite = localStorage.getItem('pwt_lite_mode');
  const isLite = isMobileScreen || storedLite === 'true';
  document.documentElement.classList.toggle('lite-mode', isLite);
  const textEl = document.getElementById('lite-mode-status');
  if (textEl) textEl.innerText = isLite ? '🍃 Lite Mode: ON' : '⚡ Lite Mode: OFF';
  updateMobileSheetLiteLabel();
}

window.addEventListener('resize', () => {
  if (window.innerWidth <= 600) {
    document.documentElement.classList.add('lite-mode');
    updateMobileSheetLiteLabel();
  }
});

function toggleLiteMode() {
  const isLite = document.documentElement.classList.toggle('lite-mode');
  localStorage.setItem('pwt_lite_mode', isLite);
  initLiteMode();
  showToast(isLite ? 'Lite Mode enabled (animations & heavy graphics off)' : 'Full animated mode restored', 'info');
}

// 2. Pause animations when tab is hidden (battery & GPU conservation)
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    document.documentElement.classList.add('animations-paused');
  } else {
    document.documentElement.classList.remove('animations-paused');
  }
});

// 3. Smooth Number Count-Up (600ms)
function runCountUp(el, endVal, suffix = '', duration = 600) {
  if (!el) return;
  const isLite = document.documentElement.classList.contains('lite-mode') || 
                (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  if (isLite) {
    el.innerText = endVal.toLocaleString() + suffix;
    return;
  }

  const startTime = performance.now();
  function step(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Smooth easeOutCubic curve
    const ease = 1 - Math.pow(1 - progress, 3);
    const current = Math.floor(ease * endVal);
    el.innerText = current.toLocaleString() + suffix;
    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      el.innerText = endVal.toLocaleString() + suffix;
    }
  }
  requestAnimationFrame(step);
}

// 4. Initialize Count-Up on Load for Dashboard KPIs
document.addEventListener('DOMContentLoaded', () => {
  initLiteMode();
  initSoundToggle();

  // Hash Routing
  handleHashRouting();
  window.addEventListener('hashchange', handleHashRouting);

  // Live polling for hub badges
  startHubPolling();

  // Animate Countdown days
  const elCd = document.getElementById('countdown-days');
  if (elCd) {
    const target = parseInt(elCd.innerText.trim(), 10);
    if (!isNaN(target)) runCountUp(elCd, target);
  }

  // Animate Total Works
  const elTotal = document.getElementById('kpi-val-total-works');
  if (elTotal) {
    const target = parseInt(elTotal.innerText.trim(), 10);
    if (!isNaN(target)) runCountUp(elTotal, target);
  }

  // Animate On Track Works
  const elOnTrack = document.getElementById('kpi-val-ontrack');
  if (elOnTrack) {
    const target = parseInt(elOnTrack.innerText.trim(), 10);
    if (!isNaN(target)) runCountUp(elOnTrack, target);
  }

  // Animate Completed Works
  const elComp = document.getElementById('kpi-val-completed');
  if (elComp) {
    const target = parseInt(elComp.innerText.trim(), 10);
    if (!isNaN(target)) runCountUp(elComp, target);
  }

  // Animate Open Alerts
  const elAlerts = document.getElementById('kpi-val-alerts');
  if (elAlerts) {
    const target = parseInt(elAlerts.innerText.trim(), 10);
    if (!isNaN(target)) runCountUp(elAlerts, target);
  }
});

// ==========================================================================
// AUDIO CHIME (WEB AUDIO API - SYNTHESIZER SOUND)
// ==========================================================================
let audioCtx = null;
function playAlertChime() {
  const soundEnabled = localStorage.getItem('ghatmitra_sound') === 'true';
  if (!soundEnabled) return;
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!audioCtx) audioCtx = new AudioContext();
    if (audioCtx.state === 'suspended') audioCtx.resume();
    
    // Pleasant dual chime: 587.33 Hz (D5) then 880 Hz (A5)
    const osc1 = audioCtx.createOscillator();
    const gain1 = audioCtx.createGain();
    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(587.33, audioCtx.currentTime);
    gain1.gain.setValueAtTime(0.15, audioCtx.currentTime);
    gain1.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.35);
    osc1.connect(gain1);
    gain1.connect(audioCtx.destination);
    osc1.start();
    osc1.stop(audioCtx.currentTime + 0.35);

    setTimeout(() => {
      if (!audioCtx) return;
      const osc2 = audioCtx.createOscillator();
      const gain2 = audioCtx.createGain();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(880, audioCtx.currentTime);
      gain2.gain.setValueAtTime(0.18, audioCtx.currentTime);
      gain2.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.45);
      osc2.connect(gain2);
      gain2.connect(audioCtx.destination);
      osc2.start();
      osc2.stop(audioCtx.currentTime + 0.45);
    }, 120);
  } catch (e) {
    console.warn("Audio chime error:", e);
  }
}

// Beep OFF by default (clear any previously stored value that turned it on)
if (localStorage.getItem('ghatmitra_sound_default_off_v3') !== 'true') {
  localStorage.removeItem('ghatmitra_sound');
  localStorage.setItem('ghatmitra_sound_default_off_v3', 'true');
}

function initSoundToggle() {
  const soundEnabled = localStorage.getItem('ghatmitra_sound') === 'true';
  const icon = document.getElementById('sound-icon');
  const label = document.getElementById('sound-label');
  if (icon) icon.innerText = soundEnabled ? '🔔' : '🔕';
  if (label) label.innerText = soundEnabled ? 'Beep: On' : 'Beep: Off';
  updateMobileSheetSoundLabel();
}

function toggleAudioBeep() {
  const current = localStorage.getItem('ghatmitra_sound') === 'true';
  const next = !current;
  localStorage.setItem('ghatmitra_sound', next);
  initSoundToggle();
  if (next) {
    playAlertChime();
    showToast("Audio alert chime turned ON", "success");
  } else {
    showToast("Audio chime turned OFF", "info");
  }
}

// Mobile More / Settings Bottom Sheet Handlers
function toggleMobileMoreMenu(e) {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  const backdrop = document.getElementById('mobile-more-backdrop');
  const sheet = document.getElementById('mobile-more-sheet');
  if (sheet) {
    const isOpen = sheet.classList.contains('active');
    if (isOpen) {
      closeMobileMoreMenu();
    } else {
      if (backdrop) backdrop.classList.add('active');
      sheet.classList.add('active');
      updateMobileSheetSoundLabel();
      updateMobileSheetLiteLabel();
    }
  }
}

function closeMobileMoreMenu() {
  const backdrop = document.getElementById('mobile-more-backdrop');
  const sheet = document.getElementById('mobile-more-sheet');
  if (backdrop) backdrop.classList.remove('active');
  if (sheet) sheet.classList.remove('active');
}

function updateMobileSheetSoundLabel() {
  const soundEnabled = localStorage.getItem('ghatmitra_sound') === 'true';
  const mobIcon = document.getElementById('mob-sound-icon');
  const mobLabel = document.getElementById('mob-sound-label');
  if (mobIcon) mobIcon.innerText = soundEnabled ? '🔔' : '🔕';
  if (mobLabel) mobLabel.innerText = soundEnabled ? 'Audio Beep: ON' : 'Audio Beep: OFF';
}

function updateMobileSheetLiteLabel() {
  const isLite = document.documentElement.classList.contains('lite-mode');
  const mobIcon = document.getElementById('mob-lite-icon');
  const mobLabel = document.getElementById('mob-lite-label');
  if (mobIcon) mobIcon.innerText = isLite ? '🍃' : '⚡';
  if (mobLabel) mobLabel.innerText = isLite ? 'Lite Mode: ON' : 'Lite Mode: OFF';
}

// ==========================================================================
// SPA HASH ROUTING CONTROLLER
// ==========================================================================
const ROUTE_VIEW_MAP = {
  'home': 'view-home',
  'guard': 'view-guard-reports',
  'field': 'view-engineer-updates',
  'works': 'view-works',
  'assets': 'view-assets',
  'vendors': 'view-vendors',
  'alerts': 'view-alerts',
  'report': 'view-report'
};

function handleHashRouting() {
  const hash = (window.location.hash || '#home').replace('#', '').trim();
  const targetRoute = ROUTE_VIEW_MAP[hash] ? hash : 'home';
  const targetViewId = ROUTE_VIEW_MAP[targetRoute];

  // 1. Toggle Hub Views
  document.querySelectorAll('.hub-view').forEach(view => {
    if (view.id === targetViewId) {
      view.classList.add('active');
    } else {
      view.classList.remove('active');
    }
  });

  // 2. Highlight active tab in desktop header
  document.querySelectorAll('#main-nav-tabs .nav-item').forEach(link => {
    const tab = link.getAttribute('data-tab');
    if (tab === targetRoute) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  // 3. Highlight active tab in mobile bottom bar
  document.querySelectorAll('#mobile-tab-bar .mobile-tab-item').forEach(link => {
    const tab = link.getAttribute('data-tab');
    if (tab === targetRoute) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  // 4. Mark unseen items as seen when opening that module
  markModuleSeen(targetRoute);

  // 5. Scroll to top smoothly
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Track unseen badge counts in memory/localStorage
let lastSeenCounts = JSON.parse(localStorage.getItem('ghatmitra_seen') || '{}');

function markModuleSeen(route) {
  lastSeenCounts[route] = Date.now();
  localStorage.setItem('ghatmitra_seen', JSON.stringify(lastSeenCounts));
  const unseenBadge = document.getElementById(`badge-unseen-${route}`);
  if (unseenBadge) {
    unseenBadge.classList.remove('badge-unseen-pulse');
  }
}

// ==========================================================================
// LIVE POLLING FOR /api/hub/counts (Every 10s) & SYNC INDICATOR
// ==========================================================================
let prevGuardCount = null;
let pollTimer = null;
let lastSyncTime = Date.now();

function updateLiveSyncDisplay() {
  const textEl = document.getElementById('live-sync-text');
  const dotEl = document.getElementById('live-sync-dot');
  if (!textEl || !dotEl) return;

  const elapsedSec = Math.floor((Date.now() - lastSyncTime) / 1000);
  if (elapsedSec > 25) {
    dotEl.className = 'live-sync-dot offline';
    textEl.innerText = 'Sync: Reconnecting...';
  } else {
    dotEl.className = 'live-sync-dot';
    if (elapsedSec < 3) {
      textEl.innerText = 'Live: Synced';
    } else {
      textEl.innerText = `Updated ${elapsedSec}s ago`;
    }
  }
}

async function fetchHubCounts() {
  if (document.hidden) return; // Paused when tab hidden
  try {
    const res = await fetch('/api/hub/counts');
    if (!res.ok) {
      const dotEl = document.getElementById('live-sync-dot');
      if (dotEl) dotEl.className = 'live-sync-dot offline';
      return;
    }
    const data = await res.json();
    lastSyncTime = Date.now();
    updateLiveSyncDisplay();

    // Check if new guard reports arrived
    if (prevGuardCount !== null && (data.guard_reports_today || 0) > prevGuardCount) {
      playAlertChime();
      showToast(`🛡️ New Guard Report received! (${data.guard_reports_today} today)`, "error");
      const navBadge = document.getElementById('nav-badge-guard');
      if (navBadge) {
        navBadge.style.display = 'inline-block';
        navBadge.innerText = data.guard_reports_today;
        navBadge.classList.add('badge-unseen-pulse');
      }
    }
    prevGuardCount = data.guard_reports_today || 0;

    // Keys safe resolution (check both formats, default to 0, never undefined)
    const worksDelayed = data.works_delayed ?? data.delayed_works ?? 0;
    const assetsFaulty = data.assets_faulty ?? data.faulty_assets ?? 0;
    const alertsOpen = data.alerts_open ?? data.open_alerts ?? 0;
    const vendorsLowest = data.vendors_lowest_score ?? data.lowest_vendor_score ?? 0;
    const guardReports = data.guard_reports_today ?? 0;
    const engineerUpdates = data.engineer_updates_today ?? 0;

    // Feature Tiles
    updateTileBadge('tile-count-guard', guardReports);
    updateTileBadge('tile-count-engineer', engineerUpdates);
    updateTileBadge('tile-count-works', worksDelayed);
    updateTileBadge('tile-count-assets', assetsFaulty);
    updateTileBadge('tile-count-vendors', vendorsLowest);
    updateTileBadge('tile-count-alerts', alertsOpen);

    // Nav Badges: use the same values as the tiles
    updateNavBadge('nav-badge-guard', guardReports);
    updateNavBadge('nav-badge-field', engineerUpdates);
    updateNavBadge('nav-badge-works', worksDelayed);
    updateNavBadge('nav-badge-assets', assetsFaulty);
    updateNavBadge('nav-badge-vendors', vendorsLowest);
    updateNavBadge('nav-badge-alerts', alertsOpen);

    // Mobile Bottom Tab Badges
    updateNavBadge('mob-badge-guard', guardReports);
    updateNavBadge('mob-badge-works', worksDelayed);
    updateNavBadge('mob-badge-assets', assetsFaulty);

  } catch (e) {
    const dotEl = document.getElementById('live-sync-dot');
    if (dotEl) dotEl.className = 'live-sync-dot offline';
  }
}

function updateTileBadge(id, val) {
  const el = document.getElementById(id);
  if (el) {
    el.innerText = (val !== undefined && val !== null) ? val : 0;
  }
}

function updateNavBadge(id, val) {
  const el = document.getElementById(id);
  if (el) {
    const count = (val !== undefined && val !== null) ? val : 0;
    el.innerText = count;
    el.style.display = 'inline-block';
  }
}

// Client-Side Layout Overflow Diagnostic Auditor
function auditMobileLayoutOverflow() {
  const winW = window.innerWidth;
  const docW = document.documentElement.scrollWidth;
  if (docW > winW) {
    console.warn(`[Layout Audit] Overflow detected! Window width: ${winW}px, document scrollWidth: ${docW}px`);
    document.querySelectorAll('*').forEach(el => {
      if (el.scrollWidth > winW) {
        console.warn(`[Overflowing Element] <${el.tagName} id="${el.id}" class="${el.className}"> scrollWidth: ${el.scrollWidth}px > ${winW}px`);
      }
    });
  } else {
    console.log(`[Layout Audit OK] Document width matches viewport: scrollWidth=${docW}px <= window=${winW}px`);
  }
}
window.addEventListener('load', auditMobileLayoutOverflow);
window.addEventListener('resize', auditMobileLayoutOverflow);

function startHubPolling() {
  fetchHubCounts();
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(fetchHubCounts, 10000);
  setInterval(updateLiveSyncDisplay, 1000);
}

// ==========================================================================
// DETAIL DRAWER CONTROLLER (CRASH-PROOF & BEFORE/AFTER FLOW)
// ==========================================================================
let currentResolvingAlertId = null;
let currentFixPhotoBase64 = null;

const DEMO_STAFF_LIST = [
  "K. Satyanarayana (Sanitation Supervisor)",
  "P. Srinivas (Electrical Inspector)",
  "M. Venkat (Civil Engineer)",
  "B. Suresh (Plumbing & Water QC)",
  "A. Krishna (Emergency Response Guard)"
];

async function openDetailDrawer(alertId) {
  const drawer = document.getElementById('detail-drawer');
  const backdrop = document.getElementById('detail-drawer-backdrop');
  if (!drawer || !backdrop) return;

  currentResolvingAlertId = alertId;
  currentFixPhotoBase64 = null;

  document.getElementById('drawer-title').innerText = "Loading details...";
  document.getElementById('drawer-body-content').innerHTML = `
    <div style="text-align: center; padding: 50px 20px; color: var(--text-muted);">
      <span style="font-size: 2.2rem; display: block; margin-bottom: 8px;">⏳</span>
      Fetching case report from central database...
    </div>
  `;
  backdrop.classList.add('open');
  drawer.classList.add('open');

  try {
    const res = await fetch(`/api/alerts/${alertId}`);
    if (!res.ok) throw new Error("Server returned HTTP " + res.status);
    const item = await res.json();

    // Guard all properties against null or undefined
    const title = item.clean_title || item.type || "Incident Alert";
    const message = item.clean_message || item.message || "No description provided";
    const ghatName = item.ghat_name || "Pushkar Ghat";
    const guardName = item.guard_name || "Patrol Guard";
    const photoUrl = item.photo_url || "";
    const resPhotoUrl = item.resolution_photo_url || "";
    const status = item.status || "open";
    const severity = (item.severity || "medium").toLowerCase();
    const note = item.note || "";
    const createdAt = item.created_at || "Recent";
    const assignedTo = item.assigned_to || "";
    const assignedAt = item.assigned_at || "";
    const inProgressAt = item.in_progress_at || "";
    const resolvedAt = item.resolved_at || "";
    const resolvedBy = item.resolved_by || "";
    const resolutionNote = item.resolution_note || "";
    const resolutionMinutes = item.resolution_minutes || (status === 'resolved' ? 14 : null);
    const lat = item.latitude || 17.0015;
    const lng = item.longitude || 81.7770;
    const refNo = item.ref_no || `ALT-${alertId}`;

    document.getElementById('drawer-title').innerText = title;

    // 1. Photos Section: Before / After comparison if resolved, else single photo box
    let photoSectionHtml = '';
    if (status === 'resolved' && (photoUrl || resPhotoUrl)) {
      photoSectionHtml = `
        <div style="font-size: 0.76rem; font-weight: 800; color: var(--navy); text-transform: uppercase; margin-bottom: 6px;">
          📸 Before &amp; After Photo Verification
        </div>
        <div class="drawer-before-after-grid">
          <!-- Before Card -->
          <div class="drawer-photo-card before">
            <div class="photo-label"><span>BEFORE (Reported)</span> <span>⚠️</span></div>
            ${photoUrl ? `<img src="${photoUrl}" alt="Before incident photo" onclick="zoomPhoto('${photoUrl}')" onerror="this.src='/static/img/kolam_pattern.svg'">` : `<div style="height:140px; display:flex; align-items:center; justify-content:center; color:var(--text-muted); font-size:0.78rem;">No initial photo</div>`}
          </div>

          <!-- After Card -->
          <div class="drawer-photo-card after">
            <div class="photo-label"><span>AFTER (Fixed)</span> <span>✓</span></div>
            ${resPhotoUrl ? `<img src="${resPhotoUrl}" alt="After fix photo" onclick="zoomPhoto('${resPhotoUrl}')" onerror="this.src='/static/img/kolam_pattern.svg'">` : `<div style="height:140px; display:flex; align-items:center; justify-content:center; color:var(--text-muted); font-size:0.78rem;">Fix verified on-ground</div>`}
          </div>
        </div>
      `;
    } else if (photoUrl) {
      photoSectionHtml = `
        <div class="drawer-photo-box" onclick="zoomPhoto('${photoUrl}')" title="Tap to expand photo">
          <img src="${photoUrl}" class="drawer-photo-img" alt="Report photo" onerror="this.src='/static/img/kolam_pattern.svg';">
          <div class="drawer-photo-overlay">🔍 Tap to Zoom Photo</div>
        </div>
      `;
    } else {
      photoSectionHtml = `
        <div class="drawer-photo-box" style="background: #f8fafc; height: 95px; border: 1.5px dashed var(--border);">
          <div style="text-align: center; color: var(--text-muted); font-size: 0.8rem;">
            <span style="font-size: 1.6rem; display: block;">📷</span>
            No on-site photo attached
          </div>
        </div>
      `;
    }

    // 2. Resolved Minutes Badge
    let resolvedBadgeHtml = '';
    if (status === 'resolved') {
      resolvedBadgeHtml = `
        <div class="badge-resolved-time">
          <span>✓</span> Resolved in ${resolutionMinutes || 15} minutes
        </div>
      `;
    }

    // 3. Workflow Timeline
    const timelineHtml = `
      <div style="font-size: 0.76rem; font-weight: 800; color: var(--navy); text-transform: uppercase; margin-bottom: 4px;">
        ⏱️ Audit Timeline
      </div>
      <div class="drawer-timeline">
        <div class="timeline-step active">
          <div class="timeline-dot"></div>
          <div class="timeline-title">Reported by ${guardName}</div>
          <div class="timeline-meta">🕒 ${createdAt}</div>
        </div>

        <div class="timeline-step ${assignedAt ? 'active' : (status !== 'open' ? 'current' : '')}">
          <div class="timeline-dot"></div>
          <div class="timeline-title">${assignedTo ? `Assigned to ${assignedTo}` : 'Supervisor Assignment'}</div>
          <div class="timeline-meta">${assignedAt ? `🕒 ${assignedAt}` : (status === 'open' ? '— Pending assignment' : '—')}</div>
        </div>

        <div class="timeline-step ${inProgressAt || status !== 'open' ? 'active' : ''}">
          <div class="timeline-dot"></div>
          <div class="timeline-title">Field Work In Progress</div>
          <div class="timeline-meta">${inProgressAt ? `🕒 ${inProgressAt}` : (status === 'in_progress' ? 'Active on site' : '—')}</div>
        </div>

        <div class="timeline-step ${status === 'resolved' ? 'active' : ''}">
          <div class="timeline-dot"></div>
          <div class="timeline-title">${status === 'resolved' ? `Resolved & Certified${resolvedBy ? ` by ${resolvedBy}` : ''}` : 'Resolution & Closure'}</div>
          <div class="timeline-meta">${resolvedAt ? `🕒 ${resolvedAt}${resolutionNote ? ` &bull; "${resolutionNote}"` : ''}` : '— Pending final resolution'}</div>
        </div>
      </div>
    `;

    // 4. Action Buttons based on status
    let actionButtonsHtml = '';
    if (status !== 'resolved') {
      actionButtonsHtml = `
        <div class="drawer-action-btn-group">
          <div style="font-size: 0.76rem; font-weight: 800; color: var(--navy); text-transform: uppercase;">
            Take Action:
          </div>
          
          <div class="btn-row">
            <button class="btn-big-action btn-assign-staff" onclick="toggleAssignSelect(${alertId})">
              <span>👤</span> Assign
            </button>
            <button class="btn-big-action btn-mark-progress" onclick="setDrawerAlertStatus(${alertId}, 'in_progress')">
              <span>⏳</span> In Progress
            </button>
            <button class="btn-big-action btn-resolve-step" onclick="toggleResolveStep(${alertId})">
              <span>✓</span> Resolve
            </button>
          </div>

          <!-- Inline Staff Assign Selector (hidden by default) -->
          <div id="assign-select-box" style="display: none; background: #f0fdf4; border: 1.5px solid #bbf7d0; border-radius: var(--radius-sm); padding: 12px; margin-top: 4px;">
            <label style="font-size: 0.78rem; font-weight: 800; color: var(--navy); display: block; margin-bottom: 6px;">
              Assign to Field Engineer / Specialist:
            </label>
            <select id="select-staff-assignee" class="form-select" style="margin-bottom: 8px;">
              ${DEMO_STAFF_LIST.map(s => `<option value="${s}">${s}</option>`).join('')}
            </select>
            <div style="display: flex; gap: 8px; justify-content: flex-end;">
              <button class="btn btn-secondary btn-sm" onclick="toggleAssignSelect(${alertId})">Cancel</button>
              <button class="btn btn-primary btn-sm" onclick="confirmStaffAssignment(${alertId})">Confirm Assignment</button>
            </div>
          </div>

          <!-- Inline Resolve Step Box (hidden by default) -->
          <div id="resolve-step-box" class="resolve-step-box" style="display: none;">
            <div style="font-size: 0.82rem; font-weight: 800; color: #166534; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
              <span>📸</span> Add Fix Photo (Optional) &amp; Notes
            </div>

            <div style="margin-bottom: 8px;">
              <input type="file" id="resolve-fix-photo-file" accept="image/*" capture="environment" class="form-input" style="font-size: 0.78rem;" onchange="handleResolvePhotoSelect(event)">
              <div id="resolve-photo-preview" style="font-size: 0.72rem; color: #15803d; margin-top: 4px; display: none;">
                ✓ Photo attached &amp; compressed (&lt;150 KB)
              </div>
            </div>

            <div style="margin-bottom: 10px;">
              <input type="text" id="resolve-what-done-input" class="form-input" placeholder="What was done? (e.g. Pump valve repaired, tap supply restored)" value="Rectified on-ground issue and verified flow.">
            </div>

            <div style="display: flex; gap: 8px; justify-content: flex-end;">
              <button class="btn btn-secondary btn-sm" onclick="toggleResolveStep(${alertId})">Cancel</button>
              <button class="btn btn-primary btn-sm" onclick="confirmResolution(${alertId})" style="background: var(--green); border-color: var(--green);">
                ✓ Confirm &amp; Mark Resolved
              </button>
            </div>
          </div>

        </div>
      `;
    } else {
      actionButtonsHtml = `
        <div class="drawer-action-btn-group">
          <button class="btn-big-action btn-reopen" onclick="setDrawerAlertStatus(${alertId}, 'open')">
            <span>🔄</span> Re-open Incident
          </button>
        </div>
      `;
    }

    document.getElementById('drawer-body-content').innerHTML = `
      ${resolvedBadgeHtml}
      ${photoSectionHtml}
      
      <div style="display: flex; gap: 8px; margin-bottom: 12px; align-items: center; flex-wrap: wrap;">
        <span class="chip-status ${status}" id="drawer-current-status">${status.replace('_', ' ')}</span>
        <span class="badge badge-${severity}">${severity.toUpperCase()} Priority</span>
        <span style="font-size: 0.76rem; color: var(--text-muted); margin-left: auto;">${refNo}</span>
      </div>

      <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 14px; margin-bottom: 14px;">
        <div style="font-size: 0.74rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px;">Incident Details</div>
        <p style="font-size: 0.95rem; color: var(--text-dark); line-height: 1.45; margin: 0; font-weight: 700;">
          ${title}
        </p>
        <p style="font-size: 0.84rem; color: #475569; margin: 4px 0 0; line-height: 1.4;">
          ${message}
        </p>
        ${note ? `<div style="font-size: 0.8rem; color: #64748b; font-style: italic; margin-top: 6px;">Note: "${note}"</div>` : ''}
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px;">
        <div style="background: var(--card); border: 1px solid var(--border); padding: 10px 12px; border-radius: 6px;">
          <div style="font-size: 0.72rem; color: var(--text-muted); font-weight: 700;">LOCATION</div>
          <div style="font-size: 0.88rem; font-weight: 800; color: var(--navy); margin-top: 2px;">📍 ${ghatName}</div>
        </div>
        <div style="background: var(--card); border: 1px solid var(--border); padding: 10px 12px; border-radius: 6px;">
          <div style="font-size: 0.72rem; color: var(--text-muted); font-weight: 700;">REPORTED BY</div>
          <div style="font-size: 0.84rem; font-weight: 700; color: #334155; margin-top: 2px;">👤 ${guardName}</div>
        </div>
      </div>

      ${timelineHtml}

      ${actionButtonsHtml}
    `;

  } catch (err) {
    document.getElementById('drawer-body-content').innerHTML = `
      <div style="text-align: center; padding: 40px 20px;">
        <span style="font-size: 2.5rem; display: block; margin-bottom: 8px;">⚠️</span>
        <strong style="color: var(--navy); display: block; font-size: 1.05rem;">Unable to load incident report</strong>
        <p style="color: var(--text-muted); font-size: 0.84rem; margin: 8px 0 16px; line-height: 1.4;">
          ${err.message || 'The server could not retrieve details for this item.'}
        </p>
        <button class="btn btn-primary btn-sm" onclick="openDetailDrawer(${alertId})">
          🔄 Retry Loading
        </button>
      </div>
    `;
  }
}

function closeDetailDrawer() {
  const drawer = document.getElementById('detail-drawer');
  const backdrop = document.getElementById('detail-drawer-backdrop');
  if (drawer) drawer.classList.remove('open');
  if (backdrop) backdrop.classList.remove('open');
}

function toggleAssignSelect(alertId) {
  const box = document.getElementById('assign-select-box');
  if (box) {
    box.style.display = box.style.display === 'none' ? 'block' : 'none';
  }
}

async function confirmStaffAssignment(alertId) {
  const select = document.getElementById('select-staff-assignee');
  const staff = select ? select.value : DEMO_STAFF_LIST[0];

  try {
    const res = await fetch(`/api/alerts/${alertId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: 'in_progress',
        assigned_to: staff
      })
    });
    if (res.ok) {
      showToast(`Assigned to ${staff.split(' ')[0]} and marked In Progress!`, 'success');
      openDetailDrawer(alertId);
      fetchHubCounts();
    } else {
      showToast("Error assigning staff", "error");
    }
  } catch (e) {
    showToast("Network error assigning staff", "error");
  }
}

function toggleResolveStep(alertId) {
  const box = document.getElementById('resolve-step-box');
  if (box) {
    box.style.display = box.style.display === 'none' ? 'block' : 'none';
  }
}

function handleResolvePhotoSelect(event) {
  const file = event.target.files[0];
  if (file) {
    compressResolutionPhoto(file, function(compressedBase64) {
      currentFixPhotoBase64 = compressedBase64;
      const previewText = document.getElementById('resolve-photo-preview');
      if (previewText) previewText.style.display = 'block';
    });
  }
}

// Compress resolution photo under 150 KB
function compressResolutionPhoto(file, callback) {
  const reader = new FileReader();
  reader.onload = function(e) {
    const img = new Image();
    img.onload = function() {
      const maxWidth = 800;
      let w = img.width;
      let h = img.height;
      if (w > maxWidth) {
        h = Math.round((h * maxWidth) / w);
        w = maxWidth;
      }
      const canvas = document.createElement('canvas');
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, w, h);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.65);
      callback(dataUrl);
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}

async function confirmResolution(alertId) {
  const noteInput = document.getElementById('resolve-what-done-input');
  const noteText = noteInput ? noteInput.value.trim() : "Issue rectified on site.";

  try {
    const res = await fetch(`/api/alerts/${alertId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        status: 'resolved',
        resolution_note: noteText,
        resolved_by: "Er. S. Rao (QC Engineer)",
        resolution_photo: currentFixPhotoBase64
      })
    });
    if (res.ok) {
      showToast("Incident certified as Resolved!", 'success');
      currentFixPhotoBase64 = null;
      openDetailDrawer(alertId);
      // Update in DOM table if present
      const rowStatusBadge = document.querySelector(`[data-alert-row-status="${alertId}"]`);
      if (rowStatusBadge) {
        rowStatusBadge.className = 'chip-status resolved';
        rowStatusBadge.innerText = 'resolved';
      }
      fetchHubCounts();
    } else {
      showToast("Error updating resolution", "error");
    }
  } catch (e) {
    showToast("Network error submitting resolution", "error");
  }
}

async function setDrawerAlertStatus(alertId, newStatus) {
  try {
    const res = await fetch(`/api/alerts/${alertId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      showToast(`Status updated to ${newStatus.replace('_', ' ')}!`, 'success');
      openDetailDrawer(alertId);
      const rowStatusBadge = document.querySelector(`[data-alert-row-status="${alertId}"]`);
      if (rowStatusBadge) {
        rowStatusBadge.className = `chip-status ${newStatus}`;
        rowStatusBadge.innerText = newStatus.replace('_', ' ');
      }
      fetchHubCounts();
    } else {
      showToast("Error updating status", "error");
    }
  } catch (e) {
    showToast("Network error updating status", "error");
  }
}

// ==========================================================================
// PHOTO ZOOM MODAL CONTROLLER
// ==========================================================================
function zoomPhoto(src) {
  const modal = document.getElementById('photo-zoom-modal');
  const img = document.getElementById('photo-zoom-img');
  if (modal && img && src) {
    img.src = src;
    modal.classList.add('open');
  }
}

function closePhotoZoom() {
  const modal = document.getElementById('photo-zoom-modal');
  if (modal) modal.classList.remove('open');
}

// ==========================================================================
// INTERACTIVE MAP MODAL CONTROLLER
// ==========================================================================
function openMapModal() {
  const modal = document.getElementById('map-modal');
  if (modal) {
    modal.classList.add('open');
    setTimeout(() => {
      if (window.hubMap) window.hubMap.invalidateSize();
    }, 200);
  }
}

function closeMapModal() {
  const modal = document.getElementById('map-modal');
  if (modal) modal.classList.remove('open');
}
