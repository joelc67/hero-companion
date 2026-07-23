"use strict";

// ---------------------------------------------------------------------------
// Global build state
// ---------------------------------------------------------------------------
const build = {
  archetype: null,
  primary: null, primary_display: null,
  secondary: null, secondary_display: null,
  pools: [], pools_display: [],
  epic: null, epic_display: null,
  incarnates: {},   // slot -> {full_name, display_name}
  include_incarnates: false,  // peak totals: fold incarnate buffs into totals
  // ⚠ v34 RECONCILIATION (Joel spotted this on the panel screenshot, 2026-07-16):
  // this global "Include accolades + amplifiers" toggle and the accolade
  // panel's per-accolade checkmarks describe THE SAME ASSUMPTION and must
  // never become two independent sources of truth about it. Plausible shape:
  // the toggle becomes "apply the CHECKED accolades", or an explicit
  // all-vs-acquired choice. Design it deliberately when the panel's model half
  // lands — do not let them drift. (Today the panel is display-only, so
  // nothing reads it and there is no conflict yet.)
  include_external: false,    // add accolades + amplifiers (external buffs)
  pvp: false,                 // PvP arena: PvP set bonuses + PvP effect variants
  tier: null,       // budget | balanced | premium — the loaded AI build's tier
  imported: false,  // true only for an IMPORTED build — gates the preserve-my-sets
                    // Solve behavior (a from-scratch/AI build has no investment to keep)
  powers: [],   // {full_name, display_name, powerset_full_name,
                //  accepted_set_category_ids, accepted_set_categories,
                //  slotCount, slots:[slot|null]}
};

let POWERSETS_CACHE = null;          // current archetype's powersets
const POWERS_CACHE = {};             // powerset_full_name -> [powers]
let activeSlot = null;               // {powerIdx, slotIdx}
let INCARNATES = null;               // /incarnates payload

const $ = (id) => document.getElementById(id);

// GLOBAL ERROR SURFACE (2026-07-20, the dead-air field report): an unreachable
// or wedged server must NEVER be silent. Root cause of the field incident: the
// tray server on :5000 was down, so every action's fetch failed and the
// null-guards (`.catch(()=>null)` -> `if(!x) return`) bailed with no message —
// three controls dead, zero explanation. Fix at the chokepoint every request
// already flows through: api() shows a visible banner on failure, then RE-THROWS
// so existing caller semantics (null-guards, try/catch "Solve error") are
// unchanged. Purely additive — control flow identical, silence removed.
function showServerError(msg) {
  let el = $("global-error-banner");
  if (!el) {
    el = document.createElement("div");
    el.id = "global-error-banner";
    el.className = "global-error-banner";
    document.body.appendChild(el);
  }
  el.innerHTML =
    '<span class="ge-msg"></span>'
    + '<button class="ge-reload" type="button">Reload</button>'
    + '<button class="ge-dismiss" type="button" aria-label="Dismiss">×</button>';
  el.querySelector(".ge-msg").textContent = msg;
  el.querySelector(".ge-reload").onclick = () => location.reload();
  el.querySelector(".ge-dismiss").onclick = () => { el.style.display = "none"; };
  el.style.display = "flex";
}
function clearServerError() {
  const el = $("global-error-banner");
  if (el) el.style.display = "none";
}
const api = (p, opts) => fetch(p, opts).then(r => {
  if (!r.ok) throw new Error("HTTP " + r.status);
  clearServerError();                     // connectivity recovered
  return r.json();
}).catch(err => {
  const net = (err instanceof TypeError)
    || /Failed to fetch|NetworkError|Load failed/i.test(String(err && err.message));
  showServerError(net
    ? "Can't reach Hero Companion — the app may not be running. "
      + "Start it from the system tray, then click Reload."
    : "Something went wrong talking to the app. Reload; if it keeps happening, "
      + "restart the app.");
  throw err;                              // preserve caller semantics (null-guards, try/catch)
});

// GLOBAL EXCEPTION SURFACE (2026-07-20, dead-air order #2.2): an uncaught JS
// exception must never silently kill the page's interactivity — the worst
// failure mode, and it happened in the field. A window-level handler turns any
// uncaught error / unhandled promise rejection into the same visible banner.
// Network/server-down rejections are already surfaced by api() with a specific
// message, so those are skipped here to avoid clobbering the better wording.
window.addEventListener("error", (e) => {
  if (e && /Script error/i.test(e.message || "")) return;   // cross-origin noise
  showServerError("Something broke on this page. Reload; the details are in "
    + "the browser console (press F12).");
});
window.addEventListener("unhandledrejection", (e) => {
  const r = e && e.reason;
  const net = (r instanceof TypeError)
    || /Failed to fetch|NetworkError|Load failed|HTTP \d/i.test(String(r && r.message));
  if (net) return;                        // api() already showed the network banner
  showServerError("Something went wrong. Reload; if it keeps happening, restart "
    + "the app.");
});

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
const escHtml = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/'/g, "&#39;");

// Collapse + EMPTY the transient build-specific panels (tray layout, respec order) so
// they never carry a previous character's content into a new/restarted/loaded build.
function resetTrayPanels() {
  const t = $("tray-out"), o = $("order-out");
  if (t) { t.classList.add("hidden"); t.innerHTML = ""; }
  if (o) { o.classList.add("hidden"); o.innerHTML = ""; }
}

function showEntry() {
  $("entry-overlay").classList.remove("hidden");
  $("entry-cards").classList.remove("hidden");
  $("saves-panel").classList.add("hidden");
  resetTrayPanels();          // restart → don't show the prior build's trays/order
  refreshContinueCard();
}
function hideEntry() { $("entry-overlay").classList.add("hidden"); }

// ---- Save / resume: a from-scratch character is weeks of real play ----
let CURRENT_SAVE = null;   // {id, name} once saved/loaded, so re-saves update in place

async function saveProgress() {
  if (!build.archetype) { alert("Pick an archetype (or import/start a build) before saving."); return; }
  let name = CURRENT_SAVE && CURRENT_SAVE.name;
  if (!name) {
    const dflt = build.primary_display
      ? `${build.primary_display} ${(build.archetype || "").replace("Class_", "")}` : "My character";
    name = prompt("Name this character (so you can resume it later):", dflt);
    if (!name) return;
  }
  const plan = { content: $("preset-content") && $("preset-content").value,
                 role: $("preset-role") && $("preset-role").value, role_mix: roleMixPayload(), mode: build._mode || null,
                 custom_targets: build._custom_targets || null };   // ruling 4: persist in the save
  const res = await api("/saves", postJson({ name, id: CURRENT_SAVE && CURRENT_SAVE.id,
    build, plan, level_reached: build.level_reached || null }));
  if (res && res.ok) {
    CURRENT_SAVE = { id: res.id, name: res.name };
    _lastSavedSnapshot = buildSnapshot();   // mark clean so auto-save doesn't re-fire
    const s = $("gen-status"); if (s) s.textContent = `💾 Saved “${res.name}”. Resume it any time from Start over → Continue.`;
  }
}

async function openSavesList() {
  const res = await api("/saves");
  const saves = (res && res.saves) || [];
  $("saves-list").innerHTML = saves.length
    ? saves.map((s) => {
        const at = (s.archetype || "").replace("Class_", "");
        const sub = [s.primary, s.secondary].filter(Boolean).join(" / ");
        // A "new"-mode save with a level below 50 is a character still being LEVELED —
        // label it as leveling-in-progress (⏳ L23/50) so it reads differently from a
        // finished level-50 kit (✓ Level-50 build). This is the Continue-screen
        // distinction between "help me get to 50" and "optimize my 50".
        const lv = s.level || null;
        const leveling = s.mode === "new" && (!lv || lv < 50);
        const pill = leveling
          ? `<span class="save-pill leveling">⏳ Leveling · L${lv || 1}/50</span>`
          : `<span class="save-pill done">✓ Level-50 build</span>`;
        return `<div class="save-row"><div class="save-main">`
          + `<div class="save-name">${escHtml(s.name)} ${pill}</div>`
          + `<div class="save-sub">${escHtml(at)}${sub ? " · " + escHtml(sub) : ""}</div></div>`
          + `<button onclick="loadSave('${escHtml(s.id)}')">Resume</button>`
          + `<button class="save-del" title="Delete" onclick="deleteSave('${escHtml(s.id)}')">🗑</button></div>`;
      }).join("")
    : `<div class="saves-empty">No saved characters yet. Start one, then hit 💾 Save in the header.</div>`;
  $("entry-cards").classList.add("hidden");
  $("saves-panel").classList.remove("hidden");
}

window.loadSave = async function (id) {
  const res = await api(`/saves/${encodeURIComponent(id)}`);
  if (!res || !res.ok) { alert((res && res.error) || "Couldn't load that save."); return; }
  // FORWARD-COMPAT guard (dead-air order #2.3): a save from an older version may
  // lack fields this renderer expects. The mapping above defaults them, but if a
  // load still throws, surface an honest note and keep the page ALIVE rather than
  // letting one exception deaden every control.
  try {
    await applyImportedBuild(res.save.build || {});
  } catch (e) {
    console.error("old-save load failed:", e);
    showServerError("This saved character is from an older version and could not "
      + "be fully loaded. Try starting a fresh build, or re-import it from the game.");
    return;
  }
  CURRENT_SAVE = { id, name: res.save.name };
  const _plan = res.save.plan || {};
  build._mode = _plan.mode || build._mode;
  // Restore the saved plan into the visible controls: the content/role
  // dropdowns (a resumed build used to come back with these EMPTY, so the
  // next Solve ran against different targets than the ones that built it)
  // and the custom targets (Joel's ruling 4: Resume reproduces them).
  // Retired generic "Fire Farm" (2026-07-20): the option is gone from the picker,
  // but the backend still accepts the key. Rather than silently remap, blank the
  // dropdown and nudge the user to choose AFK or Active.
  if (_plan.content === "fire_farm" && $("preset-content")) {
    $("preset-content").value = "";
    if ($("farm-retired-note")) $("farm-retired-note").classList.remove("hidden");
  } else {
    if ($("farm-retired-note")) $("farm-retired-note").classList.add("hidden");
    if (_plan.content && $("preset-content")) $("preset-content").value = _plan.content;
  }
  if (_plan.role && $("preset-role")) $("preset-role").value = _plan.role;
  build._custom_targets = _plan.custom_targets || null;
  updateCustomTargetsChip();
  // Restore an in-progress respec worksheet (applyImportedBuild cleared it) so a respec
  // being worked over days picks up exactly where it left off — checkboxes and all.
  restoreWorksheet(res.save.respec_worksheet || null);
  // Version drift: this save predates the current optimizer model — offer the respec
  // even when the structural hint doesn't fire (an old solver's competent slotting
  // passes the under-invest check; the CURRENT solver would still do better).
  // Dismissal is remembered per save per model, so a "no" holds until the optimizer
  // actually learns something new again.
  const vd = res.save.version_drift;
  RESPEC_VERSION_DRIFT = (vd && !localStorage.getItem(
    `respecDriftDismissed:${id}:m${vd.current_model}`)) ? vd : null;
  applyIdentityLock();          // lock archetype/powersets if this is a real (imported/respec'd) character
  _lastSavedSnapshot = buildSnapshot();   // just loaded — already clean
  hideEntry();
  recompute();
  maybeAutoOpenJourney();       // resuming a 1-50 character leads with the road too
};

window.deleteSave = async function (id) {
  if (!confirm("Delete this saved character?")) return;
  await api(`/saves/${encodeURIComponent(id)}`, { method: "DELETE" });
  openSavesList();
};

async function refreshContinueCard() {
  try {
    const res = await api("/saves");
    const n = (res && res.saves && res.saves.length) || 0;
    const card = $("entry-continue");
    if (n > 0) { $("continue-count").textContent = n; card.style.display = ""; }
    else card.style.display = "none";
  } catch (e) { /* offline-safe: just don't show the card */ }
}

// ---- Background auto-save: a from-scratch character is weeks of play, so persist
// progress on an interval — but ONLY when something actually changed (dirty check via
// a snapshot compare), so an idle build never re-writes. ----
let _lastSavedSnapshot = null;
function buildSnapshot() {
  return JSON.stringify({
    a: build.archetype, p: build.primary, s: build.secondary, pl: build.pools, e: build.epic,
    inc: build.incarnates, pw: (build.powers || []).map(pw => [pw.full_name, pw.slots]),
    fl: [build.include_incarnates, build.pvp, build.tier, build.level_reached],
  });
}
async function autoSaveTick() {
  if (!build.archetype || !(build.powers && build.powers.length)) return;  // nothing worth saving yet
  const snap = buildSnapshot();
  if (snap === _lastSavedSnapshot) return;                                  // unchanged → skip
  const name = (CURRENT_SAVE && CURRENT_SAVE.name)
    || (build.primary_display ? `${build.primary_display} ${(build.archetype || "").replace("Class_", "")}` : "Autosave");
  const plan = { content: $("preset-content") && $("preset-content").value,
                 role: $("preset-role") && $("preset-role").value, role_mix: roleMixPayload(), mode: build._mode || null,
                 custom_targets: build._custom_targets || null };   // ruling 4: persist in the save
  const res = await api("/saves", postJson({ name, id: CURRENT_SAVE && CURRENT_SAVE.id,
    build, plan, level_reached: build.level_reached || null }));
  if (res && res.ok) {
    CURRENT_SAVE = { id: res.id, name: res.name };
    _lastSavedSnapshot = snap;
    const ind = $("autosave-ind");
    if (ind) ind.textContent = `auto-saved ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  }
}

// Auto-pick a sensible, legal power selection for the chosen AT + sets, tuned to
// role × exposure × content — the engine piece behind "Respec 50" and "Start new".
async function autoPickPowers() {
  if (!build.archetype || !build.primary || !build.secondary) {
    alert("Pick an archetype, primary, and secondary first."); return;
  }
  // v34 item 5: same class rule — any path that GENERATES a level-50 build
  // assumes the standard accolades and says so.
  await preselectStandardAccolades();
  build._exposure = $("autopick-exposure") && $("autopick-exposure").value;
  const res = await api("/build/autopick", postJson({
    archetype: build.archetype, primary: build.primary, secondary: build.secondary,
    role: $("preset-role") && $("preset-role").value, role_mix: roleMixPayload(),
    content: $("preset-content") && $("preset-content").value,
    exposure: build._exposure,
    travel: $("autopick-travel") && $("autopick-travel").value,
    custom_targets: build._custom_targets || null }));
  if (!res || !res.ok) { alert((res && res.error) || "Auto-pick failed."); return; }
  if (res.custom_note) {
    const out = $("ai-response");
    if (out) { out.classList.remove("muted"); out.innerHTML = renderMarkdown(res.custom_note); }
  }
  build.powers = res.powers;
  build.imported = false;
  await syncPoolsEpicFromPowers(res.powers);   // reflect the chosen pool/epic powers in the dropdowns
  renderPowers();
  recompute();
  const s = $("gen-status");
  if (s) {
    s.textContent = `🪄 Auto-picked ${res.count} powers for your goal. Now hit Solve to optimize the slotting + incarnates.`;
    // Travel heads-up: Super Speed / Super Jump are GROUND travel. They share a pool
    // efficiently (Super Speed + Hasten = one Speed pool), but you can't run into some
    // iTrials (BAF, Lambda) — those need Flight or Teleport, or a P2W jet pack.
    const tv = $("autopick-travel") && $("autopick-travel").value;
    if (tv === "super_speed" || tv === "super_jump") {
      const itrial = $("preset-content") && $("preset-content").value === "itrial";
      const tname = tv === "super_speed" ? "Super Speed" : "Super Jump";
      const tip = document.createElement("p");
      tip.className = "lvl-tip";
      tip.innerHTML = `🚀 <strong>${tname}</strong> is <em>ground</em> travel`
        + (itrial ? ` — and your <strong>iTrial</strong> goal needs vertical access` : ``)
        + `: you can't run into iTrials like <strong>BAF / Lambda</strong>. Carry a P2W `
        + `<strong>jet pack</strong>, or switch travel to <strong>Fly / Teleport</strong> `
        + `(that costs an extra pool — Super Speed shares its pool with Hasten, Fly/Teleport don't).`;
      s.appendChild(tip);
    }
  }
}

function revealBuilder() {
  const b = $("builder");
  if (b) b.scrollIntoView({ behavior: "smooth", block: "start" });
  const at = $("sel-archetype");
  if (at) setTimeout(() => at.focus(), 350);
}
// "Start a new character" — reveal the builder and focus the first choice. The guided
// discovery flow (recommend an AT from role × exposure × content) + the level-by-level
// path layer on here next. `_mode` will branch new-character vs respec behavior.
// STATE-LIFECYCLE RULE (Joel's field report 2026-07-14, third bug in this
// family): `build` is a long-lived mutable global — every flow that means "a
// DIFFERENT character" must reset the build-scoped ephemerals explicitly, or
// they leak into the next build (his repro: a Stalker's front-line exposure
// seeded Melee 45 into a fresh Blaster's targets editor).
function resetBuildScopedState() {
  build._custom_targets = null;
  build._exposure = null;
  build._travel = null;
  roleFocus = { secondary: "", pct: 100 };
  Object.keys(PREVIEW_BOOSTS).forEach(k => delete PREVIEW_BOOSTS[k]);
  // Accolade ticks are PER-CHARACTER, and this Set is module-level — so before
  // this line it leaked across characters: tick/untick on one, start another,
  // and it inherited the last one's accolade state. Same stale-state family as
  // the custom-targets contamination (a Stalker's Melee-45 seeding a fresh
  // Blaster's editor) — found while root-causing walk-3. A generator re-ticks
  // the standard four straight after, so a NEW level-50 still starts correct.
  ACCOLADES_CHECKED.clear();
  updateCustomTargetsChip();
}

function startFromScratch() {
  resetBuildScopedState();   // a NEW character inherits nothing
  build._mode = "new"; build.level_reached = build.level_reached || 1; openWizard("new");
}
// "Build a new level-50 character" — a SHORT guided wizard that plans a fresh end-game kit
// from scratch (so a 50 isn't dropped on the dense builder cold). Start-new adds a DISCOVERY
// step in front (recommend an AT/sets). This is a PLANNING build for a character that doesn't
// exist in-game yet, so its identity is NOT locked (unlike an imported/respec'd real character)
// — you can freely swap archetype/powersets while planning. level_reached=50 marks it a 50 build.
function startNew50() {
  // Joel's confirmed 0.12.20 eyeball find: this entry card (the ↺ menu's
  // "Build a new level-50 character") NEVER reset — startFromScratch did,
  // this didn't, and openWizard's "new50" branch then re-seeded every old
  // answer as "from your setup". Reset means reset, on EVERY start-over
  // entry point.
  resetBuildScopedState();
  build._mode = "new50"; build.level_reached = 50; openWizard("new50");
}

// Clone a select's options AND its current selection — copying innerHTML alone drops the
// chosen value, which silently reset the wizard's Content/Role to "— choose —" and lost
// the user's pick (it then defaulted to "general").
const cloneOptions = (dst, src) => { if (dst && src) { dst.innerHTML = src.innerHTML; dst.value = src.value; } };

// Provenance of every "How do you play" answer — "" (unanswered) | "setup"
// (carried from your current character/presets — a choice you made earlier) |
// "you" (picked this visit). Joel's design ruling (2026-07-08, supersedes the
// tagged-defaults fix): there are NO defaults — the planner never invents an
// answer to "how do you play"; all four must be answered before building.
let WIZ_SRC = { role: "", content: "", exposure: "", travel: "" };
function wizSetSrc(key, src) {
  WIZ_SRC[key] = src;
  const el = $("wiz-src-" + key);
  if (el) {
    el.textContent = src === "you" ? "your pick" : (src === "setup" ? "from your setup" : "");
    el.className = "wiz-src" + (src ? " wiz-src-" + src : "");
  }
}
const _KHELDIANS = ["Class_Peacebringer", "Class_Warshade"];
const _wizIsKheldian = () => _KHELDIANS.includes($("wiz-at") && $("wiz-at").value);
// Kheldians answer one more question — which FORM they want to live in (each
// answer serves that form's own certified champion). Hidden for everyone else.
function wizFormRow() {
  const row = $("wiz-form-row"), why = $("wiz-form-why");
  if (!row) return;
  // The Form question only exists when form champions actually SHIP in this
  // build (META.form_champions) — a route is never offered to a champion that
  // isn't there. It self-activates in the release that bundles them.
  const kheld = _wizIsKheldian() && !!(META && META.form_champions);
  row.classList.toggle("hidden", !kheld);
  if (why) why.classList.toggle("hidden", !kheld);   // the WHY shows before any answer
  if (!kheld && $("wiz-form")) { $("wiz-form").value = ""; wizSetSrc("form", ""); }
}
const wizAnswered = () => ["wiz-role", "wiz-content", "wiz-exposure", "wiz-travel"]
  .concat(_wizIsKheldian() && META && META.form_champions ? ["wiz-form"] : [])
  .every(id => $(id) && $(id).value);
// Build-my-kit stays disabled until all four questions are answered.
function wizGateBuild() {
  const ok = wizAnswered();
  const btn = $("wiz-build");
  if (btn) {
    btn.disabled = !ok;
    btn.title = ok ? "" : "Answer the four questions above first.";
  }
  if (!ok) $("wiz-status").textContent = "Answer the four “How do you play?” questions first — the planner never chooses for you.";
  else if ($("wiz-status").textContent.startsWith("Answer the four")) $("wiz-status").textContent = "";
}

// FIELD REPORT (Joel's 0.12.22 walk, 2026-07-20): he clicked Build with the
// primary still on its placeholder and got "ten minutes of no build" — the gate
// SET the same gray text that was already sitting there, so every click after
// the first changed nothing visible: a false no-op by repetition. The no-dead-
// controls law demands a RESPONSE: name the missing fields, ring them red,
// scroll the first one into view, and flash the status so a repeat click is
// visibly a fresh answer.
function flagMissing(els, msg, statusEl) {
  els.forEach(el => el && el.classList.add("wiz-missing"));
  const st = statusEl || $("wiz-status");
  st.textContent = msg;
  st.classList.remove("wiz-status-flash");
  void st.offsetWidth;                     // restart the animation on every click
  st.classList.add("wiz-status-flash");
  // scroll the STATUS into view too when it sits below the fold (walk failure #2:
  // the solve gate's answer rendered off-screen = "zero visible response")
  const first = els.find(Boolean) || st;
  if (first) first.scrollIntoView({ behavior: "smooth", block: "center" });
}
const wizFlagMissing = (els, msg) => flagMissing(els, msg, $("wiz-status"));

async function openWizard(mode) {
  if ($("wiz-at").options.length <= 1) $("wiz-at").innerHTML = $("sel-archetype").innerHTML;
  cloneOptions($("wiz-content"), $("preset-content"));
  cloneOptions($("wiz-role"), $("preset-role"));
  wizFormRow();   // Kheldians get the Form question; everyone else never sees it
  // NO DEFAULTS + STATE-LIFECYCLE (Joel's confirmed 0.12.20 eyeball find,
  // superseding the "from your setup" carry): BOTH wizard modes are reached
  // only through the entry cards, and an entry card means a NEW character —
  // every question starts genuinely unanswered, always. The old else-branch
  // re-seeded the previous character's answers as "from your setup" (that's
  // exactly what Joel saw surviving the reset button), and the old travel/
  // identity restores below it did the same for travel, archetype, and
  // powersets. Reset means reset — no exceptions, no browser knowledge
  // required. (If a "tweak my current answers" reopen ever becomes a real
  // flow, it gets its own explicit mode — it never rides the new-character
  // cards again.)
  ["wiz-role", "wiz-content", "wiz-exposure", "wiz-travel", "wiz-form"].forEach(id => {
    if ($(id)) $(id).value = "";
  });
  ["role", "content", "exposure", "travel", "form"].forEach(k => wizSetSrc(k, ""));
  const presetC = $("preset-content"), presetR = $("preset-role");
  if (presetC) presetC.value = "";
  if (presetR) presetR.value = "";
  $("wiz-primary").innerHTML = "<option value=''>— primary set —</option>";
  $("wiz-secondary").innerHTML = "<option value=''>— secondary set —</option>";
  $("wiz-primary").disabled = $("wiz-secondary").disabled = true;
  $("wiz-result").classList.add("hidden");
  $("disc-results").innerHTML = "";
  $("wiz-status").textContent = "";
  const isNew = mode === "new";
  $("wiz-title").textContent = isNew ? "✨ Create a new character" : "♻️ Build a new level-50 character";
  $("wiz-intro").textContent = isNew
    ? "Let's find a character that fits how you want to play — then build it."
    : "Answer a few questions and I'll build the whole thing — powers, slotting, caps, epic, and incarnates.";
  $("wiz-discover").classList.toggle("hidden", !isNew);   // discovery only for Start-new
  $("disc-hint").classList.toggle("hidden", !isNew);      // …and so is its pointer in step 1
  wizUpdateHint();
  $("respec-wizard").classList.remove("hidden");
  // A new character's identity starts unanswered too (the old import-reopen
  // re-fill leaked archetype + powersets through the reset button; the dead-
  // selects bug it fixed can't occur on a blank wizard — the selects are
  // disabled until an archetype is chosen, the normal fresh path).
  $("wiz-at").value = "";
  wizGateBuild();
  wizExplain(null);   // renders only what's actually been answered
}
let _WIZ_BUILT_LEVELING = false;   // set by buildRespec, consumed on ANY wizard exit
function closeRespecWizard() {
  $("respec-wizard").classList.add("hidden");
  if (_WIZ_BUILT_LEVELING) {
    _WIZ_BUILT_LEVELING = false;
    maybeAutoOpenJourney();   // the greet fires however the wizard was left
  }
}

// DISCOVERY: ranked archetypes from the "How do you play?" answers (ONE-COPY
// RULE — the recommender owns no questions; it reads wiz-role/content/exposure).
// The wizard's Role vocabulary is richer than /discover's aim vocabulary:
// "controller" is the aim "control", and "debuffer" ranks exactly as "buffer"
// (the server's buffer/healer/debuff table is one list — Defender-family ATs).
// "pets" has no Role equivalent by design (commanding pets is an archetype,
// not an objective) — the markup carries a visible Mastermind pointer instead.
const _DISC_ROLE = { controller: "control", debuffer: "buffer" };
async function runDiscovery() {
  const roleRaw = $("wiz-role").value;
  if (!roleRaw) {
    // no silent damage-default (the server falls back to "damage" for an
    // unknown role — an unanswered question must never become that quietly)
    wizFlagMissing([$("wiz-role")], "Answer Role first — then I can rank archetypes for you.");
    return;
  }
  const role = _DISC_ROLE[roleRaw] || roleRaw;
  const content = $("wiz-content").value || null;    // unanswered = no assumption,
  const exposure = $("wiz-exposure").value || null;  // not a silent default
  const res = await api("/discover", postJson({ role, content, exposure }));
  if (!res || !res.ok) return;
  $("disc-results").innerHTML = res.recommendations.map((r) =>
    `<div class="disc-card"><div class="disc-top"><span class="disc-at">${escHtml(r.display)}</span>`
    + `<span class="disc-ease">${escHtml(r.ease)}</span></div>`
    + `<div class="disc-why">${escHtml(r.why)} — your <b>${escHtml(r.role_slot)}</b> set is the defining choice `
    + `(${r.defining_sets.length} to pick from).</div>`
    + (r.note ? `<div class="disc-note ${r.note.charAt(0) === "✓" ? "good" : "warn"}">${escHtml(r.note)}</div>` : "")
    + `<button onclick="pickDiscovery('${escHtml(r.archetype)}')">Choose ${escHtml(r.display)} →</button></div>`).join("")
    + `<p class="muted small">${escHtml(res.note)}</p>`;
}
// Level-by-level path (v1): the ordered picks + their slotting, derived from the solved
// build (each power carries its pick_level + slots). The interactive per-step stat popup
// is the next iteration on this same data.
function levelingPlanHtml() {
  // Inherents (Health/Stamina/Brawl…) are AUTO-GRANTED — never a pick. They carry an
  // internal pick_level for sorting, but showing them as choices misleads (field
  // report: "the solver told me to take Health at level 2").
  const isInherent = (p) => (p.full_name || "").startsWith("Inherent.");
  // Creation order: when two picks share level 1, the game asks for the SECONDARY
  // power first (Shriek before Alkaloid) — the tie-break mirrors that everywhere.
  const secFirst = (p) => (p.powerset_full_name === build.secondary ? 0 : 1);
  const ps = (build.powers || []).slice().filter(p => p.pick_level && !isInherent(p))
    .sort((a, b) => ((a.pick_level || 1) - (b.pick_level || 1)) || (secFirst(a) - secFirst(b)));
  if (!ps.length) return "<p class='muted small'>Build a kit first.</p>";
  const inhSlotted = (build.powers || []).filter(p => isInherent(p)
    && (p.slots || []).filter(Boolean).length);
  const rows = ps.map((p) => {
    const filled = (p.slots || []).filter(Boolean).length;
    const sets = [...new Set((p.slots || []).map(s => s && s.set_name)
      .filter(s => s && s !== "Common IO"))];
    const slotTxt = filled
      ? `${filled} slot${filled > 1 ? "s" : ""}${sets.length ? ` — ${sets.slice(0, 2).join(", ")}${sets.length > 2 ? "…" : ""}`
        : (filled === 1 && !sets.length ? " (common IO)" : "")}`
      : "1 slot";
    return `<div class="lvl-row"><span class="lvl-num">${p.pick_level}</span>`
      + `<span class="lvl-pwr"><b>${escHtml(p.display_name || p.full_name.split(".").pop())}</b>`
      + `<span class="muted small"> · ${escHtml(slotTxt)}</span></span></div>`;
  }).join("");
  // Incarnates (all "level 50"), shown after the leveled picks if any are set.
  const inc = Object.entries(build.incarnates || {})
    .filter(([, v]) => v && (v.full_name || v.display_name))
    .map(([slot, v]) => `<div class="lvl-row"><span class="lvl-num">50</span>`
      + `<span class="lvl-pwr"><b>${escHtml(slot)}</b>`
      + `<span class="muted small"> · ${escHtml(v.display_name || v.full_name.split(".").pop().replace(/_/g, " "))}</span></span></div>`)
    .join("");
  const inh = inhSlotted.length
    ? `<div class="lvl-row"><span class="lvl-num">—</span><span class="lvl-pwr">`
      + `<b>Inherent (automatic, never picked):</b> <span class="muted small">`
      + inhSlotted.map(p => `${escHtml(p.display_name || p.full_name.split(".").pop())} `
        + `(${(p.slots || []).filter(Boolean).length} slot${(p.slots || []).filter(Boolean).length > 1 ? "s" : ""})`).join(" · ")
      + ` — the game grants these; just place the slots.</span></span></div>`
    : "";
  return `<div class="lvl-head">📋 Your respec order — pick these in sequence in-game</div>`
    + `<div class="lvl-list">${rows}${inc}${inh}</div>`
    + `<p class="muted small">This is the exact in-game order: take each power at the level shown. Drop your earned slots into them as you go and craft the sets when you can afford them — slot <strong>Attuned</strong> so they survive exemplaring. Travel + survival are taken early on purpose. By 50 you'll match the optimized build.</p>`;
}

// POWER TRAY LAYOUT — fetch the 4-row in-game tray arrangement for the current build and
// render it like the game's trays. App runs offline, so type glyphs map to native emoji
// (no CDN icon font). Hover a slot for the full power + role.
const GLYPH_EMOJI = {
  "ti-lock": "🔒", "ti-sword": "⚔️", "ti-trending-down": "📉", "ti-shield": "🛡️",
  "ti-shield-bolt": "🛡️", "ti-flag": "🚩", "ti-plane": "✈️", "ti-run": "🏃",
  "ti-clock-bolt": "⏱️", "ti-paw": "🐾", "ti-heart-plus": "➕", "ti-flame": "🔥",
  "ti-sparkles": "✨", "ti-eye": "👁️", "ti-eye-off": "🚫", "ti-building-arch": "🏛️",
  "ti-map-pin": "📍", "ti-users-group": "👥", "ti-bed": "🛏️", "ti-mood-smile": "😀",
  "ti-pill": "💊", "ti-circle": "⚪",
};
// Tray semantics (community standard): 1 rotation, 2 mid-fight clicks, 3 set-and-forget
// toggles, 4 travel — colors follow the meaning, not the tray number.
const TRAY_ROLE = { 1: "tray-rot", 2: "tray-util", 3: "tray-on", 4: "tray-move" };

// Render the 4-row in-game tray layout into `out`. These are always-visible labeled sections
// now (no toggle) — refreshBuildViews() keeps them live. App runs offline, so glyphs map to emoji.
// The INCARNATES brick: same shape as a power tray, docked right above them — the
// solver's (or your) six incarnate choices with their in-game family icons.
const INC_SLOT_ORDER = ["Alpha", "Judgement", "Interface", "Lore", "Destiny", "Hybrid"];
function incarnateTrayHtml() {
  const inc = build.incarnates || {};
  if (!Object.keys(inc).length) return "";
  const cells = INC_SLOT_ORDER.map(slot => {
    const v = inc[slot];
    if (!v) {
      return `<div class="tray-slot inc-empty" title="${slot} — no choice yet (Solve recommends one)">`
        + `<span class="tray-ico">⬡</span><span class="tray-name">${slot}</span></div>`;
    }
    const icon = INC_ICON[v.full_name];
    const ico = icon
      ? `<img class="tray-ico-img" src="${icon}" alt="">`
      : `<span class="tray-ico">🜂</span>`;
    return `<div class="tray-slot" title="${escHtml(`${slot}: ${v.display_name}`)}">${ico}`
      + `<span class="tray-name">${escHtml(v.display_name.split(" ")[0])}</span></div>`;
  }).join("");
  return `<div class="tray-row tray-inc"><div class="tray-label">Incarnates</div>`
    + `<div class="tray-slots">${cells}</div></div>`;
}

async function renderTrayLayout(out) {
  const head = `<div class="lvl-head">🎮 In-game power trays — hover a slot for the full power</div>`;
  try {
    const res = await api("/build/trays", postJson({ powers: build.powers, incarnates: build.incarnates || {},
      archetype: build.archetype, role: ($("preset-role") && $("preset-role").value) || null, role_mix: roleMixPayload(),
      exposure: build._exposure || ($("autopick-exposure") && $("autopick-exposure").value) || null, totals: LAST_TOTALS }));
    if (!res || !res.ok) { out.innerHTML = head + "<p class='muted small'>Couldn't build the tray layout.</p>"; return; }
    out.innerHTML = head
      + incarnateTrayHtml()
      + res.trays.map(t => {
          const slots = t.slots.map(s => {
            const emoji = GLYPH_EMOJI[s.glyph] || "⚪";
            const ico = s.icon
              ? `<img class="tray-ico-img" src="${s.icon}" alt=""`
                + ` onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'tray-ico',textContent:'${emoji}'}))">`
              : `<span class="tray-ico">${emoji}</span>`;
            return `<div class="tray-slot" title="${escHtml(s.title)}">${ico}`
              + `<span class="tray-name">${escHtml(s.short)}</span></div>`;
          }).join("");
          return `<div class="tray-row ${TRAY_ROLE[t.group || t.n]}"><div class="tray-label">${escHtml(t.label)}</div>`
            + `<div class="tray-slots">${slots}</div>`
            + (t.note ? `<div class="tray-note">${escHtml(t.note)}</div>` : "") + `</div>`;
        }).join("")
      + `<p class="muted small">The rotation is a priority order, not a strict left-to-right macro — recharge gaps mean you weave the next ready hit. Macros are suggestions to bind; Low FX cuts league visual noise.</p>`;
  } catch (e) {
    out.innerHTML = head + "<p class='muted small'>Couldn't build the tray layout.</p>";
  }
}

// Keep the respec-order + tray-layout sections in plain view and in sync with the current
// build — called at the end of every recompute(). Hidden only when there are no powers yet.
async function refreshBuildViews() {
  const o = $("order-out"), t = $("tray-out");
  const has = !!(build.powers && build.powers.length);
  if (o) { o.classList.toggle("hidden", !has); if (has) o.innerHTML = levelingPlanHtml(); }
  if (t) { t.classList.toggle("hidden", !has); if (has) await renderTrayLayout(t); }
}

// Interactive leveling STEPPER: walk each pick, see the stat it contributes (delta) +
// the cumulative build so far. The per-step "what this choice buys you" the user wanted.
let LEVELING_STEPS = null, LEVEL_STEP_I = 0;
// The stepper is a light, constant evaluator — it suggests, you decide. It tracks whether you've
// gone off the suggested plan (to offer an ADAPT), and holds the last end-game re-fit summary.
let LEVELING_DEVIATED = false, LAST_REFIT = "", LEVELING_TOTAL = 67, LEVELING_IS_EAT = false, LEVELING_EAT_TYPE = null;
const _LVL_STATS = [["sl_res", "S/L res", "%"], ["fire_res", "Fire res", "%"],
  ["ranged_def", "Ranged def", "%"], ["melee_def", "Melee def", "%"], ["aoe_def", "AoE def", "%"],
  ["recharge", "Recharge", "%"], ["recovery", "Recovery", "%"], ["max_hp", "Max HP", "%"],
  ["st_dps", "ST DPS", ""], ["aoe_dps", "AoE DPS", ""]];

async function openLevelStepper() {
  const out = $("wiz-plan-out");
  out.innerHTML = "<p class='muted small'>Walking your levels…</p>";
  const res = await api("/build/leveling-steps", postJson({ archetype: build.archetype, powers: build.powers }));
  if (!res || !res.ok || !res.steps || !res.steps.length) { out.innerHTML = levelingPlanHtml(); return; }
  LEVELING_STEPS = res.steps;
  LEVELING_TOTAL = res.total_slots || 67;
  LEVELING_IS_EAT = !!res.is_eat;
  LEVELING_EAT_TYPE = res.eat_type || null;
  // Resume a leveling character at the level they last told us they're at, not level 1 —
  // so the walk opens where they actually are in-game.
  LEVEL_STEP_I = (isLevelingBuild() && build.level_reached)
    ? _stepIndexForLevel(build.level_reached) : 0;
  renderLevelStep();
}
function renderLevelStep() {
  const steps = LEVELING_STEPS, i = LEVEL_STEP_I, s = steps[i];
  const hasPicks = (s.picks || []).length > 0;
  const deltas = _LVL_STATS.map(([k, lab, u]) => {
    const dv = (s.delta || {})[k]; if (!dv || Math.abs(dv) < 1) return "";
    return `<span class="rt-delta ${dv > 0 ? "up" : "down"}">${dv > 0 ? "+" : ""}${dv}${u} ${lab}</span>`;
  }).filter(Boolean).join(" ");
  const cum = _LVL_STATS.filter(([k]) => (s.stats || {})[k]).map(([k, lab, u]) =>
    `<span class="lvl-stat">${lab} <b>${s.stats[k]}${u}</b></span>`).join("");

  // POWER PICK(S) at this level — each with a "your call" alternative picker.
  let pickHtml = "";
  for (const pk of (s.picks || [])) {
    if (pk.temp) {
      // VEAT phase-1 filler: the end-game build doesn't need a power in this slot,
      // because the level-24 respec re-places everything anyway.
      pickHtml += `<div class="lvl-pick"><span class="lvl-pick-lead">🎬 Pick a power:</span> `
        + `<b>Your choice</b> <span class="muted small">any base-set or pool power you like — `
        + `the level-24 respec rebuilds every pick, so this one is temporary</span></div>`;
      continue;
    }
    const alts = _altPowersForLevel(s.level, pk.full_name);
    pickHtml += `<div class="lvl-pick"><span class="lvl-pick-lead">🎬 Pick a power:</span> `
      + `<b>${escHtml(pk.name)}</b> <span class="muted small">${escHtml(pk.powerset)}</span>`
      + (alts.length
          ? `<div class="lvl-choice"><label class="muted small">🎚️ or take your own here: `
            + `<select onchange="swapLevelPick(${i}, '${escHtml(pk.full_name)}', this.value)">`
            + `<option value="">— guided: ${escHtml(pk.name)} —</option>`
            + alts.map(a => `<option value="${escHtml(a.full_name)}">${escHtml(a.display_name)} · ${escHtml(a.powerset)}</option>`).join("")
            + `</select></label></div>`
          : "")
      + `</div>`;
  }
  // SLOTS granted at this level (only on real slot levels).
  const slotHtml = s.slots
    ? `<div class="lvl-slots">🔧 <b>Place ${s.slots} enhancement slot${s.slots > 1 ? "s" : ""}</b> `
      + `<span class="muted small">(${s.slots_running} / ${LEVELING_TOTAL} placed so far)</span>`
      + (s.enh_advice ? `<div class="muted small lvl-enh">${escHtml(s.enh_advice)}</div>` : "")
      + `</div>`
    : "";
  const msHtml = s.milestone ? `<div class="lvl-milestone">⭐ ${escHtml(s.milestone)}</div>` : "";
  // VEAT level-24 respec: the complete re-place order, branch powers included — placed
  // retroactively, so early slots can now hold branch powers the live walk couldn't offer.
  const respecHtml = (s.respec_order && s.respec_order.length)
    ? `<div class="lvl-respec"><b>🕸️ Respec re-place order</b> <span class="muted small">— in the respec
       screen, take your picks in this order (all six sets are open now, and branch powers can sit in
       early slots):</span><ol class="respec-list">`
      + s.respec_order.map(r => `<li><span class="respec-lvl">L${r.level}</span> ${escHtml(r.name)}
         <span class="muted small">${escHtml(r.powerset)}</span></li>`).join("")
      + `</ol></div>`
    : "";
  const eatBanner = LEVELING_EAT_TYPE === "veat"
    ? `<div class="lvl-eat">🕸️ <strong>Arachnos VEAT</strong> — a two-phase career: levels 1–23 use only your <strong>base sets</strong> (branch powers aren't available yet), then the <strong>mandatory level-24 respec</strong> opens your branch (Crab/Bane · Night Widow/Fortunata) and re-places every pick — the walk hands you the full re-place order at that step. Patron pools open at 35.</div>`
    : LEVELING_EAT_TYPE === "kheldian"
    ? `<div class="lvl-eat">🌌 <strong>Kheldian</strong> — you level from your two big sets (Nova & Dwarf <strong>forms</strong> included) with inherent flight, and take <strong>no epic pool</strong>. The walk reflects that.</div>`
    : "";

  $("wiz-plan-out").innerHTML =
    `<div class="lvl-step">`
    + `<div class="lvl-reassure">🧭 A companion, not a script — take each suggestion or make it yours. Nothing's permanent (a <strong>/respec</strong> at 50 rewrites it all), and I'll keep evaluating as you go.</div>`
    + levelSyncBanner(s.level)
    + eatBanner
    + `<div class="lvl-step-nav">`
    + `<button class="secondary" ${i === 0 ? "disabled" : ""} onclick="levelStep(-1)">◀ Prev</button>`
    + `<span class="lvl-num-big">Level ${s.level}</span>`
    + `<button class="secondary" ${i === steps.length - 1 ? "disabled" : ""} onclick="levelStep(1)">Next ▶</button></div>`
    + pickHtml + slotHtml + msHtml + respecHtml
    + (hasPicks && deltas ? `<div class="lvl-step-delta"><span class="muted small">This pick adds:</span><br>${deltas}</div>` : "")
    + (cum ? `<div class="lvl-step-cum"><span class="muted small">Build so far:</span> ${cum}</div>` : "")
    + (s.tips || []).map(t => `<div class="lvl-tip">💡 ${escHtml(t)}</div>`).join("")
    + (s.play || []).map(t => `<div class="lvl-play">${escHtml(t)}</div>`).join("")
    + `<div class="lvl-eval">`
    + (LEVELING_DEVIATED
        ? `🔀 You've made this your own — good. Want me to <button class="linkbtn" onclick="refitEndgame()">re-fit the end-game around your choices</button>, or keep going and I'll keep suggesting? <button class="linkbtn quiet" onclick="resetToOptimal()">↩ back to the suggested plan</button>`
        : `🧭 Take each suggestion or pick your own — I'll keep evaluating as you go and flag anything worth a look. Nothing's locked.`)
    + `</div>`
    + `<div id="lvl-endgame">${LAST_REFIT}</div>`
    + `</div>`;
}
// ── THE LEVELING JOURNEY (task #16) — the horizontal road ───────────────────
// Design language locked from static/journey_mock2.html (Joel's direction call,
// 2026-07-22): the 1-50 rolls past left-to-right like a map, cards alternate
// above/below the road, you-are-here pulses at the player's level. Same
// grounded data as the stepper (/build/leveling-steps) plus badges.bin content
// (/journey/badges). Cards are COLLAPSED by default (click a card for its
// deltas and tips) — inviting, never crammed. Zone rungs are honesty-tier
// until the i24 server-data pass lands (Joel's sourcing ruling): zone display
// names, level fit, TF/SF rosters and badge coordinates are labeled pending,
// and every content entry rides its provenance string.
let JOURNEY_BADGES = null;
let JOURNEY_ACCS = null;   // /accolades rows, fetched once for the accolades drawer
let JOURNEY_PLACES = null; // /journey/places — the author's route (see the endpoint's docstring)

// Map the route's level bands onto the road's stops. A band starts at a level
// that may not BE a stop (stops only exist where the plan does something), so
// each band and each Task Force lands on the last stop at or before its level —
// nothing is silently dropped for want of an exact match.
function _routeForStops(steps, bands) {
  const out = steps.map(() => ({ events: [] }));
  if (!Array.isArray(bands) || !bands.length) return out;
  const stopAtOrBefore = (lv) => {
    let k = 0;
    for (let i = 0; i < steps.length; i++) { if (steps[i].level <= lv) k = i; else break; }
    return k;
  };
  bands.forEach((b) => {
    out[stopAtOrBefore(b.from)].band = b;
    (b.events || []).forEach(ev => out[stopAtOrBefore(ev.min || b.from)].events.push(ev));
  });
  return out;
}

// Same landing rule as the route: an item whose level isn't a stop lands on the
// last stop at or before it.
function _attachByLevel(steps, items) {
  const out = steps.map(() => []);
  const at = (lv) => { let k = 0; for (let i = 0; i < steps.length; i++) { if (steps[i].level <= lv) k = i; else break; } return k; };
  (items || []).forEach(it => out[at(it.from)].push(it));
  return out;
}

// The story layer lives in the card's DETAIL, not on its face: a contact chain
// is a paragraph, and a paragraph on every stop is the wall we just removed.
// The face carries only the zone name, so you know there's something to open.
function _storyHtml(zones) {
  return (zones || []).map(z =>
    `<div class="jny-story"><b>📖 ${escHtml(z.zone)}</b> <span class="muted small">levels ${z.from}–${z.to}</span>`
    + (z.contacts && z.contacts.length
        ? `<div class="jny-story-chain">${z.contacts.map(escHtml).join(" → ")}</div>` : "")
    + (z.unlocks ? `<div class="jny-tip">🔓 ${escHtml(z.unlocks)}</div>` : "")
    + (z.xp_pause ? `<div class="jny-tip">⏸ pause XP at ${z.xp_pause.join(", then ")}</div>` : "")
    + (z.content_warning ? `<div class="jny-warn">⚠ ${escHtml(z.content_warning)}</div>` : "")
    + (z.note ? `<div class="muted small">${escHtml(z.note)}</div>` : "")
    + `</div>`).join("");
}

// ── THE LEVEL PANEL (Joel's layout ruling, 2026-07-24) ──────────────────────
// "Zone image on left, then all info on right. Able to be scrolled down within
// its window instead of maxing the whole time line size." So the road went back
// to being a slim timetable and everything that used to fatten the cards lives
// here, in one fixed-height window that scrolls itself.
let _JNY_SEL = null;   // selected stop index
let _JNY_CTX = null;   // {steps, route, storyAt, ...} — set by renderJourney

window.selectJourneyStop = function (i) {
  _JNY_SEL = i;
  document.querySelectorAll("#journey-body .jny-card").forEach((c, k) =>
    c.classList.toggle("sel", k === i));
  renderJourneyLevelPanel();
};

// ── ZONE ↔ BADGE ↔ ACCOLADE JOIN ────────────────────────────────────────────
// Badges and accolades belong ON the level that sends you to their zone, not in
// a wall underneath (Joel). Two grounded joins make that possible, and neither
// invents a name:
//   1. badges.bin groups exploration badges under zone keys that ARE the English
//      names in CamelCase (AtlasPark, SharkheadIsle). Matching a name we already
//      have TO a key is safe; GENERATING a name FROM a key is not, and we still
//      don't do that (CreysFolley is not "Creys Folley").
//   2. the accolade roster's own text says where each component badge lives —
//      "Exploration badge in Sharkhead Isle" — so the zone name comes from the
//      game's data, not from us.
// Anything that doesn't match simply shows nothing. No guesses, no near-misses.
const _zoneNorm = (s) => String(s || "").toLowerCase()
  .replace(/^(the|echo:)\s+/g, "").replace(/[^a-z0-9]/g, "");

function _zoneKeysFor(name, zones) {
  const n = _zoneNorm(name);
  if (!n) return [];
  const exact = zones.filter(z => _zoneNorm(z.zone_key) === n);
  if (exact.length) return exact;
  // "Striga Isle" → Striga and "Talos" → TalosIsland: one is a prefix of the
  // other, either direction. Guarded at 5 characters so short keys can't
  // over-match ("Eden" must never swallow something else).
  return zones.filter(z => {
    const k = _zoneNorm(z.zone_key);
    return k.length >= 5 && n.length >= 5 && (n.startsWith(k) || k.startsWith(n));
  });
}

// Route places read "Atlas Park missions" / "Kings Row missions/radios" — the
// zone is the part in front. Anything that isn't a place at all ("street
// sweeping") simply fails to match, which is the correct outcome.
const _placeZoneName = (p) => String(p || "")
  .replace(/\s*missions?\b.*$/i, "").replace(/\s*\/\s*radios?\b/i, "").trim();

// One zone, listed once, under its fullest name. The story layer says "The
// Hollows" and the route says "Hollows"; first wins, and the story layer is
// passed first on purpose.
function _dedupeZoneNames(names) {
  const seen = new Map();
  names.filter(Boolean).forEach((n) => { const k = _zoneNorm(n); if (!seen.has(k)) seen.set(k, n); });
  return [...seen.values()];
}

// accolade component badges, indexed by the zone the GAME says they're in
function _accoladesByZone() {
  const idx = {};
  ((JOURNEY_ACCS || {}).rows || []).filter(a => a.tier === "passive").forEach((a) => {
    (a.badge_chain || []).forEach((c) => {
      const m = /badge in (.+?)\.?$/i.exec(c.tracks || "");
      if (!m) return;
      (idx[_zoneNorm(m[1])] = idx[_zoneNorm(m[1])] || []).push(
        { accolade: a.display || a.key, badge: c.badge });
    });
  });
  return idx;
}

function _zoneRewardsHtml(zoneNames) {
  const zones = (JOURNEY_BADGES || {}).zones || [];
  const accIdx = _accoladesByZone();
  return zoneNames.map((name) => {
    const keys = _zoneKeysFor(name, zones);
    const badges = keys.flatMap(k => k.badges || []);
    const accs = accIdx[_zoneNorm(name)] || [];
    if (!badges.length && !accs.length) return "";
    return `<div class="jny-rewards"><b>🏅 In ${escHtml(name)}</b>`
      + (badges.length
          ? `<div class="muted small">${badges.length} exploration badge${badges.length > 1 ? "s" : ""}: `
            + badges.slice(0, 6).map(b => escHtml(b.display_hero || b.display_villain)).join(", ")
            + (badges.length > 6 ? `, +${badges.length - 6} more` : "") + `</div>`
          : "")
      + accs.map(a => `<div class="jny-acc">⭐ <b>${escHtml(a.accolade)}</b> accolade — `
          + `its <i>${escHtml(a.badge)}</i> badge is here</div>`).join("")
      + `</div>`;
  }).join("");
}

// The art slot: the game's OWN zone map, extracted from the client's pigg
// archives (tools/extract_zone_art.py). Only 11 of the game's 38 mapped zones
// ship a map texture, so most levels have no art — and that slot says so rather
// than showing a picture of the wrong place.
// Zones that arrived AFTER Gulbasaur wrote the guides. Shown on the levels they
// cover, in their own block, with their own source line — the road should not
// quietly end at 2020.
function _modernHtml(level) {
  const m = (JOURNEY_PLACES || {}).modern || {};
  // A zone with no level range is NOT placed. A range is the whole basis for
  // putting a zone in front of someone at a given level, so a missing one is
  // recorded in the data and skipped here — never approximated.
  const hits = (m.zones || []).filter(z => z.from != null && z.to != null
    && level >= z.from && level <= z.to);
  if (!hits.length) return "";
  return hits.map((z) => {
    // Neighbourhoods carry their OWN level bands, which is the finest-grained
    // "where should I actually be standing" the Journey has — so only the ones
    // that fit this level are shown.
    const hoods = (z.neighborhoods || []).filter(n => level >= n.from && level <= n.to);
    const events = (z.events || []).filter(e => !e.min || (level >= e.min && level <= (e.max || 50)));
    const foes = z.enemies || [];
    const parts = [
      `<div class="jny-modern"><b>🆕 ${escHtml(z.zone)}</b> `
        + `<span class="muted small">${escHtml(z.kind || "")} · ${z.from}–${z.to}`
        + (z.since ? ` · ${escHtml(z.since)}` : "") + `</span>`,
      // PvP is stated before anything else about the zone. "Other players can
      // attack you" is not a detail to discover after walking in.
      z.pvp ? `<div class="jny-warn">⚔ <b>PvP zone.</b> ${escHtml(z.pvp_note || "")}</div>` : "",
      // A separate starting path is not a place you visit — it is a different
      // road entirely, and saying so first stops it reading as a detour.
      z.alt_start ? `<div class="jny-altstart">🧭 <b>A different road.</b> ${escHtml(z.alt_start_note || "")}</div>` : "",
      // Yellow/Orange/Red is the wiki's own difficulty marking, and it answers
      // the question the game's tram board never does: you CAN go in, but is it
      // a fight you want at this level? (Joel's Positron case, per-neighbourhood.)
      hoods.length
        ? `<div class="jny-route-places">At your level: `
          + hoods.map(n => escHtml(n.name)
              + (n.risk ? ` <span class="jny-risk risk-${n.risk.toLowerCase()}">${escHtml(n.risk)}</span>` : ""))
              .join(" · ")
          + `</div>` : "",
      events.map(_eventHtml).join(""),
      foes.length
        ? `<div class="muted small">Who you'll fight: ${foes.slice(0, 8).map(escHtml).join(", ")}`
          + (foes.length > 8 ? `, +${foes.length - 8} more` : "") + `</div>` : "",
      (z.safe_havens || []).length
        ? `<div class="jny-tip">🛡 Safe spots: ${z.safe_havens.map(escHtml).join(" · ")}`
          + (z.safe_havens_note ? ` <span class="muted small">— ${escHtml(z.safe_havens_note)}</span>` : "")
          + `</div>` : "",
      (z.contacts || []).length
        ? `<div class="muted small">Contacts: ${z.contacts.map(escHtml).join(" · ")}</div>` : "",
      z.note ? `<div class="muted small">${escHtml(z.note)}</div>` : "",
      `</div>`,
    ];
    return parts.join("");
  }).join("") + `<div class="jny-route-src">newer than the guides: ${escHtml(m.provenance)}</div>`;
}

// Art lookup tolerates the same near-miss the badge join does: the route says
// "Talos", the asset is "TalosIsland". Exact first, then a prefix either way,
// guarded at 5 characters so nothing short over-matches.
function _artFileFor(name) {
  const art = (JOURNEY_PLACES || {}).art || {};
  const n = _zoneNorm(name);
  if (!n) return null;
  // A zone may declare which art asset is its own, for the cases where the
  // client ships it under a historical name (Boomtown's map is "Baumton").
  // Only ever from the data, with a stated reason — never inferred here.
  const declared = ((JOURNEY_PLACES || {}).modern || {}).zones || [];
  const owner = declared.find(z => z.art_key && _zoneNorm(z.zone) === n);
  if (owner && art[owner.art_key]) return art[owner.art_key];
  if (art[n]) return art[n];
  const k = Object.keys(art).find(key =>
    key.length >= 5 && n.length >= 5 && (n.startsWith(key) || key.startsWith(n)));
  return k ? art[k] : null;
}

function _zoneArtHtml(names) {
  // Show the first zone at this level that HAS art, not just the first zone —
  // level 1 lists "Tutorial" before "Atlas Park", and only one of them is a
  // place with a map.
  const zoneName = names.find(n => _artFileFor(n)) || names[0] || "";
  const file = _artFileFor(zoneName);
  return `<div class="jny-art${file ? " has-art" : ""}">`
    + (file
        ? `<img src="/static/zone_art/${encodeURIComponent(file)}" alt="${escHtml(zoneName)} map"
             title="${escHtml(zoneName)} — the game's own zone map">`
        : (zoneName ? `<div class="jny-art-name">${escHtml(zoneName)}</div>` : "")
          + `<div class="jny-art-pending">no map art for this zone<br>`
          + `<span class="muted small">the client ships one for 11 zones only</span></div>`)
    + `</div>`;
}

function renderJourneyLevelPanel() {
  const host = document.getElementById("jny-panel");
  if (!host || !_JNY_CTX) return;
  const { steps, route, storyAt, bands, lvBadges, hereIdx } = _JNY_CTX;
  const i = _JNY_SEL, s = steps[i];
  if (!s) { host.innerHTML = ""; return; }
  const band = route[i].band || _routeBandAt(s.level, bands);
  const zones = storyAt[i];
  // The art follows the story zone when there is one, otherwise the route's
  // first named place — the thing a player would actually be looking at.
  // Every zone this level sends you to, story names first, deduped by normalised
  // name — one list feeds both the art slot and the badge/accolade block.
  const zoneNames = _dedupeZoneNames(zones.map(z => z.zone)
    .concat((band ? band.places : []).map(_placeZoneName)));
  const lb = lvBadges[s.level];
  const deltas = _LVL_STATS.map(([k, lab, u]) => {
    const dv = (s.delta || {})[k]; if (!dv || Math.abs(dv) < 1) return "";
    return `<span class="rt-delta ${dv > 0 ? "up" : "down"}">${dv > 0 ? "+" : ""}${dv}${u} ${lab}</span>`;
  }).filter(Boolean).join(" ");

  host.innerHTML = _zoneArtHtml(zoneNames)
    + `<div class="jny-panel-info">`
    + `<h4 class="jny-panel-h">Level ${s.level}`
    + (i === hereIdx ? ` <span class="jny-panel-here">★ you are here</span>`
       : i < hereIdx ? ` <span class="muted small">— reached</span>` : "")
    + `</h4>`
    + (s.picks || []).map(pk => pk.temp
        ? `<div class="jny-pick"><b>Your choice</b> <span class="muted small">temporary — the level-24 respec re-places it</span></div>`
        : `<div class="jny-pick"><b>${escHtml(pk.name)}</b> <span class="muted small">${escHtml(pk.powerset)}</span></div>`).join("")
    + (s.slots ? `<div class="muted small">${s.slots} new slot${s.slots > 1 ? "s" : ""} — ${s.slots_running} / ${LEVELING_TOTAL} placed</div>` : "")
    + (s.milestone ? `<div class="jny-ms">⭐ ${escHtml(s.milestone)}</div>` : "")
    + (lb ? `<div class="jny-zbadge"><b>🏅 ${escHtml(lb.display_hero)}</b>`
        + `<div class="muted small">${escHtml(lb.desc_hero || lb.desc_villain || "")}</div></div>` : "")
    + (deltas ? `<div class="jny-detail-deltas">${deltas}</div>` : "")
    + (s.tips || []).map(t => `<div class="jny-tip">💡 ${escHtml(t)}</div>`).join("")
    + _routeHtml(band, route[i].events, true)
    + (band ? `<div class="jny-route-src">where to play: ${escHtml(_JNY_CTX.routeProv)}</div>` : "")
    + _storyHtml(zones)
    + (zones.length ? `<div class="jny-route-src">story route: ${escHtml(_JNY_CTX.storyProv)}</div>` : "")
    // What's worth collecting where this level sends you — named here, not left
    // in the catalogue below.
    // Deduped by NORMALISED name: the story layer says "The Hollows" and the
    // route says "Hollows missions", and those are one zone, listed once. Story
    // names come first so the fuller wording wins.
    + _zoneRewardsHtml(zoneNames)
    + _modernHtml(s.level)
    + (zones.some(z => z.xp_pause) && _JNY_CTX.xpMacro.text
        ? `<div class="jny-tip">⏸ XP toggle macro: <code>${escHtml(_JNY_CTX.xpMacro.text)}</code></div>` : "")
    + `</div>`;
}

// The Master-of / iTrial challenge badge for a task force or trial, matched by
// name to the events the road already lists. "Apex TF" → "apex", "Lambda Sector
// (LAM)" → "lambdasector", "Behavioral Adjustment Facility (BAF)" → its acronym
// "baf". Returns null when a run has no Master badge (most low-level TFs).
function _challengeFor(eventName) {
  const ch = (JOURNEY_PLACES || {}).challenges || {};
  if (!eventName) return null;
  const paren = /\(([^)]+)\)/.exec(eventName);           // the (BAF) acronym, if any
  const acr = paren ? _zoneNorm(paren[1]) : "";
  const base = _zoneNorm(eventName.replace(/\([^)]*\)/, "")
    .replace(/\b(task force|strike force|trial|tf|sf)\b/gi, ""));
  for (const [key, rec] of Object.entries(ch)) {
    if (key === base || key === acr) return rec;
    if (key.length >= 5 && base.length >= 5 && (key.startsWith(base) || base.startsWith(key))) return rec;
  }
  return null;
}

// One event line, plus its Master badge and challenge checklist if it has one.
function _eventHtml(ev) {
  const range = ev.min ? ` <span class="muted small">(${ev.min}${ev.max ? `–${ev.max}` : "+"})</span>` : "";
  const note = ev.note ? ` <span class="muted small">· ${escHtml(ev.note)}</span>` : "";
  let html = `<div class="jny-tf">${ev.kind === "trial" ? "⚔" : "🛡"} ${escHtml(ev.name)}${range}${note}</div>`;
  const c = _challengeFor(ev.name);
  if (c) {
    html += `<div class="jny-master">🏆 <b>${escHtml(c.master_badge)}</b>`
      + (c.challenge_badges && c.challenge_badges.length
          ? ` — earn: ${c.challenge_badges.map(escHtml).join(", ")}`
          : "")
      + `</div>`;
  }
  return html;
}

function _routeBandAt(level, bands) {
  return (bands || []).find(b => level >= b.from && level <= b.to) || null;
}

// One block: where this level plays, and what opens up here. Kept to a few
// lines on purpose — this is a signpost, not the wall of everything-everywhere
// the drawers used to be.
function _routeHtml(band, events, showPlaces) {
  const bits = [];
  if (band && showPlaces) {
    bits.push(`<div class="jny-route"><b>📍 Levels ${band.from}–${band.to}</b>`
      + `<div class="jny-route-places">${band.places.map(escHtml).join(" · ")}</div>`
      + (band.advice ? `<div class="jny-tip">💡 ${escHtml(band.advice)}</div>` : "")
      + `</div>`);
  }
  events.forEach((ev) => bits.push(_eventHtml(ev)));
  return bits.join("");
}

async function openJourneyView(auto = false) {
  // The road gets its own full-width overlay (a 720px wizard box cramps a
  // horizontal journey) — so it opens identically from the wizard's result
  // button, the header 🗺️, or a resumed character. `auto` marks a first-
  // meeting self-open (maybeAutoOpenJourney) — only THAT close is a decision.
  _journeyAutoOpened = auto;
  const modal = $("journey-modal"), out = $("journey-body");
  modal.classList.remove("hidden");
  const jb = $("journey-btn");
  if (jb) jb.classList.add("journey-open");   // the pill reads as "on" while the road is out
  out.innerHTML = "<p class='muted small'>Rolling out the road…</p>";
  if (!LEVELING_STEPS) {
    const res = await api("/build/leveling-steps",
      postJson({ archetype: build.archetype, powers: build.powers }));
    if (!res || !res.ok || !res.steps || !res.steps.length) {
      out.innerHTML = "<p class='muted'>I couldn't lay the road out — the plan needs powers first.</p>";
      return;
    }
    LEVELING_STEPS = res.steps;
    LEVELING_TOTAL = res.total_slots || 67;
  }
  if (!JOURNEY_BADGES) JOURNEY_BADGES = (await api("/journey/badges")) || {};
  if (!JOURNEY_ACCS) JOURNEY_ACCS = (await api("/accolades")) || {};
  if (!JOURNEY_PLACES) JOURNEY_PLACES = (await api("/journey/places")) || {};
  renderJourney();
  // greet the player at their level: center the you-are-here stop
  const here = document.querySelector(".jny-stop.here");
  if (here) here.scrollIntoView({ inline: "center", block: "nearest" });
}

// FIRST MEETING (Joel's ruling, 2026-07-22): a 1-50 character's journey view
// STARTS ON — it is the point of a leveling wizard — and its first appearance
// says what it is, how to toggle it, and how to hook up the chat log. Then
// the user decides (choice doctrine): any close is a remembered decision, we
// never force it open again. Non-leveling builds aren't auto-opened, but
// their first manual open shows the same intro, so the basics are always
// somewhere.
// SEMANTICS (Joel, third field report 2026-07-23 — the once-per-browser
// greeting was the bug all along): the road opens for EVERY new 1-50
// character. Closing is just closing — it never records a decision. The
// remembered, reversible "no" is an EXPLICIT visible checkbox in the road's
// header ("open automatically for new 1–50 characters" → journeyAutoOff).
// The intro card shows until "Got it" is actually pressed (journeyIntroSeen
// — a fresh key: the old ones recorded closes-as-decisions, which closes no
// longer mean).
let _journeyAutoOpened = false;
function journeyIntroDone() { return !!localStorage.getItem("journeyIntroSeen"); }
function journeyAutoOff() { return !!localStorage.getItem("journeyAutoOff"); }
window.journeyIntroGotIt = function () {
  try { localStorage.setItem("journeyIntroSeen", "1"); } catch (e) { /* private mode */ }
  const card = document.getElementById("jny-intro");
  if (card) card.remove();
};
window.setJourneyAutoOpen = function (on) {
  try {
    if (on) localStorage.removeItem("journeyAutoOff");
    else localStorage.setItem("journeyAutoOff", "1");
  } catch (e) { /* private mode */ }
};
function maybeAutoOpenJourney() {
  // Every gate says WHY out loud. Five rounds of "nothing happened" were five
  // rounds of guessing which of these three returned early on a screen I can't
  // see; the console now answers it in one line, from whichever of the three
  // call sites ran (resume, wizard exit, build finish).
  const why = !isNewCharacterPlan() ? `not a new character (mode=${build._mode})`
    : !(build.powers || []).length ? "no powers in the build yet"
    : journeyAutoOff() ? "auto-open is switched off (road header checkbox)"
    : "";
  console.log(`[journey] greet ${why ? "SKIPPED — " + why : "OPENING"}`,
              { mode: build._mode, powers: (build.powers || []).length,
                autoOff: journeyAutoOff(), introSeen: journeyIntroDone() });
  if (why) return false;
  openJourneyView(true);
  return true;
}
function _journeyIntroHtml() {
  return `<div class="jny-intro" id="jny-intro">
    <b>👋 This is your Leveling Journey</b> — the whole 1–50 as a road. Every stop
    is a level where your plan does something: the power to pick, the enhancement
    slots to place, milestones and badges along the way. Click any card to see
    what that level buys you. The ★ marker is you — it moves when you update your
    level in the plan.
    <div class="muted small" style="margin-top:6px">Close it any time (✕ or Esc) and bring it
    back with the <b>🗺️ Journey</b> button in the header — it's a simple on/off switch.</div>
    <div style="margin-top:8px">💡 <b>Worth doing now:</b> turn on the game's chat log.
    Hero Companion reads it (only on your machine, only with your say-so) and your
    Play Log fills with what you actually earned — influence, drops with keep/sell
    calls, session insights — while you just play.</div>
    ${gamelogSetupHelp()}
    <button class="secondary" style="width:auto;margin-top:8px" onclick="journeyIntroGotIt()">Got it — don't show this again</button>
  </div>`;
}

// One switch, both directions: the header "🗺️ Journey" pill opens the road
// and closes it again. When the overlay closes any OTHER way (✕, Esc,
// clicking the dark backdrop), the pill pulses for a moment so the user
// learns where the road lives before they ever need to find it again.
function closeJourneyView(teach = true) {
  $("journey-modal").classList.add("hidden");
  const jb = $("journey-btn");
  if (jb) jb.classList.remove("journey-open");
  if (teach) teachJourneyPill();
  _journeyAutoOpened = false;   // closing is just closing — no decision recorded
}

function toggleJourneyView() {
  if ($("journey-modal").classList.contains("hidden")) openJourneyView();
  else closeJourneyView(false);           // they used the pill — no lesson needed
}

function teachJourneyPill() {
  const jb = $("journey-btn");
  if (!jb || getComputedStyle(jb).display === "none") return;
  jb.classList.remove("journey-pulse");
  void jb.offsetWidth;                    // restart the animation
  jb.classList.add("journey-pulse");
  setTimeout(() => jb.classList.remove("journey-pulse"), 2600);
}

// The road claims exactly the height its cards need, no more. Cards sit above
// and below the line, so the lane must reserve room for the tallest one; every
// fixed guess has been wrong in one direction or the other (190px clipped an
// open card, 240px ate the screen with everything collapsed). Measure instead:
// tallest card + the 34px stem that lifts it off the line + a little air.
// Every card hangs BELOW the line now, so the lane reserves room on one side
// only: above it there is just the ★ marker. Measured, never guessed — a fixed
// number has been wrong in both directions here (190px clipped an open card,
// 240px ate the screen with everything collapsed).
function _fitJourneyLane() {
  const lane = document.querySelector("#journey-body .jny-lane");
  if (!lane) return;
  let tallest = 0;
  lane.querySelectorAll(".jny-card").forEach(c => { tallest = Math.max(tallest, c.offsetHeight); });
  lane.style.paddingTop = "56px";                                    // ★ marker + air
  if (tallest) lane.style.paddingBottom = `${Math.ceil(tallest) + 46}px`;
}

// Grab-and-drag panning (Joel's report: the road wouldn't drag with the mouse
// — only wheel/keys scrolled it; a map you scroll like a map should drag like
// one). Click-vs-drag discrimination at 5px so card clicks still work, and
// the click that ends a real drag is swallowed so it can't toggle a card.
function _wireJourneyDrag() {
  const strip = document.querySelector("#journey-body .jny-strip");
  if (!strip) return;
  let down = null, dragged = false;
  strip.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    down = { x: e.clientX, left: strip.scrollLeft }; dragged = false;
  });
  strip.addEventListener("pointermove", (e) => {
    if (!down) return;
    const dx = e.clientX - down.x;
    if (!dragged && Math.abs(dx) > 5) {
      dragged = true;
      strip.classList.add("jny-grabbing");
      try { strip.setPointerCapture(e.pointerId); } catch (err) { /* older engines */ }
    }
    if (dragged) strip.scrollLeft = down.left - dx;
  });
  const end = () => {
    if (dragged) strip.addEventListener("click",
      (ce) => { ce.stopPropagation(); ce.preventDefault(); }, { capture: true, once: true });
    down = null; dragged = false; strip.classList.remove("jny-grabbing");
  };
  strip.addEventListener("pointerup", end);
  strip.addEventListener("pointercancel", end);
}

function renderJourney() {
  const steps = LEVELING_STEPS;
  // a leveling character starts the road at level 1 even before their first sync
  const hereLv = isLevelingBuild() ? (build.level_reached || 1) : null;
  const hereIdx = hereLv != null ? _stepIndexForLevel(hereLv) : -1;
  const jb = JOURNEY_BADGES || {};
  const lvBadges = jb.level_badges || {};
  // The route follows the character's side — the Rogue Isles are a different road.
  const align = (localStorage.getItem("cohAlignment") || "hero") === "villain" ? "villain" : "hero";
  const bands = (JOURNEY_PLACES || {})[align] || [];
  const route = _routeForStops(steps, bands);
  const storyLayer = (JOURNEY_PLACES || {}).story || {};
  const storyAt = _attachByLevel(steps, (storyLayer[align] || {}).zones || []);

  const stops = steps.map((s, i) => {
    const state = i < hereIdx ? "done" : i === hereIdx ? "here" : "";
    const picks = (s.picks || []).map(pk => pk.temp
      ? `<div class="jny-pick"><b>Your choice</b> <span class="muted small">temporary — the level-24 respec re-places it</span></div>`
      : `<div class="jny-pick"><b>${escHtml(pk.name)}</b> <span class="muted small">${escHtml(pk.powerset)}</span></div>`
    ).join("");
    const slotDots = s.slots
      ? `<div class="jny-slots">${'<span class="new"></span>'.repeat(s.slots)}
         <span class="muted small">${s.slots_running} / ${LEVELING_TOTAL} placed</span></div>`
      : "";
    const lb = lvBadges[s.level];
    const badgeChip = lb
      ? `<span class="jny-chip badge" title="${escHtml(lb.desc_hero || lb.desc_villain || "")}">🏅 ${escHtml(lb.display_hero)}${lb.display_villain && lb.display_villain !== lb.display_hero ? ` / ${escHtml(lb.display_villain)}` : ""}</span>`
      : "";
    const ms = s.milestone ? `<div class="jny-ms">⭐ ${escHtml(s.milestone)}</div>` : "";
    // collapsed by default: deltas + tips live behind the card click
    const deltas = _LVL_STATS.map(([k, lab, u]) => {
      const dv = (s.delta || {})[k]; if (!dv || Math.abs(dv) < 1) return "";
      return `<span class="rt-delta ${dv > 0 ? "up" : "down"}">${dv > 0 ? "+" : ""}${dv}${u} ${lab}</span>`;
    }).filter(Boolean).join(" ");
    // THE ROAD IS A TIMETABLE, NOT A NOTICEBOARD (Joel's layout ruling): the
    // stop carries only what fits at a glance — the level, its picks, its slots
    // and a marker that there's more. Everything else moves to the panel below,
    // which scrolls in its own window instead of stretching the whole road.
    const marks = (route[i].band ? "📍" : "") + (route[i].events.length ? "🛡" : "")
      + (storyAt[i].length ? "📖" : "");
    return `<div class="jny-stop ${state}"><div class="jny-node">${s.level}</div>`
      + (state === "here" ? `<div class="jny-youare">★ you are here</div>` : "")
      + `<div class="jny-card${i === _JNY_SEL ? " sel" : ""}" id="jny-card-${i}"`
      + ` onclick="selectJourneyStop(${i})" title="click to see this level in full">`
      + `<div class="jny-lv">Level ${s.level}${state === "done" ? " — reached ✓" : state === "here" ? " — now" : ""}</div>`
      + picks + slotDots + ms + badgeChip
      + (marks ? `<div class="jny-marks">${marks}</div>` : "")
      + `</div></div>`;
  }).join("");

  // Panel context — the panel re-renders on click without rebuilding the road.
  _JNY_CTX = { steps, route, storyAt, bands, lvBadges, hereIdx,
               storyProv: (storyLayer.provenance || ""), storyUrls: storyLayer.urls || {},
               xpMacro: storyLayer.xp_macro || {},
               routeProv: (JOURNEY_PLACES || {}).provenance || "" };
  if (_JNY_SEL == null || _JNY_SEL >= steps.length) _JNY_SEL = hereIdx >= 0 ? hereIdx : 0;

  const badgeLocCredit = jb.location_credit || "";
  const zones = (jb.zones || []).map(z =>
    `<details class="jny-zone"><summary><b>${escHtml(z.zone_key)}</b>
       <span class="muted small">${z.badges.length} exploration badge${z.badges.length > 1 ? "s" : ""}</span></summary>`
    + z.badges.map(b => `<div class="jny-zbadge"><b>${escHtml(b.display_hero || b.display_villain)}</b>`
        // WHERE it is (n15g's directions) leads; the flavour text follows.
        + (b.where ? `<div class="jny-where">📍 ${escHtml(b.where)}`
            + (b.coords ? ` <span class="muted small">(${b.coords.join(", ")})</span>` : "") + `</div>` : "")
        + (b.find_hint ? `<div class="muted small">${escHtml(b.find_hint)}</div>` : "")
        + `</div>`).join("")
    + `</details>`).join("");

  // Accolades drawer — the build-affecting (passive) tier from the game-first
  // roster the Accolades panel already ships; attainment text rides where the
  // game data carries it, and its absence is stated, never papered over.
  const accRows = ((JOURNEY_ACCS || {}).rows || []).filter(a => a.tier === "passive");
  const accs = accRows.map(a =>
    `<details class="jny-zone"><summary><b>${escHtml(a.display || a.key)}</b>
       <span class="muted small">${escHtml(a.effect_short || "")}${a.standard_assumed ? " · one of the standard four" : ""}</span></summary>
     <div class="jny-zbadge">${a.attain_summary || a.attain
        ? `<div class="muted small">${escHtml(a.attain_summary || a.attain)}</div>`
        : `<div class="muted small">How to earn it isn't in the game's client files — attainment text arrives with the server-data pass.</div>`}
     ${(a.badge_chain || []).length ? `<div class="muted small">Badge chain: ${a.badge_chain.map(escHtml).join(" → ")}</div>` : ""}
     </div></details>`).join("");

  // step-by-step lives in the wizard modal — only offer the jump when it's open
  const wizOpen = !document.getElementById("respec-wizard").classList.contains("hidden");
  $("journey-body").innerHTML =
    `<div class="jny">`
    + (journeyIntroDone() ? "" : _journeyIntroHtml())
    + `<div class="jny-head"><span class="muted small">Scroll or drag the road — every stop is a level your plan does something. Click a card for what it buys you.</span>`
    + (wizOpen ? ` <button class="linkbtn" onclick="closeJourneyView(); openLevelStepper()">▶ step-by-step view</button>` : "")
    + ` <label class="muted small jny-autoopen"><input type="checkbox" id="jny-autoopen"
        ${journeyAutoOff() ? "" : "checked"} onchange="setJourneyAutoOpen(this.checked)">
        open automatically for new characters</label>`
    + `</div>`
    + `<div class="jny-viewport"><div class="jny-strip"><div class="jny-lane">${stops}</div></div></div>`
    + `<div class="jny-panel" id="jny-panel"></div>`
    + (zones
        ? `<details class="jny-zones"><summary>🧭 <b>Zones & badges</b> <span class="muted small">— the grounded
           catalog from the game's own files. ${escHtml(jb.pending || "")}</span></summary>
           <div class="jny-zonegrid">${zones}</div>
           <div class="jny-prov">badge identity: ${escHtml(jb.provenance || "badges.bin")}`
           + (badgeLocCredit ? ` · 📍 ${escHtml(badgeLocCredit)}` : "")
           + ` · visual finder: the VidiotMaps in-game map overlay</div></details>`
        : "")
    + (accs
        ? `<details class="jny-zones"><summary>🏅 <b>Accolades worth working toward</b> <span class="muted small">—
           permanent build bonuses; tick the ones you own in the Accolades panel and the totals follow.</span></summary>
           <div class="jny-zonegrid">${accs}</div></details>`
        : "")
    + `</div>`;
  _wireJourneyDrag();
  _fitJourneyLane();
  renderJourneyLevelPanel();
}

// ── Level tracking + absence flag (leveling builds only) ────────────────────
// The companion can only stay in sync with what the player TELLS it — we don't watch
// the game. So a leveling character carries build.level_reached (last-known level), and
// the banner lets them confirm/update it. If they've advanced several levels since the
// last sync, we flag the drift and offer the in-game .txt import as the catch-up path,
// because guiding from a stale level ("take Hover at 6" when they're already 18) is
// exactly the amateur-hour mistake the tool must avoid.
const SYNC_DRIFT_LEVELS = 5;   // gap that triggers a "let's re-sync" nudge

function isLevelingBuild() { return build._mode === "new"; }
// A character that does NOT exist in the game yet — whether the plan walks 1-50
// or targets the end-game kit. BOTH still have to be levelled from 1, so both
// get the road (Joel's field report: he reached for "Build a new level-50
// character", built, and got silence — the greet was gated on the 1-50 card
// alone). Imported/respec'd characters are real and already somewhere; their
// greeting waits for the Leveling Companion catch-up rung.
function isNewCharacterPlan() { return build._mode === "new" || build._mode === "new50"; }

// GAME RULE (Joel, 2026-07-17): endgame content unlocks by level — Epic /
// Ancillary powers at level 35 (Patron pools ALSO require completing their
// Patron arc), incarnate abilities at level 50. The 1-50 leveling walk PREVIEWS
// the finished build, so — per Joel's ruling + the choice doctrine ("advise,
// don't override") — we DON'T block: the player may toggle incarnates on and
// keep epic picks in the plan, and we WARN that these aren't available at their
// current level yet. The "Build a new level-50 character" path (level_reached
// = 50) is an endgame plan, so nothing warns there.
function incarnatesUnlocked() {
  return (build.level_reached || (isLevelingBuild() ? 1 : 50)) >= 50;
}

// The warnings shown when a leveling character previews content it hasn't
// unlocked. Empty unless we're in the 1-50 walk AND actually previewing gated
// content — so a fresh level-50 build never warns.
function endgameWarnings() {
  const out = [];
  if (!isLevelingBuild()) return out;
  const lv = build.level_reached || 1;
  if (build.include_incarnates && lv < 50) {
    out.push(`⚠️ Incarnate abilities unlock at level 50. These peak totals are an `
      + `endgame preview — your level-${lv} character doesn't have them yet.`);
  }
  const hasEpic = (build.powers || []).some(p => (p.full_name || "").startsWith("Epic."));
  if (hasEpic && lv < 35) {
    out.push(`⚠️ Epic / Ancillary powers unlock at level 35 (Patron pools also `
      + `require completing their Patron arc). They're in your plan as a preview `
      + `— not available at level ${lv} yet.`);
  }
  return out;
}

// Paint the warnings into the banner beneath the totals toggles. Called from
// recompute() and on any level change; hidden entirely when there's nothing
// to warn about.
function renderEndgameWarnings() {
  const el = $("endgame-warn");
  if (!el) return;
  const w = endgameWarnings();
  el.classList.toggle("hidden", !w.length);
  el.innerHTML = w.map(m => `<div class="warn-row">${escHtml(m)}</div>`).join("");
}

// Nearest walk-step index for a given game level (first step at/after it, else the last).
function _stepIndexForLevel(level) {
  const steps = LEVELING_STEPS || [];
  for (let i = 0; i < steps.length; i++) if ((steps[i].level || 0) >= level) return i;
  return Math.max(0, steps.length - 1);
}

// The re-sync banner shown atop each level step for a character being leveled. `stepLevel`
// is the level of the step currently on screen; build.level_reached is where the player
// actually is in-game (what they last told us).
function levelSyncBanner(stepLevel) {
  if (!isLevelingBuild()) return "";
  const tracked = build.level_reached || null;
  const gap = tracked ? Math.abs((stepLevel || tracked) - tracked) : 0;
  const behind = tracked && (stepLevel || 0) < tracked - SYNC_DRIFT_LEVELS;
  let msg;
  if (!tracked) {
    msg = `📍 <strong>What level are you in-game right now?</strong> Tell me and I'll jump the walk to match — so every suggestion is a choice you can actually make at your level.`;
  } else if (behind) {
    msg = `📍 I have you at <strong>level ${tracked}</strong>, but you're viewing level ${stepLevel}. Update me whenever you level so I never suggest a pick you've already passed.`;
  } else {
    msg = `📍 Tracking you at <strong>level ${tracked}</strong>. Leveled up? Update it so we stay in step.`;
  }
  const input = `<span class="lvl-sync-set">I'm now level `
    + `<input type="number" min="1" max="50" class="lvl-sync-input" value="${tracked || ''}" `
    + `onchange="setCurrentLevel(this.value)" onkeydown="if(event.key==='Enter'){setCurrentLevel(this.value)}"> `
    + `<button class="linkbtn" onclick="setCurrentLevel(this.previousElementSibling.value)">sync ▶</button></span>`;
  // Absence / drift warning + the catch-up import path (point: framing the in-game .txt
  // import as re-sync). Shown when the tool and the player are several levels apart.
  const drifted = tracked && gap >= SYNC_DRIFT_LEVELS;
  const resync = drifted
    ? `<div class="lvl-sync-warn">⚠️ We're about <strong>${gap} levels apart</strong>. If you've been playing without me for a while, the fastest way to get back in step is to `
      + `<button class="linkbtn" onclick="resyncFromGame()">import your character from the game</button> `
      + `— save it to a text file in-game and I'll re-read exactly where you are (powers, slots, level) and pick the walk up from there.`
      + `<div class="lvl-sync-exemplar">🕰️ Outran the content getting here? No harm done — <strong>Ouroboros flashback</strong> lets you exemplar back down and experience the arcs you skipped (and learn your powers one at a time, the way the game teaches itself).</div>`
      + `</div>`
    : "";
  return `<div class="lvl-sync">${msg}<div class="lvl-sync-row">${input}</div>${resync}</div>`;
}

// Player tells us their real in-game level → record it, jump the walk to that level, and
// autosave picks up the new level_reached. If it's a big jump forward from the last sync,
// the drift warning (above) will surface the catch-up import on the next render.
window.setCurrentLevel = function (val) {
  const n = Math.max(1, Math.min(50, parseInt(val, 10) || 0));
  if (!n) return;
  build.level_reached = n;
  renderEndgameWarnings();   // the warning depends on the tracked level
  if (LEVELING_STEPS && LEVELING_STEPS.length) { LEVEL_STEP_I = _stepIndexForLevel(n); }
  renderLevelStep();
  autoSaveTick();   // persist the new level immediately so Continue shows ⏳ L{n}/50
};

// "Import your character from the game" — the re-sync path for a leveler who's been away.
// Reuses the existing in-game import entry; framed as a catch-up rather than a fresh import.
window.resyncFromGame = function () {
  const f = $("import-file");
  if (f) f.click();
  const s = $("gen-status");
  if (s) s.textContent = "📥 Re-syncing: pick the character file you exported in-game and I'll pick up exactly where you are.";
};

// Powers you could legally take AT THIS LEVEL instead of the guided pick — from your own
// powersets, available by this level, and not already taken elsewhere in the plan.
function _altPowersForLevel(level, currentFullName) {
  const picked = new Set(build.powers.map(p => p.full_name));
  const out = [];
  for (const ps of chosenPowersets()) {
    // VEAT branch sets only exist after the level-24 respec — before that the game
    // won't allow their powers, so don't offer them as alternatives.
    if (LEVELING_EAT_TYPE === "veat" && level < 24 && VEAT_BASE_SET[ps]) continue;
    for (const p of (POWERS_CACHE[ps] || [])) {
      if (!p.slottable) continue;
      if ((p.level_available || 1) > level) continue;   // not available at this level yet
      if (p.full_name === currentFullName || picked.has(p.full_name)) continue;
      out.push({ full_name: p.full_name,
                 display_name: p.display_name || p.full_name.split(".").pop().replace(/_/g, " "),
                 powerset: ps.split(".").pop().replace(/_/g, " ") });
    }
  }
  return out.sort((a, b) => a.display_name.localeCompare(b.display_name));
}
// Swap the guided pick at a step for the player's own choice, re-walk the plan, and land back
// on the same step so they immediately see what their pick contributes.
window.swapLevelPick = async function (stepIndex, oldFullName, newFullName) {
  if (!newFullName) return;
  const step = LEVELING_STEPS[stepIndex];
  let np = null, nps = null;
  for (const ps of chosenPowersets()) {
    const f = (POWERS_CACHE[ps] || []).find(x => x.full_name === newFullName);
    if (f) { np = f; nps = ps; break; }
  }
  if (!np) return;
  recordEdit();
  const idx = build.powers.findIndex(p => p.full_name === oldFullName);
  const pickLevel = idx >= 0 ? (build.powers[idx].pick_level || step.level) : step.level;
  const swapped = {
    full_name: np.full_name, display_name: np.display_name, powerset_full_name: nps,
    accepted_set_categories: np.accepted_set_categories || [],
    accepted_set_category_ids: np.accepted_set_category_ids || [],
    power_type: np.power_type, include_in_totals: np.power_type === 1 || np.power_type === 2,
    pick_level: pickLevel, level_available: np.level_available, slotCount: 1, slots: [null],
  };
  if (idx >= 0) build.powers[idx] = swapped; else build.powers.push(swapped);
  LEVELING_DEVIATED = true; LAST_REFIT = "";   // off the suggested plan → offer an adapt; old re-fit is now stale
  renderPowers(); recompute();
  await openLevelStepper();                    // re-walk the plan with your pick in place
  LEVEL_STEP_I = Math.min(stepIndex, (LEVELING_STEPS || []).length - 1);
  renderLevelStep();
};

// Support roles kill slowly SOLO (no team to finish) — flag it honestly on a re-fit.
const _SUPPORT_ROLES = new Set(["buffer", "healer", "support", "controller", "control", "debuffer"]);
function _wizGoal() {
  const g = (id, ...fallbacks) => ($(id) && $(id).value) || fallbacks.find(Boolean) || "";
  return {
    role: g("wiz-role", $("preset-role") && $("preset-role").value, "damage"),
    content: g("wiz-content", $("preset-content") && $("preset-content").value, "general"),
    exposure: ($("wiz-exposure") && $("wiz-exposure").value) || build._exposure || null,
    travel: ($("wiz-travel") && $("wiz-travel").value) || "teleport",
  };
}
// 2b — the DOWNSTREAM horizon: re-solve the level-50 slotting around the picks you've actually
// made, and show what your end-game becomes (+ an honest solo-support heads-up).
window.refitEndgame = async function () {
  const out = $("lvl-endgame"); if (!out) return;
  out.innerHTML = "<p class='muted small'>Re-fitting your level-50 build around your picks…</p>";
  const goal = _wizGoal();
  const sol = await api("/build/solve", postJson({
    archetype: build.archetype, powers: build.powers, content: goal.content, role: goal.role, preserve: false }));
  if (!sol || !sol.ok) { out.innerHTML = "<p class='muted small'>Couldn't re-fit — set a Content goal and try again.</p>"; return; }
  build.powers = sol.powers; renderPowers(); recompute();
  const t = sol.totals || {};
  const g = p => { const v = p.reduce((a, k) => (a ? a[k] : undefined), t); return typeof v === "number" ? v : ((v && v.value) || 0); };
  const stat = (lab, val) => `<span class="lvl-stat">${lab} <b>${val}</b></span>`;
  const cells = [stat("Recharge", g(["recharge"]) + "%"), stat("S/L def", g(["defense", "Smashing"]) + "%"),
    stat("S/L res", g(["resistance", "Smashing"]) + "%"), stat("Ranged def", g(["defense", "Ranged"]) + "%"),
    stat("ST DPS", Math.round((t.offense && t.offense.st_dps) || 0)),
    stat("AoE DPS", Math.round((t.offense && t.offense.aoe_dps) || 0))].join(" ");
  const solo = goal.content === "general" || goal.content === "av";
  const note = (solo && _SUPPORT_ROLES.has(goal.role))
    ? `<div class="disc-note warn">⚠ Solo + support — these ATs kill slowly alone. Lean on your secondary/epic damage + procs so you can finish fights yourself (or a respec can shift you toward more personal damage).</div>` : "";
  LAST_REFIT = `<div class="lvl-endgame-box"><div class="muted small">✓ Re-fit around your choices — your level-50 now:</div>`
    + `<div class="lvl-endgame-stats">${cells}</div>${note}`
    + `<div class="muted small">This is your plan now — keep stepping, I'll keep suggesting from here.</div></div>`;
  LEVELING_DEVIATED = false;               // your choices ARE the plan now — back to calm advisory
  const keepStep = LEVEL_STEP_I;
  await openLevelStepper();                // re-walk toward the NEW end-game fit
  LEVEL_STEP_I = Math.min(keepStep, (LEVELING_STEPS || []).length - 1);
  renderLevelStep();                       // renders LAST_REFIT + keeps the walk going
};
// Discard deviations and rebuild the solver's optimal plan for this AT + powersets.
window.resetToOptimal = async function () {
  if (!confirm("Reset to the solver's optimal plan?\n\nThis replaces your custom picks with the recommended end-game for your archetype and powersets. Your saved character isn't touched — this only changes the current plan.")) return;
  const out = $("lvl-endgame"); if (out) out.innerHTML = "<p class='muted small'>Rebuilding the optimal plan…</p>";
  const goal = _wizGoal();
  recordEdit();
  const ap = await api("/build/autopick", postJson({
    archetype: build.archetype, primary: build.primary, secondary: build.secondary,
    role: goal.role, content: goal.content, exposure: goal.exposure, travel: goal.travel,
    custom_targets: build._custom_targets || null }));
  if (!ap || !ap.ok) { if (out) out.innerHTML = "<p class='muted small'>Couldn't rebuild right now.</p>"; return; }
  const sol = await api("/build/solve", postJson({
    archetype: build.archetype, powers: ap.powers, content: goal.content, role: goal.role, preserve: false }));
  build.powers = (sol && sol.ok) ? sol.powers : ap.powers;
  LEVELING_DEVIATED = false; LAST_REFIT = "";   // back on the suggested plan
  // v34 item 5 (ENTRY-POINT CLASS, Joel's walk-2 defect 2): EVERY level-50
  // generation path preselects the standard accolades and states it — not just
  // the wizard's Build. This is the reset lesson verbatim: the rule is about
  // the CLASS of entry point, and wiring one member is how the last one bit us.
  await preselectStandardAccolades();
  renderPowers(); recompute();
  await openLevelStepper(); LEVEL_STEP_I = 0; renderLevelStep();
};
window.levelStep = (d) => {
  LEVEL_STEP_I = Math.max(0, Math.min(LEVELING_STEPS.length - 1, LEVEL_STEP_I + d));
  renderLevelStep();
};

window.pickDiscovery = async function (at) {
  $("wiz-at").value = at;
  await wizLoadPowersets();
  // ONE-COPY RULE: the aim answers already ARE wiz-role/content/exposure (the
  // recommender read them from there), tagged "your pick" by their own change
  // handlers — nothing to copy. Travel stays unanswered on purpose: it is
  // always an explicit pick. The recommender stays available for a re-find;
  // only its result cards clear once one is chosen.
  wizGateBuild();
  wizUpdateHint();
  wizExplain(null);
  $("disc-results").innerHTML = "";
  $("wiz-at").scrollIntoView({ behavior: "smooth", block: "center" });
};

// Show the tool's read of role × content × exposure, so the user sees how it's
// interpreting the goal — esp. that a SUPPORT character in a fire farm is a team /
// dual-box mule, never a soloist.
function wizInterpret(role, content, exposure) {
  const support = role === "buffer" || role === "healer";
  const frontish = exposure === "front";
  if (content === "fire_farm") {
    return support
      ? "→ As support in a fire farm you're on a team or a dual-box mule for the farmer — I'll build for survival + buff uptime"
        + (frontish ? " (and you're in the spawn, so survival to the fire/S-L caps)." : ", staying at the edge.")
      : "→ You're the farmer — AoE clear plus survival to the fire & S/L caps.";
  }
  if (content === "itrial" || content === "team")
    return support ? "→ League/team support — group buffs + a survival cushion for spike & debuff content."
                   : "→ League/team — AoE clear + survival for +3/+4 content.";
  if (content === "av") return "→ Hard single targets — sustained single-target DPS + survival through long fights.";
  return support ? "→ General support — survivable buffs/heals for everyday content."
                 : "→ General — balanced damage + survival.";
}
function wizUpdateHint() {
  const h = $("wiz-hint");
  if (!h) return;
  // No invented reading of unanswered questions (no-defaults ruling).
  h.textContent = ($("wiz-role").value && $("wiz-content").value)
    ? wizInterpret($("wiz-role").value, $("wiz-content").value, $("wiz-exposure").value)
    : "";
}

// "How do you play" explainer (ideas.md 2026-07-08): every choice pops a DETAILED,
// TAILORED explanation (specific to the chosen AT + primary + secondary), and a
// summary panel shows what the combined answers make the planner actually chase.
// Server-derived from the same presets the solve uses, so it never drifts.
let WIZ_POP_KEY = null;      // which choice's pop-up is open (refreshes on char change)
let WIZ_EXPLAIN_SEQ = 0;     // stale-response guard
async function wizExplain(changedKey) {
  const at = $("wiz-at") && $("wiz-at").value;
  // NO DEFAULTS, fixed scope (release-gate bug): a question the user JUST
  // answered always pops its explainer — explaining a given answer invents
  // nothing. The server returns null for every UNANSWERED question, and the
  // summary asserts nothing until Role AND Content exist (empty text = hidden).
  // The old whole-function gate on Role+Content silenced the Role and
  // Fight-from pop-ups on every first pass — they sit BEFORE Mostly-in.
  const anyAnswered = ["wiz-role", "wiz-content", "wiz-exposure", "wiz-travel", "wiz-form"]
    .some(id => $(id) && $(id).value);
  if (!anyAnswered) {
    const pop = $("wiz-pop"), sum = $("wiz-summary");
    if (pop) pop.classList.add("hidden");
    if (sum) sum.classList.add("hidden");
    return;
  }
  const seq = ++WIZ_EXPLAIN_SEQ;
  const r = await api("/build/explain_intent", postJson({
    archetype: at || null,
    primary: ($("wiz-primary") && $("wiz-primary").value) || null,
    secondary: ($("wiz-secondary") && $("wiz-secondary").value) || null,
    // RAW values only — inventing "none"/"flex" here made the pop-up and summary
    // assert answers nobody gave (the travel-carryover field report). The server
    // says "not chosen yet" for whatever is missing.
    role: ($("wiz-role") && $("wiz-role").value) || null,
    content: ($("wiz-content") && $("wiz-content").value) || null,
    exposure: ($("wiz-exposure") && $("wiz-exposure").value) || null,
    travel: ($("wiz-travel") && $("wiz-travel").value) || null,
    form: ($("wiz-form") && $("wiz-form").value) || null,
  })).catch(() => null);
  if (!r || !r.ok || seq !== WIZ_EXPLAIN_SEQ) return;
  if (changedKey) WIZ_POP_KEY = changedKey;
  const pop = $("wiz-pop");
  const d = WIZ_POP_KEY && r[WIZ_POP_KEY];
  if (pop && d) {
    const tailorNote = (at && $("wiz-primary").value && $("wiz-secondary").value)
      ? "" : `<div class="muted small" style="margin-top:6px">Pick your archetype and
              powersets in step 1 and this explanation tailors itself to them.</div>`;
    pop.innerHTML = `<button class="wiz-pop-x" title="dismiss"
        onclick="WIZ_POP_KEY=null;this.parentElement.classList.add('hidden')">✕</button>`
      + `<div class="wiz-pop-title">${escHtml(d.title || "")}</div>`
      + `<div class="wiz-pop-text">${escHtml(d.text || "")}</div>` + tailorNote;
    pop.classList.remove("hidden");
  }
  const sum = $("wiz-summary"), s = r.summary || {};
  if (sum) {
    // The summary asserts a playstyle only once all four questions are answered;
    // partial answers get a progress line instead of an invented plan.
    const sumTitle = wizAnswered()
      ? "📋 Your play style — what the planner will chase"
      : "📋 Partial answers — finish the four questions to lock in the plan";
    sum.innerHTML = `<div class="wiz-sum-title">${sumTitle}</div>`
      + `<div class="wiz-sum-text">${escHtml(s.text || "")}</div>`
      + `<div class="wiz-sum-tgts">${(s.targets || [])
            .map(t => `<span class="wiz-tgt">${escHtml(t)}</span>`).join("")}</div>`
      // Joel's ruling 2: the targets editor opens from where the target
      // chips display — presets stay the offered path; custom is your act.
      + (wizAnswered() ? `<button class="mini" style="margin-top:6px"
            onclick="openTargetsEditor()">Customize build targets…</button>` : "");
    sum.classList.toggle("hidden", !s.text);
  }
}

async function wizLoadPowersets() {
  const at = $("wiz-at").value, pri = $("wiz-primary"), sec = $("wiz-secondary");
  pri.innerHTML = "<option value=''>— primary set —</option>";
  sec.innerHTML = "<option value=''>— secondary set —</option>";
  pri.disabled = sec.disabled = !at;
  if (!at) return;
  const ps = await api(`/powersets/${at}`);
  for (const p of (ps.primary || [])) pri.add(new Option(p.display_name, p.full_name));
  for (const p of (ps.secondary || [])) sec.add(new Option(p.display_name, p.full_name));
  // Single-path ATs (Kheldians): the only primary/secondary select themselves,
  // and innate flight/teleport means no extra travel power by default.
  if ((ps.primary || []).length === 1) pri.selectedIndex = 1;
  if ((ps.secondary || []).length === 1) sec.selectedIndex = 1;
  pri.onchange = () => pairVeatSets(pri, sec, VEAT_PAIR);
  sec.onchange = () => pairVeatSets(sec, pri, VEAT_PAIR_REV);
  // Travel is never auto-set (design ruling: endgame entry can REQUIRE specific
  // travel — BAF/Lambda enter only by Flight or Teleport). The tailored pop-up
  // teaches Kheldians their innate flight/TP; the pick stays theirs.
}

async function buildRespec() {
  const at = $("wiz-at").value, pri = $("wiz-primary").value, sec = $("wiz-secondary").value;
  if (!at || !pri || !sec) {
    const missing = [], names = [];
    if (!at) { missing.push($("wiz-at")); names.push("archetype"); }
    if (!pri) { missing.push($("wiz-primary")); names.push("primary set"); }
    if (!sec) { missing.push($("wiz-secondary")); names.push("secondary set"); }
    wizFlagMissing(missing, `Pick your ${names.join(" and ")} in step 1 — highlighted in red above.`);
    return;
  }
  // NO DEFAULTS (design ruling): the button is gated, and this guard backs it up —
  // the planner never invents an answer to "how do you play."
  if (!wizAnswered()) { wizGateBuild(); return; }
  const role = $("wiz-role").value;
  const content = $("wiz-content").value;
  const exposure = $("wiz-exposure").value, travel = $("wiz-travel").value;
  // Kheldian FORM route: "human" IS the classic 4-part champion (no form tag);
  // dwarf/nova serve that form's own champion as the base to build under.
  const form = _wizIsKheldian() && $("wiz-form").value !== "human"
    ? $("wiz-form").value : null;
  build._exposure = exposure;   // carries into the solve so the def vector matches
  build._travel = travel;       // remembered so reopening restores YOUR answer
  $("wiz-build").disabled = true;
  // Live elapsed pulse across BOTH stages (autopick + solve) — the field
  // report's "30 seconds of silence" was this line sitting static while a
  // hard combo solved (Fire/Icy Dominator measured 13s server-side; the
  // solver's exact math is the cost, the silence was the defect).
  const stopWizPulse = startSolvePulse($("wiz-status"),
    "Choosing powers + solving the slotting");
  try {
    await applyImportedBuild({ archetype: at, primary: pri, secondary: sec, pools: [], incarnates: {}, powers: [] });
    const ap = await api("/build/autopick", postJson({ archetype: at, primary: pri, secondary: sec, role, content, exposure, travel, form,
      custom_targets: build._custom_targets || null }));
    if (!ap || !ap.ok) { $("wiz-status").textContent = (ap && ap.error) || "Auto-pick failed."; return; }
    if (ap.custom_note) {
      const _o = $("ai-response");
      if (_o) { _o.classList.remove("muted"); _o.innerHTML = renderMarkdown(ap.custom_note); }
    }
    build.powers = ap.powers; build.imported = false;
    // Autopick chose pool + epic powers — sync the top-of-page dropdowns to them (the empty-powers
    // applyImportedBuild call above couldn't, since the powers didn't exist yet).
    await syncPoolsEpicFromPowers(ap.powers);
    if ($("preset-content")) $("preset-content").value = content;
    if ($("preset-role")) $("preset-role").value = role;
    // v34 item 5: a generated level-50 build ASSUMES the standard accolades —
    // the same four every community reference build carries, and the same four
    // the farm presets already assume on the scoring side. Choice doctrine: the
    // assumption is VISIBLE (they render checked in the panel, and the build
    // states it) and REVERSIBLE (untick any of them and the totals follow).
    await preselectStandardAccolades();
    renderPowers();
    // The wizard ALREADY gathered + showed the role/content/exposure intent, so skip the
    // confirm gate (its button would render behind this modal and hang the flow).
    await solveSlotting(null, { skipConfirm: true });
    // The first-meeting greet keys on "a leveling build WAS BUILT", not on which
    // button dismisses the wizard afterward — Joel's gaming-box report: leave
    // the wizard any way other than the two reveal buttons and the greeting
    // never fired. closeRespecWizard consumes this flag on ANY exit.
    _WIZ_BUILT_LEVELING = isLevelingBuild();
    $("wiz-result").classList.remove("hidden");
    // 0.12.20 eyeball fix (Joel: clicking Build looked like nothing happened —
    // the result rendered below the fold INSIDE this pop-up, with the pop-up
    // itself sitting in front of the build): an UNMISSABLE reveal button
    // leads the result, and the result scrolls itself into view. One click
    // dismisses the pop-up and lands on the build.
    $("wiz-result").innerHTML = `<button id="wiz-reveal" class="wiz-reveal-cta">`
      + `⬇&nbsp; Your build is ready — click to see it &nbsp;⬇</button>`
      + `<strong>✓ Your ${ap.count}-power kit is ready.</strong>`
      // v34 item 5: state the accolade assumption ON the build — visible and
      // reversible, never silent (choice doctrine).
      + `<p class="acc-assumed-note">🏅 These numbers assume the four standard accolades`
      + `${build._accoladeHp ? ` (+${build._accoladeHp} HP)` : ""} — the ones most level-50s have. `
      + `They're ticked in the Accolades panel below the powers; untick any you don't have and the totals follow.</p>`
      + `<p class="muted small">Powers chosen, slotting optimized, and incarnates recommended for your goal. `
      + `Travel + survival are taken early so they survive exemplaring into old Task Forces. `
      + `Open the full build to review caps, DPS, and per-slot enhancements — and tweak anything, or 💾 Save it.</p>`
      + `<p class="muted small">💡 Crafting tip: slot your sets as <strong>Attuned</strong> — they scale to any level and keep their set bonuses when you exemplar down for low-level content.</p>`
      + ((content === "itrial" && (travel === "super_speed" || travel === "super_jump"))
          ? `<p class="lvl-tip">🚀 <strong>iTrial access:</strong> some trials (BAF, Lambda) can only be entered by <strong>Flight or Teleport</strong> — you can't run in. With ${travel === "super_speed" ? "Super Speed" : "Super Jump"} you'll want a P2W <strong>jet pack</strong> on hand. Switching travel to Fly/Teleport fixes it but costs an extra pool (Super Speed shares its pool with Hasten; Fly/Teleport don't).</p>`
          : "")
      + `<div class="wiz-result-btns"><button id="wiz-step" class="secondary" style="width:auto">▶ Walk it step-by-step</button>`
      + `<button id="wiz-journey" class="secondary" style="width:auto">🗺️ See the journey</button>`
      + `<button id="wiz-open" class="solve-btn" style="width:auto">Open the full build →</button></div>`
      + `<div id="wiz-plan-out"></div>`;
    $("wiz-plan-out").innerHTML = levelingPlanHtml();   // show the full in-game respec order up front
    const _reveal = () => {
      closeRespecWizard();      // any-exit seam stays as the backstop
      $("builder").scrollIntoView({ behavior: "smooth", block: "start" });
    };
    // THE TRIGGER IS THE BUILD FINISHING, not the wizard exit (Joel's fourth
    // report finally isolated it: he builds, then WAITS for the promised road
    // — no exit ever happens). A 1-50 start "starts ON": the road opens right
    // now, over the wizard; closing it lands on the result underneath.
    // Called unconditionally: maybeAutoOpenJourney applies the SAME gates and
    // now reports which one stopped it, so there is no second place to fail
    // silently. The any-exit backstop arms only if this open did NOT happen.
    _WIZ_BUILT_LEVELING = !maybeAutoOpenJourney();
    $("wiz-reveal").addEventListener("click", _reveal);
    $("wiz-open").addEventListener("click", _reveal);
    $("wiz-step").addEventListener("click", openLevelStepper);
    $("wiz-journey").addEventListener("click", openJourneyView);
    // The click's consequence must be ON SCREEN. scrollIntoView proved
    // unreliable here (the wizard-box is a scroll container inside a fixed
    // modal and never moved) — scroll the container itself, measured.
    const _box = $("wiz-reveal").closest(".wizard-box");
    if (_box) {
      const _delta = $("wiz-reveal").getBoundingClientRect().top
        - _box.getBoundingClientRect().top;
      // instant, not smooth: smooth scrollTo silently no-ops on this
      // container (measured — scrollTop stayed 0 even standalone), and an
      // unmissable reveal that sometimes doesn't reveal is a false no-op
      // all over again.
      _box.scrollTo({ top: _box.scrollTop + _delta - 60 });
    }
    stopWizPulse();
    $("wiz-status").textContent = "";
  } finally { stopWizPulse(); $("wiz-build").disabled = false; }
}

// Natural roles per archetype (from /archetypes): picking outside them is a DELIBERATE
// off-role build (Offender, tankermind…) — warn loudly so the user owns the choice.
let NATURAL_ROLES = {};
const ROLE_LABELS = { controller: "Controller / Lockdown", debuffer: "Debuffer",
                     buffer: "Buffer / Support", healer: "Healer",
                     damage: "Damage dealer", tank: "Tank / Survivor",
                     mixed: "Mixed role / Generalist" };

let SET_ROLE_EXTENSIONS = {};
// The user's answer to "if we split your focus, what percentage on each role?" —
// {primaryRole, secondaryRole, pct} (pct = % on the primary). Null until they answer.
let roleFocus = { secondary: "", pct: 100 };

function roleMixPayload() {
  const roleSel = $("preset-role");
  const r = roleSel && roleSel.value;
  if (!r || !roleFocus.secondary || roleFocus.secondary === r || roleFocus.pct >= 100)
    return null;
  return { [r]: roleFocus.pct, [roleFocus.secondary]: 100 - roleFocus.pct };
}

function renderRoleFocusSplit() {
  // When the AT + chosen sets legitimize MORE than one role, don't guess the player's
  // intent — ASK: "how do you want to split your focus?" (e.g. an MM with Empathy:
  // henchmen support vs team healing).
  const roleSel = $("preset-role");
  if (!roleSel) return;
  let box = $("role-focus-split");
  if (!box) {
    box = document.createElement("div");
    box.id = "role-focus-split";
    box.style.cssText = "margin:6px 0;";
    ($("off-role-warning") || roleSel.closest("label") || roleSel)
      .insertAdjacentElement("afterend", box);
  }
  const at = build.archetype;
  const r = ({ control: "controller", support: "buffer" })[roleSel.value] || roleSel.value;
  const legit = [...new Set([...(NATURAL_ROLES[at] || []), ...rolesFromSets()])];
  const others = legit.filter(x => x !== r);
  if (!(at && r && others.length)) { box.innerHTML = ""; roleFocus = { secondary: "", pct: 100 }; return; }
  const opts = others.map(o =>
    `<option value="${o}" ${roleFocus.secondary === o ? "selected" : ""}>${ROLE_LABELS[o] || o}</option>`).join("");
  box.innerHTML =
    `<div class="muted small">Your picks support more than one role — <b>how do you want to split your focus?</b></div>
     <label class="small">${ROLE_LABELS[r] || r} <b><span id="rf-pct">${roleFocus.pct}</span>%</b>
       <input type="range" id="rf-slider" min="50" max="100" step="5" value="${roleFocus.pct}">
       <select id="rf-secondary"><option value="">— all-in (100%) —</option>${opts}</select>
       <span id="rf-note" class="muted small"></span></label>`;
  const upd = () => {
    roleFocus.pct = +$("rf-slider").value;
    roleFocus.secondary = $("rf-secondary").value;
    $("rf-pct").textContent = roleFocus.pct;
    $("rf-note").textContent = roleFocus.secondary && roleFocus.pct < 100
      ? `→ ${roleFocus.pct}% ${ROLE_LABELS[r] || r} / ${100 - roleFocus.pct}% ${ROLE_LABELS[roleFocus.secondary]}`
      : "(single-role focus)";
  };
  $("rf-slider").addEventListener("input", upd);
  $("rf-secondary").addEventListener("change", upd);
  upd();
}

function rolesFromSets() {
  // Roles legitimized by the CHOSEN powersets — a Controller with Poison plays Debuffer,
  // an MM with Empathy heals (his own henchmen are a team). Control primaries ⇒ controller.
  const out = [];
  for (const ps of [build.primary, build.secondary]) {
    if (!ps) continue;
    const base = ps.split(".").pop();
    (SET_ROLE_EXTENSIONS[base] || []).forEach(r => { if (!out.includes(r)) out.push(r); });
    if (ps.split(".")[0].endsWith("_Control") && !out.includes("controller"))
      out.push("controller");
  }
  return out;
}

function updateOffRoleWarning() {
  const roleSel = $("preset-role");
  if (!roleSel) return;
  let warn = $("off-role-warning");
  if (!warn) {
    warn = document.createElement("div");
    warn.id = "off-role-warning";
    warn.style.cssText = "font-weight:bold;margin:4px 0;";
    const host = roleSel.closest("label") || roleSel;
    host.insertAdjacentElement("afterend", warn);
  }
  const at = build.archetype;
  const role = ({ control: "controller", support: "buffer" })[roleSel.value] || roleSel.value;
  const nat = NATURAL_ROLES[at] || [];
  warn.textContent = ""; warn.style.color = "";
  if (!(at && role && nat.length) || nat.includes(role)) return;
  const atName = (($("sel-archetype") || {}).selectedOptions || [{}])[0].textContent
    || "this archetype";
  const ext = rolesFromSets();
  if (ext.includes(role)) {
    const srcs = [build.primary, build.secondary].filter(ps => ps &&
      ((SET_ROLE_EXTENSIONS[ps.split(".").pop()] || []).includes(role)
        || (role === "controller" && ps.split(".")[0].endsWith("_Control"))))
      .map(ps => ps.split(".").pop().replace(/_/g, " "));
    warn.style.color = "#7ec8ff";
    warn.textContent = `◆ ROLE EXTENSION: ${ROLE_LABELS[role] || role} isn't a ` +
      `${atName}'s official role, but your ${srcs.join(" / ") || "powerset"} choice ` +
      `makes it a legitimate multi-role play — deliberate diversity, still role-based.`;
  } else {
    warn.style.color = "#ffb347";
    warn.textContent = `⚠ OFF-ROLE CHOICE: a ${atName}'s natural role is ` +
      `${nat.map(n => ROLE_LABELS[n] || n).join(" / ")}, and none of your powersets ` +
      `extend to ${ROLE_LABELS[role] || role}. The optimizer will honor it — a ` +
      `deliberate off-role character, and that's the choice you're making.`;
  }
}

function refreshRoleUI() { updateOffRoleWarning(); renderRoleFocusSplit(); }


// ── ALIGNMENT (Hero Companion reskin): the app has an alignment like any CoH character.
// Hero = Paragon blue & gold, Villain = Rogue Isles crimson. Persisted per browser.
function applyAlignment(al) {
  document.body.classList.remove("theme-hero", "theme-villain");
  document.body.classList.add(al === "villain" ? "theme-villain" : "theme-hero");
  const name = al === "villain" ? "Villain Companion" : "Hero Companion";
  const glyph = al === "villain" ? "🦹" : "🦸";
  const tag = al === "villain" ? "your Rogue Isles accomplice" : "your City of Heroes sidekick";
  if ($("app-name")) $("app-name").textContent = name;
  if ($("app-glyph")) $("app-glyph").textContent = glyph;
  const tagEl = document.querySelector(".app-tag"); if (tagEl) tagEl.textContent = tag;
  const btn = $("alignment-btn");
  if (btn) {
    btn.textContent = al === "villain" ? "🦸" : "🦹";
    btn.title = al === "villain" ? "Go Hero — reskin the whole app" : "Go Villain — reskin the whole app";
  }
  document.title = name + " — City of Heroes";
  document.querySelectorAll(".align-card").forEach(c =>
    c.classList.toggle("on", c.dataset.align === al));
  try { localStorage.setItem("cohAlignment", al); } catch (e) {}
  // Accolades gate on the character's alignment. Switching sides means this is
  // now a different-alignment character, so drop the accolades it can no longer
  // hold and assume the new side's standard set (auto-pick, Joel's intent), then
  // recompute (re-gates totals + re-renders the panel greying).
  if (typeof build !== "undefined" && build.powers && build.powers.length
      && ACCOLADES_ROWS) {
    for (const a of ACCOLADES_ROWS) {
      if (a.alignment && a.alignment !== al) ACCOLADES_CHECKED.delete(a.key);
      else if (a.standard_assumed && a.alignment === al) ACCOLADES_CHECKED.add(a.key);
    }
    try { recompute(); } catch (e) {}
  }
}
window.toggleAlignment = function () {
  const cur = localStorage.getItem("cohAlignment") || "hero";
  applyAlignment(cur === "hero" ? "villain" : "hero");
};


// VEAT BRANCH PAIRING: a Soldier/Widow makes ONE choice — the branch — not two independent
// set picks (master corpus: Bane↔Bane Training, Crab↔Crab Training, Night Widow↔Widow
// Teamwork; cross-branch combos are impossible in game). Picking either side selects its mate.
const VEAT_PAIR = {
  Arachnos_Soldier: "Training_and_Gadgets", Bane_Spider_Soldier: "Bane_Spider_Training",
  Crab_Spider_Soldier: "Crab_Spider_Training",
  Widow_Training: "Teamwork", Night_Widow_Training: "Widow_Teamwork",
  Fortunata_Training: "Fortunata_Teamwork",
};
const VEAT_PAIR_REV = Object.fromEntries(Object.entries(VEAT_PAIR).map(([k, v]) => [v, k]));

function pairVeatSets(changedSel, otherSel, map) {
  const base = (changedSel.value || "").split(".").pop();
  const mate = map[base];
  if (!mate) return false;
  const opt = [...otherSel.options].find(o => (o.value || "").split(".").pop() === mate);
  if (opt && otherSel.value !== opt.value) {
    otherSel.value = opt.value;
    otherSel.dispatchEvent(new Event("change"));
  }
  return !!opt;
}

// ── Project home: versions, bug reports, champion submissions, update check ──
// Everything here is USER-CLICK only — the app never sends anything on its own.
let META = null;
let AI_ON = true;   // flipped by /health; standalone builds report ai_enabled:false
const _urlReady = (u) => !!u && !u.includes("REPLACE-ME");

// Which app.js did THIS browser actually load? The URL carries the server's
// cache-busting token, so a stale cached script shows an old token here even
// when the server reports a new commit — the two halves of "is this fresh".
function jsAssetToken() {
  const s = document.querySelector('script[src*="app.js"]');
  return s ? `app.js ${new URL(s.src, location.href).searchParams.get("v") || "(untokenized)"}`
           : "app.js (not found)";
}

async function loadMeta() {
  try { META = await api("/meta"); } catch { META = null; }
  const f = $("app-version-foot");
  if (f && META) f.textContent = `v${META.app_version} · model v${META.model_version}`;
  // Header leads with the APP version (the number users actually care about);
  // the Mids data build lives in the About dialog it opens. (UX item 2026-07-16)
  const hv = $("app-ver");
  if (hv && META) {
    // Build stamp: the server's commit next to the version, so "which code is
    // this tab running" is answerable by eye. Only source checkouts have a
    // commit — installed copies just show the version, as before.
    hv.textContent = META.build_commit
      ? `v${META.app_version} · ${META.build_commit} ⓘ` : `v${META.app_version} ⓘ`;
    hv.title = `server ${META.build_commit || "(packaged)"} · ${jsAssetToken()}`;
    hv.hidden = false;
    hv.onclick = showAbout;
  }
  // Running from source = the dev copy. Badge it so it can never be mistaken
  // for the installed app when both are open (they serve different ports).
  if (META && !META.packaged && $("app-name") && !$("dev-badge")) {
    $("app-name").insertAdjacentHTML("afterend",
      ` <span id="dev-badge" title="Development copy running from source (port ${location.port || 80}) — the installed app is separate">DEV</span>`);
  }
  initUpdateFlow();
}

// ── About dialog (header version click, UX item 2026-07-16) ─────────────────
// Display-only. Explains the version vocabulary the header used to leave
// unexplained; every number comes from /meta so it can never drift from the
// running app.
function showAbout() {
  if (!META) return;
  const urls = META.urls || {};
  const link = (u, label) => _urlReady(u)
    ? `<a href="${escHtml(u)}" target="_blank" rel="noopener">${escHtml(label)}</a>` : "";
  const links = [
    link(urls.forum_thread, "Forum thread"),
    link(urls.releases, "Releases"),
    link(urls.pulse_boards, "Pulse Boards"),
    link(urls.project_home, "GitHub"),
    `<a href="/docs/credits" target="_blank">Credits</a>`,
  ].filter(Boolean).join(" · ");
  const roster = META.champion_count
    ? `<div class="about-row"><b>Champions</b><span>${META.champion_count} certified
       reference builds, each converged and re-verified whenever the model changes.</span></div>` : "";
  $("about-body").innerHTML = `
    <p>Hero Companion designs, optimizes, and levels City of Heroes characters
    with you. It is free and noncommercial, forever.</p>
    <div class="about-row"><b>App version</b><span>${escHtml(META.app_version)}
      (the program itself; updates arrive through the releases page)</span></div>
    <div class="about-row"><b>Build model</b><span>v${escHtml(String(META.model_version))}
      (the math that scores and optimizes builds; champions are re-verified when
      it changes)</span></div>
    <div class="about-row"><b>Game data</b><span>${escHtml(META.db_name || "Mids data")}
      ${escHtml(META.db_version || "")}, with the values that drive the optimizer
      checked against the game client's own files</span></div>
    ${roster}
    <div class="about-row"><b>This build</b><span>server
      ${escHtml(META.build_commit || "(packaged — no source commit)")}, browser loaded
      ${escHtml(jsAssetToken())}. If those two ever look out of step with a change you
      were expecting, the page is running older code than the server.</span></div>
    <p class="about-links">${links}</p>`;
  $("about-modal").classList.remove("hidden");
}

// ── Startup update flow (Mids-style, but opt-in) ────────────────────────────
// First run asks ONCE whether to auto-check at startup — plainly worded, because
// the tool promises to never contact anything without the user's say-so. The
// answer persists; "on" checks GitHub Releases each launch and prompts with
// Update now / Remind me later. The manual footer button always works regardless.
function _ubShow(html) { const b = $("update-banner"); if (b) { b.innerHTML = html; b.classList.remove("hidden"); } }
function _ubHide() { const b = $("update-banner"); if (b) b.classList.add("hidden"); }

function initUpdateFlow() {
  if (!META || !_urlReady((META.urls || {}).releases_api)) return;   // no online home configured
  const pref = localStorage.getItem("hc_update_check");
  if (pref === "off") return;
  if (pref === null) {
    _ubShow(`🔔 <b>Check for updates automatically when the app starts?</b> `
      + `It contacts github.com to compare version numbers — nothing else is ever sent.`
      + `<button class="linkbtn" onclick="setUpdatePref('on')">Yes, check at startup</button>`
      + `<button class="linkbtn quiet" onclick="setUpdatePref('off')">No thanks</button>`);
    return;
  }
  runStartupUpdateCheck();
}
window.setUpdatePref = function (v) {
  localStorage.setItem("hc_update_check", v);
  _ubHide();
  if (v === "on") runStartupUpdateCheck();
};
function _showUpdatePrompt(r) {
  // Installed app: Update now downloads + installs + restarts, no browser trip.
  // Running from source (or if auto-install fails): the download page is the path.
  const updateAct = (META && META.packaged)
    ? `<button class="linkbtn" onclick="oneClickUpdate('${escHtml(r.latest)}','${escHtml(r.url)}')">Update now</button>`
    : `<button class="linkbtn" onclick="window.open('${escHtml(r.url)}','_blank');_ubHide()">Update now</button>`;
  _ubShow(`⬆ <b>Hero Companion v${escHtml(r.latest)}</b> is available — you have v${escHtml(r.current)}.`
    + updateAct
    + `<button class="linkbtn quiet" onclick="_ubHide()">Remind me later</button>`);
}

// Download the installer from the project's releases and hand over to it — the
// installer ends this app, installs, and relaunches it; we poll until the new
// version answers, then reload into it.
window.oneClickUpdate = async function (latest, pageUrl) {
  _ubShow(`⬇ Downloading v${escHtml(latest)}… (~40 MB — hang tight)`);
  const res = await api("/update/install", postJson({})).catch(() => null);
  if (!res || !res.ok) {
    _ubShow(`⚠ ${escHtml((res && res.response) || "Auto-update couldn't start.")} `
      + `<button class="linkbtn" onclick="window.open('${escHtml(pageUrl)}','_blank');_ubHide()">Open the download page</button>`
      + `<button class="linkbtn quiet" onclick="_ubHide()">Dismiss</button>`);
    return;
  }
  _ubShow(`🔧 Installing v${escHtml(latest)}… <b>keep this tab open</b> — it becomes the new `
    + `version by itself when the install finishes (usually under a minute).`);
  const before = META ? META.app_version : "";
  const check = async () => {
    try {
      const m = await fetch("/meta").then(x => x.json());
      if (m.app_version && m.app_version !== before) { clearInterval(timer); location.reload(); }
    } catch { /* app is mid-restart — keep waiting */ }
  };
  const timer = setInterval(check, 2000);
  // Browsers throttle (Edge: suspend) background-tab timers — the field-tested
  // stale-tab papercut. Check immediately on every signal that the user is back.
  document.addEventListener("visibilitychange", () => { if (!document.hidden) check(); });
  window.addEventListener("focus", check);
  window.addEventListener("pageshow", check);
};
async function runStartupUpdateCheck() {
  const r = await api("/meta/update-check").catch(() => null);
  if (!r || !r.ok || !r.update_available) return;    // up to date / offline → stay silent
  _showUpdatePrompt(r);
}
// The header ⟳ chip — the always-available override, independent of the startup pref.
async function manualUpdateCheck() {
  _ubShow("⏳ Checking for updates…");
  const r = await api("/meta/update-check").catch(() => null);
  if (!r || !r.ok) {
    _ubShow(r && r.reason === "not_configured"
      ? "The project's online home isn't configured in this copy."
      : "Couldn't reach github.com — are you offline?");
    setTimeout(_ubHide, 5000);
    return;
  }
  if (!r.update_available) {
    _ubShow(`✓ You're up to date (v${escHtml(r.current)}).`);
    setTimeout(_ubHide, 4000);
    return;
  }
  _showUpdatePrompt(r);
}
window._ubHide = _ubHide;

function reportBug() {
  if (!META) return;
  const url = (META.urls || {}).bug_report;
  if (!_urlReady(url)) {
    alert("The project's GitHub home isn't set up yet — once it exists, this button opens a "
        + "pre-filled bug report there. (Dev note: set the real repo in client_config.json.)");
    return;
  }
  const ctx = build.archetype
    ? `\n**Character:** ${build.archetype} · ${build.primary || "?"} / ${build.secondary || "?"}`
      + ` · role ${build.role || "?"} · ${(build.powers || []).length} powers`
    : "\n**Character:** (none loaded)";
  const body =
    "**What happened?**\n(describe the bug — what you did, what you expected, what you got)\n\n"
    + "**Versions** (auto-filled)\n"
    + `- App: ${META.app_version}\n- Model: v${META.model_version}\n- Game data: ${META.db_name} ${META.db_version}`
    + ctx + "\n\n**Build export** (optional but very helpful)\n"
    + "Paste your Mids export or attach your save file here.\n";
  window.open(`${url}?title=${encodeURIComponent("[bug] ")}&body=${encodeURIComponent(body)}`, "_blank");
}

async function submitChampion() {
  if (!build.archetype || !(build.powers || []).length) {
    alert("Load or build a character first — a champion candidate is your CURRENT build."); return;
  }
  const res = await api("/champion/bundle", postJson({
    archetype: build.archetype, primary: build.primary, secondary: build.secondary,
    epic: build.epic, role: build.role, content: build.content,
    build: { powers: build.powers, pools: build.pools },
  }));
  if (!res || !res.ok) { alert("Couldn't bundle the build — is the server running?"); return; }
  // download the candidate file...
  const blob = new Blob([JSON.stringify(res.bundle, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `champion-candidate-${(build.archetype || "at").replace("Class_", "")}`
             + `-${(build.primary || "").split(".").pop()}-${(build.secondary || "").split(".").pop()}.json`;
  a.click(); URL.revokeObjectURL(a.href);
  // ...then point at the submission queue (hub re-scores everything, so the file is safe to share)
  const url = (META && META.urls || {}).champion_submit;
  if (_urlReady(url)) {
    if (confirm("Candidate file saved. Open the champion submission page to post it?")) window.open(url, "_blank");
  } else {
    alert("Candidate file saved. The online submission queue isn't set up yet — once the GitHub "
        + "home exists, this button will open it for you. Keep the file; it stays valid.");
  }
}

async function checkUpdates() {
  const el = $("update-check");
  if (el) el.textContent = "checking…";
  const r = await api("/meta/update-check").catch(() => null);
  if (!el) return;
  if (!r || !r.ok) {
    el.textContent = r && r.reason === "not_configured" ? "updates: not configured yet" : "updates: offline";
    setTimeout(() => { el.textContent = "check for updates"; }, 4000);
    return;
  }
  if (r.update_available) {
    el.innerHTML = `⬆ v${escHtml(r.latest)} available — <b>open releases</b>`;
    el.onclick = () => window.open(r.url, "_blank");
  } else {
    el.textContent = `✓ up to date (v${r.current})`;
    setTimeout(() => { el.textContent = "check for updates"; }, 4000);
  }
}

async function init() {
  const data = await api("/archetypes");
  // The Mids data build used to be the ONLY version in the header — the one
  // number no user cares about (UX item 2026-07-16). It now lives in the
  // About dialog; the header leads with the app version (see loadMeta).
  $("db-version").textContent = "";
  loadMeta();   // versions + project-home links (bug reports, champions, updates)
  NATURAL_ROLES = Object.fromEntries(
    data.archetypes.map(a => [a.name, a.natural_roles || []]));
  SET_ROLE_EXTENSIONS = data.set_role_extensions || {};
  const sel = $("sel-archetype");
  sel.innerHTML = `<option value="">— choose archetype —</option>` +
    data.archetypes.map(a => `<option value="${a.name}">${a.display_name}</option>`).join("");
  sel.addEventListener("change", (e) => { onArchetypeChange(e); refreshRoleUI(); });
  const _pr = $("preset-role");
  if (_pr) _pr.addEventListener("change", refreshRoleUI);
  document.querySelectorAll(".align-card").forEach(c =>
    c.addEventListener("click", () => applyAlignment(c.dataset.align)));
  applyAlignment(localStorage.getItem("cohAlignment") || "hero");
  if ($("alignment-btn")) $("alignment-btn").addEventListener("click", toggleAlignment);

  // pool selectors (4)
  $("pool-selectors").innerHTML = [0,1,2,3].map(i =>
    `<select class="pool-sel" data-i="${i}" disabled></select>`).join("");

  $("sel-primary").addEventListener("change", e => {
    addPowersetPowers(e.target, "primary");
    pairVeatSets(e.target, $("sel-secondary"), VEAT_PAIR);
    refreshRoleUI(); });
  $("sel-secondary").addEventListener("change", e => {
    addPowersetPowers(e.target, "secondary");
    pairVeatSets(e.target, $("sel-primary"), VEAT_PAIR_REV);
    refreshRoleUI(); });
  $("sel-epic").addEventListener("change", e => addPowersetPowers(e.target, "epic"));

  $("modal-close").addEventListener("click", closeModal);
  $("tier-close").addEventListener("click", () => $("tier-modal").classList.add("hidden"));
  $("about-close").addEventListener("click", () => $("about-modal").classList.add("hidden"));
  $("about-modal").addEventListener("click", (e) => {
    if (e.target === $("about-modal")) $("about-modal").classList.add("hidden"); });
  $("modal-search").addEventListener("input", renderModalSets);
  $("ai-send").addEventListener("click", askAI);
  $("gen-btn").addEventListener("click", confirmGoalThenGenerate);
  $("gen-confirm-yes").addEventListener("click", generateBuild);
  $("gen-confirm-edit").addEventListener("click", () => {
    $("gen-confirm").classList.add("hidden");
    $("gen-goal").focus();
  });
  document.querySelectorAll(".tier-cb").forEach(cb =>
    cb.addEventListener("change", updateGenBtnLabel));
  renderRoleChips();
  updateGenBtnLabel();
  $("opt-btn").addEventListener("click", optimizeBuild);
  $("solve-btn").addEventListener("click", solveSlotting);
  // v35 §4: the preserve checkbox is the MASTER LOCK SWITCH — checking it locks
  // every hand-slotted power (padlocks appear), unchecking unlocks everything.
  // Individual padlock clicks re-derive its state (mixed = indeterminate).
  if ($("preserve-toggle")) $("preserve-toggle").addEventListener("change", (ev) => {
    setAllLocks(ev.target.checked);
    syncPreserveFromLocks();
    renderPowers();
    const st = $("gen-status");
    if (st) st.textContent = ev.target.checked
      ? "🔒 Locked every power with a hand-placed set — unlock exceptions on their cards."
      : "🔓 Everything unlocked — a re-solve may change any power.";
  });
  if ($("preset-content")) $("preset-content").addEventListener("change", previewPreset);
  if ($("preset-role")) $("preset-role").addEventListener("change", previewPreset);
  // Retired-Fire-Farm nudge: pick AFK/Active (sets the picker + re-previews) or defer.
  if ($("farm-retired-note")) $("farm-retired-note").addEventListener("click", (e) => {
    const pick = e.target.closest(".rn-pick");
    if (pick && $("preset-content")) {
      $("preset-content").value = pick.dataset.farm;
      $("preset-content").dispatchEvent(new Event("change"));
    }
    if (pick || e.target.closest(".rn-dismiss"))
      $("farm-retired-note").classList.add("hidden");
  });
  $("export-btn").addEventListener("click", exportMids);
  // Converter panel: build the interactive "want/have" tool when first opened (works with no build).
  if ($("conv-guide-details")) {
    $("conv-guide-details").addEventListener("toggle", (e) => {
      if (e.target.open) { renderConverterTool(); renderConverterGuide(); }
    });
  }
  $("import-btn").addEventListener("click", () => $("import-file").click());
  $("import-file").addEventListener("change", importMids);
  // Entry router — the front door: how do you want to start?
  // entry stays visible until a file is actually CHOSEN (importMids hides it) —
  // a cancelled/failed OS dialog must never strand the user on the bare planner
  $("entry-mids").addEventListener("click", () => $("import-file").click());
  // in-game card: scan-first (the app finds the saves), file picker as fallback
  $("ingame-scan-go").addEventListener("click", () => ingameScan());
  $("ingame-pick-go").addEventListener("click", () => $("import-file").click());
  $("entry-scratch").addEventListener("click", () => { hideEntry(); startFromScratch(); });
  $("entry-respec").addEventListener("click", () => { hideEntry(); startNew50(); });
  $("entry-continue").addEventListener("click", openSavesList);
  $("saves-back").addEventListener("click", () => {
    $("saves-panel").classList.add("hidden"); $("entry-cards").classList.remove("hidden"); });
  $("save-btn").addEventListener("click", saveProgress);
  $("journey-btn").addEventListener("click", toggleJourneyView);
  $("journey-close").addEventListener("click", () => closeJourneyView());
  // standard overlay affordances: Esc closes, so does clicking the dark backdrop
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !$("journey-modal").classList.contains("hidden")) closeJourneyView();
  });
  $("journey-modal").addEventListener("click", (e) => {
    if (e.target === $("journey-modal")) closeJourneyView();
  });
  if ($("bug-btn")) $("bug-btn").addEventListener("click", reportBug);
  if ($("champ-btn")) $("champ-btn").addEventListener("click", submitChampion);
  if ($("update-check")) $("update-check").addEventListener("click", checkUpdates);
  if ($("update-btn")) $("update-btn").addEventListener("click", manualUpdateCheck);
  $("wiz-close").addEventListener("click", closeRespecWizard);
  $("wiz-at").addEventListener("change", () => { wizLoadPowersets(); wizFormRow(); wizExplain(null); });
  if ($("wiz-form")) $("wiz-form").addEventListener("change", () => {
    wizSetSrc("form", $("wiz-form").value ? "you" : "");
    wizGateBuild();
    wizExplain("form");   // the chosen form pops its plain-language explanation
  });
  $("wiz-build").addEventListener("click", buildRespec);
  // a flagged-missing field clears its red ring the moment it gets a value
  document.addEventListener("change", (e) => {
    const t = e.target;
    if (t && t.classList && t.classList.contains("wiz-missing") && t.value)
      t.classList.remove("wiz-missing");
  });
  $("disc-find").addEventListener("click", runDiscovery);
  // Each "How do you play" choice pops its tailored explanation; the summary panel
  // refreshes on every change (including character changes — the text re-tailors).
  [["wiz-role", "role"], ["wiz-content", "content"], ["wiz-exposure", "exposure"],
   ["wiz-travel", "travel"]].forEach(([id, key]) =>
    $(id).addEventListener("change", () => {
      wizSetSrc(key, $(id).value ? "you" : "");
      wizGateBuild(); wizUpdateHint(); wizExplain(key);
    }));
  ["wiz-primary", "wiz-secondary"].forEach((id) =>
    $(id).addEventListener("change", () => wizExplain(null)));
  $("start-over-btn").addEventListener("click", showEntry);
  refreshContinueCard();   // overlay shows on load — reveal Continue if saves exist
  setInterval(autoSaveTick, 120000);   // background auto-save every 2 min (only if changed)
  $("powercolor").addEventListener("toggle", (e) => { if (e.target.open) renderPowerColorRows(); });
  $("pc-preview-btn").addEventListener("click", () => previewPowerColors());
  $("pc-download-btn").addEventListener("click", downloadPowerCust);
  $("incarnate-peak-toggle").addEventListener("change", (e) => {
    // warn-but-allow (Joel's choice-doctrine ruling): the player may preview
    // incarnates below 50; recompute() surfaces the endgame warning if so.
    build.include_incarnates = e.target.checked;
    recompute();
  });
  $("external-toggle").addEventListener("change", (e) => {
    build.include_external = e.target.checked;
    recompute();
  });
  $("pvp-toggle").addEventListener("change", (e) => {
    build.pvp = e.target.checked;
    recompute();
  });
  // #9 combat suppression — a VIEW of the totals, never a build property: not
  // saved, not exported, never sent on solve paths (buildPayload adds it only
  // for calculate/validate so the engine can drop suppressed effect layers).
  $("suppression-toggle").addEventListener("change", (e) => {
    build.suppression = e.target.checked;
    recompute();
  });

  // AI availability. Standalone builds ship AI-OFF (ai_enabled false): the whole
  // assistant seam disappears — no dead chip, no "Ask Claude" that can't answer.
  // The deterministic controls (presets, goal text, Solve) stay; they never needed AI.
  api("/health").then(h => {
    AI_ON = !!h.ai_enabled;
    const _at = $("assistant-title");
    if (_at) _at.innerHTML = escHtml(_at.textContent) + " " + helpIcon('build-assistant');
    if (!AI_ON) {
      const chip = $("claude-status"); if (chip) chip.remove();
      const t = $("assistant-title"); if (t) t.innerHTML = "Build Assistant " + helpIcon('build-assistant');
      const gi = $("gen-intro");
      if (gi) gi.textContent = "Pick archetype + primary + secondary above, choose "
        + "what you're building for, and the solver designs and slots it instantly.";
      const gb = $("gen-btn"); if (gb) gb.style.display = "none";
      document.querySelectorAll(".tier-pick").forEach(el => { el.style.display = "none"; });
      const qa = $("ai-qa"); if (qa) qa.style.display = "none";
      recompute();          // re-gate opt-btn/fit-hint now that AI_ON is known
      return;
    }
    // the placeholder moved out of the HTML (ai-response now lives outside
    // #ai-qa); only the AI-ON client shows the ask-a-question copy
    const _ar = $("ai-response");
    if (_ar && !_ar.innerHTML.trim()) _ar.textContent = "No question asked yet.";
    $("claude-status").textContent = h.claude_available
      ? "AI: Claude Code ready" : "AI: Claude Code not found";
    $("claude-status").style.color = h.claude_available ? "var(--def)" : "var(--bad)";
  });

  INCARNATES = await api("/incarnates");
  renderIncarnates();

  renderSuggested();
  recompute();
  initGamelog();               // the Play Log course at the bottom (fire-and-forget)
}

// ── PLAY LOG (P1): pick an account, ingest /logchat day files, show insights ──
// The raw log never renders — only conclusions (haul verdicts, session totals) plus
// an honest coverage footer, since the parse patterns are provisional until a real
// log sample confirms them.
async function initGamelog() {
  const sec = $("gamelog");
  if (!sec) return;
  // CONSENT FIRST (field report: the app read game files with no permission asked and
  // no statement of use). Until the user explicitly enables the Play Log, the app
  // does not even LOOK at the game's folders — same promise as the update check.
  const consent = localStorage.getItem("hc_playlog");
  if (consent !== "on") {
    sec.classList.remove("hidden");
    $("gl-refresh").style.display = "none";
    $("gl-cards").innerHTML = "";
    $("gl-coverage").innerHTML = "";
    if (consent === "off") {
      $("gl-setup").innerHTML = `<span class="muted">The Play Log is off — the app reads no `
        + `game files. <button class="linkbtn quiet" onclick="playlogConsent('on')">Turn it on</button></span>`;
    } else {
      $("gl-setup").innerHTML =
        `<b>Turn your game sessions into insights</b> — your stats, on your screen. The Play Log reads `
        + `the chat log your game writes and shows you what you earned: influence, drops with keep/sell `
        + `advice, kills, incarnate materials.<br>`
        + `<span class="muted">It all stays on this computer — nothing is uploaded or shared.</span><br>`
        + `<div class="gl-privacy">🔒 <b>Your privacy:</b> this tool only ever handles <b>game data</b> — `
        + `prices, drops, and stats. It never touches your real name, email, location, IP, or account `
        + `login, and it never shares anything about the other players in your chat log. If a future `
        + `version lets you share stats to help the community, that will be a <b>separate, clearly `
        + `labeled opt-in</b> — game data only, and anonymous.</div>`
        + `<button class="gl-acct-btn" onclick="playlogConsent('on')">✅ Show me my stats</button> `
        + `<button class="linkbtn quiet" onclick="playlogConsent('off')">Not now</button>`
        + gamelogSetupHelp();
    }
    return;
  }
  try {
    const scan = await api("/gamelog/scan", postJson({}));
    if (!scan || !scan.ok || !(scan.accounts || []).length) return;   // no game install found
    sec.classList.remove("hidden");
    GAMELOG_ACCOUNTS = scan.accounts;
    GAMELOG_WATCHING = scan.watching || [];   // list of watched log dirs (dual-box = >1)
    GAMELOG_WATCH_STATUS = scan.watch_status || [];   // named per-dir facts (v35, no bare counts)
    renderGamelogControls();
    if (GAMELOG_WATCHING.length) gamelogIngest();
  } catch { /* section stays hidden on any failure */ }
}

// All discovered accounts + the subset currently watched. A dual-boxer ticks BOTH so
// the Play Log shows each character (each account is its own log).
let GAMELOG_ACCOUNTS = [];
let GAMELOG_WATCHING = [];
let GAMELOG_WATCH_STATUS = [];   // [{dir, account, live, age_sec, newest}] from the server

function renderGamelogControls() {
  const nd = (p) => (p || "").replace(/\\/g, "\\\\");
  // v35 (the four-vs-two field report): every watched connection is NAMED —
  // its chip carries the path + last-activity verdict from the server's
  // watch_status, and "live" means RECENT ACTIVITY (24h window, stated),
  // never mere existence. No bare counts anywhere on this surface.
  const statusOf = {};
  (GAMELOG_WATCH_STATUS || []).forEach(s => { statusOf[s.dir] = s; });
  const ageTxt = (s) => s == null ? "no log files yet"
    : s < 3600 ? `${Math.floor(s / 60)} min ago`
    : s < 172800 ? `${Math.floor(s / 3600)} h ago`
    : `${Math.floor(s / 86400)} d ago`;
  const chips = (GAMELOG_ACCOUNTS || []).map(a => {
    const on = GAMELOG_WATCHING.includes(a.log_dir);
    const st = statusOf[a.log_dir];
    const stale = on && st && !st.live;
    const tip = `${a.log_dir}\n`
      + (st ? `last log activity: ${ageTxt(st.age_sec)}`
            + (stale ? "\nDORMANT — no writes in 24h; not counted as live. "
              + "Old install or logging off? Unwatch it, or it revives the "
              + "moment the game writes here." : "")
        : "");
    return `<button class="gl-chip${on ? " active" : ""}${stale ? " stale" : ""}"`
      + ` title="${escHtml(tip)}" onclick="gamelogToggle('${nd(escHtml(a.log_dir))}')">`
      + `${on ? (stale ? "◌ " : "● ") : ""}${escHtml(a.account)}`
      + (a.has_logs ? (stale ? ` <span class="muted">(dormant, ${ageTxt(st.age_sec)})</span>` : "")
                    : ` <span class="muted">(no logs)</span>`) + `</button>`;
  }).join(" ");
  const liveN = (GAMELOG_WATCH_STATUS || []).filter(s => s.live).length;
  const watching = GAMELOG_WATCHING.length;
  $("gl-setup").innerHTML =
    (watching ? `<span class="gl-live" title="Live = the game wrote to that log within 24 hours — hover each account for its path and last activity">`
      + `● ${liveN} live${watching > liveN ? ` / ${watching - liveN} dormant` : ""}</span> ` : "")
    + `<b>Watch account${GAMELOG_ACCOUNTS.length > 1 ? "s" : ""}:</b> ${chips} `
    + `<span class="muted small">— ${watching ? "click to add/remove. " : "pick the one(s) you play. "}`
    + `Dual-boxing? Watch both to see each character side by side.</span>`
    + (watching ? "" : gamelogSetupHelp());
  $("gl-refresh").style.display = watching ? "" : "none";
  if (!watching) { $("gl-cards").innerHTML = ""; $("gl-coverage").innerHTML = ""; gamelogStopLive(); }
}

window.gamelogToggle = async function (dir) {
  const i = GAMELOG_WATCHING.indexOf(dir);
  if (i >= 0) GAMELOG_WATCHING.splice(i, 1); else GAMELOG_WATCHING.push(dir);
  const r = await api("/gamelog/watch", postJson({ log_dirs: GAMELOG_WATCHING }));
  if (r && r.ok) {
    GAMELOG_WATCHING = r.watching || GAMELOG_WATCHING;
    GAMELOG_WATCH_STATUS = r.watch_status || GAMELOG_WATCH_STATUS;
  }
  renderGamelogControls();
  if (GAMELOG_WATCHING.length) gamelogIngest(); else gamelogStopLive();
};

// Per-character fit link (used inside each character's stat card). Returns HTML for the
// "load their fit / import / link" action, based on the character + its matched fit.
let GAMELOG_LINK_CHAR = null;   // character whose link action is currently in flight
function gamelogFitActionHtml(character, fit) {
  const c = escHtml(character);
  const saveOpen = typeof CURRENT_SAVE !== "undefined" && CURRENT_SAVE;
  const loaded = fit && saveOpen && CURRENT_SAVE.id === fit.id;
  const nm = (v) => escHtml(v || "");
  if (fit && fit.linked) {
    return loaded ? `<span class="muted small">fit loaded</span>`
      : `<button class="linkbtn" onclick="loadSave('${nm(fit.id)}')">▶ load fit</button>`;
  }
  if (fit) {
    return `<button class="linkbtn" onclick="gamelogLink('${nm(character)}','${nm(fit.id)}')">▶ load ${nm(fit.name)}</button>`
      + ` <button class="linkbtn quiet" onclick="gamelogNotThis('${nm(character)}')" title="Matched by name — clear if wrong">not ${c}'s?</button>`;
  }
  return `<button class="linkbtn" onclick="gamelogImportFit('${nm(character)}')">📥 import fit</button>`
    + (saveOpen ? ` <button class="linkbtn" onclick="gamelogLink('${nm(character)}')">link open fit</button>` : "");
}

// "Playing as <character>" + a one-click link to that character's saved fit — this is
// what connects the log (who's active) to the builds (their fit). The character comes
// from the log's "Welcome to City of Heroes, X!" marker.
// Explicitly tie a character to a fit (rename-proof). Args: (character, [saveId]). With
// no saveId, links whatever fit is currently open (CURRENT_SAVE). Re-renders from the
// fresh insights the link endpoint returns.
window.gamelogLink = async function (character, saveId) {
  if (!character) return;
  const id = saveId || (typeof CURRENT_SAVE !== "undefined" && CURRENT_SAVE && CURRENT_SAVE.id);
  if (!id) return;
  const r = await api("/gamelog/link", postJson({ character, save_id: id }));
  if (saveId) loadSave(saveId);           // loading a named guess: open it too
  if (r && r.ok) renderGamelog(r.insights, null, null);
};
window.gamelogNotThis = async function (character) {
  if (!character) return;
  const r = await api("/gamelog/link", postJson({ character, save_id: "" }));
  if (r && r.ok) renderGamelog(r.insights, null, null);
  $("gl-coverage").innerHTML = `<span class="muted small">Cleared the guess for `
    + `<b>${escHtml(character)}</b>. Open their fit (Resume or import), then click "link open fit".</span>`;
};
window.gamelogImportFit = function (character) {
  $("gl-coverage").innerHTML = `<span class="muted small">To import <b>${escHtml(character || "this character")}</b>'s `
    + `build: in game type <code>/build_save_file</code>, then pick the exported file →</span>`;
  resyncFromGame();
};

// Live reader: while an account is watched and the Play Log is on screen, poll for new
// log entries so the cards fill in as you play (the ingest reads the file even while the
// game holds it open). Paused when the tab is hidden (browsers throttle it anyway).
let GAMELOG_TIMER = null;
function gamelogStartLive() {
  if (GAMELOG_TIMER) clearInterval(GAMELOG_TIMER);
  GAMELOG_TIMER = setInterval(() => {
    if (!document.hidden && localStorage.getItem("hc_playlog") === "on") gamelogIngest(true);
  }, 20000);   // every 20s — the game flushes the log periodically
}
function gamelogStopLive() {
  if (GAMELOG_TIMER) { clearInterval(GAMELOG_TIMER); GAMELOG_TIMER = null; }
}

window.playlogConsent = function (v) {
  localStorage.setItem("hc_playlog", v);
  initGamelog();
};

// One-time in-game setup, framed so the user only has to think about ONE thing:
// turn on the chat log. The tab details are spelled out so they never have to fuss.
function gamelogSetupHelp() {
  return `<details class="gl-help"><summary>First time? How to turn on your chat log (2 minutes)</summary>
    <ol>
      <li><b>Turn on logging</b> — in game, type <code>/logchat</code> in the chat box and press Enter.
          You'll see "Your chat is now being logged." <b>Then log out to character select and back in</b>
          — logging only starts on a fresh login.</li>
      <li><b>Make a channel tab that captures everything</b> (so nothing is missed):
        <ul>
          <li>Right-click the chat tab bar → <i>Add Tab</i>. Name it <b>Companion</b>.</li>
          <li>In the tab's channel list, add <b>all</b> the channels (tick everything —
              System, Rewards, Combat, and the rest).</li>
          <li>Drag the Companion tab up with your other tabs. It can sit in the background —
              it just needs to exist so its channels get logged.</li>
        </ul>
      </li>
      <li>That's it. Play normally, then come back here — your stats fill in on their own.</li>
    </ol>
    <span class="muted">Note: the game shows the log file as 0&nbsp;KB while you're playing (it's holding
    the file open); the contents are really there and appear when you zone or log out.</span>
  </details>`;
}

window.gamelogIngest = async function (isPoll) {
  const r = await api("/gamelog/ingest", postJson({}));
  if (!r || !r.ok) {
    if (isPoll) return;              // a background poll failing is silent
    renderGamelogControls();        // no watched account → back to the account chips
    return;
  }
  renderGamelog(r.insights, r.report, r.status);
  gamelogStartLive();               // (re)arm the live poll now that we're watching
};

function renderGamelog(ins, report, status) {
  const s = (ins || {}).summary || {};
  const haul = (ins || {}).haul || [];
  const fmt = (n) => (n || 0).toLocaleString();
  // Logging-off nudge: we can't see whether the game is running, so only nudge on a
  // clear signal — no chat log for today at all (they likely haven't turned /logchat on).
  const hint = $("gl-hint") || (() => {
    const d = document.createElement("div"); d.id = "gl-hint"; d.className = "gl-hint";
    $("gl-cards").before(d); return d;
  })();
  if (status && status.has_files === false) {
    hint.innerHTML = `⚠ No chat log file found for this account yet. In game, type `
      + `<code>/logchat</code>, then log out to character select and back in.`;
    hint.style.display = "";
  } else if (status && status.today_log === false) {
    hint.innerHTML = `⚠ No chat log for today — if you're playing now, type <code>/logchat</code> `
      + `in game (and relog once) to start today's log.`;
    hint.style.display = "";
  } else { hint.style.display = "none"; }
  // Per-character stat cards: one per character the log names (a dual-boxer sees Rattle
  // and the farmer side by side). Falls back to a combined card if no character is named.
  const fitOf = {};
  ((ins || {}).who || []).forEach(w => { if (w.character) fitOf[w.character] = w; });
  const kindsLine = (dk) => Object.keys(dk || {}).length
    ? Object.entries(dk).map(([k, n]) => `${n} ${escHtml(k)}`).join(" · ") : "none yet";
  const statCard = (name, cs, w) => {
    const head = name
      ? `<b>${escHtml(name)}</b> <span class="glc-fit">${w ? gamelogFitActionHtml(name, w.fit) : ""}</span>`
      : "THIS SESSION";
    return `<div class="gl-card"><div class="glc-head glc-char">${head}</div>
      <div class="glc-line">Influence <b class="up">+${fmt(cs.inf_gained)}</b>${cs.inf_spent ? ` / <b class="dn">-${fmt(cs.inf_spent)}</b>` : ""}</div>
      <div class="glc-line">Enemies defeated <b>${fmt(cs.kills)}</b>${cs.deaths ? ` · <span class="dn">${fmt(cs.deaths)} faceplant${cs.deaths > 1 ? "s" : ""}</span>` : ""}</div>
      <div class="glc-line">XP <b>${fmt(cs.xp)}</b>${cs.merits ? ` · merits <b>${fmt(cs.merits)}</b>` : ""}</div>
      <div class="glc-line muted">drops: ${kindsLine(cs.drop_kinds)}</div>
      ${(cs.badges || []).length ? `<div class="glc-line">Badges: <b>${cs.badges.slice(-4).map(escHtml).join(", ")}</b></div>` : ""}</div>`;
  };
  const cards = [];
  const byChar = s.by_character || {};
  const names = Object.keys(byChar);
  if (names.length) {
    names.forEach(n => cards.push(statCard(n, byChar[n], fitOf[n])));
  } else {
    cards.push(statCard(null, s, null));   // no Welcome marker yet — combined totals
  }
  // Fit-matched drops (a set the watched character's build actually slots) float to the top
  // and get a ★ — a standard set you'd normally vendor is a KEEP when it's YOUR plan.
  const fitHaul = (ins || {}).fit_haul || 0;
  const recent = haul.slice(-40).reverse();
  recent.sort((a, b) => (b.for_build ? 1 : 0) - (a.for_build ? 1 : 0));
  const rows = recent.slice(0, 18).map(h => {
    const fb = h.for_build;
    const star = fb ? `<span class="gl-star" title="${escHtml(h.why)}">★</span> ` : "";
    return `<tr class="${fb ? "gl-fit-row" : ""}" title="${escHtml(h.why || "")}">`
      + `<td>${star}${escHtml(h.item)}</td><td class="muted">${escHtml(h.kind || "")}</td>`
      + `<td class="${h.verdict === "KEEP" ? "gl-keep" : "gl-sell"}">${escHtml(h.verdict)}</td></tr>`;
  }).join("");
  const fitNote = fitHaul
    ? ` <span class="gl-fit-count" title="Drops that fit a watched character's saved build">★ ${fitHaul} for your build</span>`
    : "";
  cards.push(`<div class="gl-card gl-wide"><div class="glc-head">RECENT HAUL <span class="muted small">(hover a row for the why)</span>${fitNote}</div>
    ${rows ? `<table class="gl-table">${rows}</table>` : `<div class="glc-line muted">No drops logged yet — play a session with /logchat on, then hit ⟳.</div>`}</div>`);
  $("gl-cards").innerHTML = cards.join("");
  if (report) {
    const cov = report.new_lines
      ? `Read ${fmt(report.new_lines)} new line(s) from ${report.files} file(s) — parsed ${fmt(report.parsed)} event(s), `
        + `${fmt(report.unparsed_interesting)} data-looking line(s) not recognized.`
      : "No new log lines since last read.";
    $("gl-coverage").innerHTML = cov
      + ((report.unparsed_samples || []).length
        ? ` <span class="muted">A few lines weren't recognized — <button class="linkbtn quiet" `
          + `onclick="reportBug()">report them</button> to improve the parser.</span>`
          + `<details><summary>show unrecognized samples</summary><pre class="gl-pre">${escHtml(report.unparsed_samples.join("\n"))}</pre></details>`
        : "");
  }
  renderFeedBlock();
}

// ── Pulse Boards feed (Lite parity): explicit, reversible opt-in behind the
// shown terms. Without the release-build key the whole block honestly says so. ──
async function renderFeedBlock() {
  const host = $("gl-feed-block");
  if (!host) return;
  const st = await api("/gamelog/feed");
  if (!st || !st.ok) { host.innerHTML = ""; return; }
  if (!st.key_present) {
    host.innerHTML = `<span class="muted small">Live-board feed: not available in this build `
      + `(no upload key — source runs and forks never feed).</span>`;
    return;
  }
  if (!st.consented) {
    host.innerHTML = `<details><summary class="muted small">📡 Feed the live Pulse Boards — read the terms first</summary>`
      + `<pre class="gl-pre">${escHtml(st.terms)}</pre>`
      + `<button class="ghost-btn" onclick="feedConsent()">I accept — start feeding</button></details>`;
    return;
  }
  const on = !st.feed_disabled;
  host.innerHTML = `<label class="incarnate-toggle" title="The feed sends your captured play data (pseudonymized) to the live Pulse Boards. Reversible any time.">`
    + `<input type="checkbox" ${on ? "checked" : ""} onchange="feedToggle(this.checked)"> 📡 Feed the live boards`
    + `</label> <span class="muted small">${on ? (st.uploaded_last ? `last upload ${escHtml(st.uploaded_last)}` : "waiting for new capture") : "off — nothing uploads"}`
    + `${st.last_error ? ` · ${escHtml(st.last_error)}` : ""}</span>`;
}
window.feedConsent = async function () {
  await api("/gamelog/feed", postJson({ accept_terms: true, enabled: true }));
  renderFeedBlock();
};
window.feedToggle = async function (on) {
  await api("/gamelog/feed", postJson({ enabled: on }));
  renderFeedBlock();
};

// full_name -> family icon URL (server resolves Incarnate_{Slot}_{Family}_{Rarity}.png)
let INC_ICON = {};

function renderIncarnates() {
  if (INCARNATES) {
    INC_ICON = {};
    (INCARNATES.slots || []).forEach(s => (s.choices || []).forEach(ch => {
      if (ch.icon) INC_ICON[ch.full_name] = ch.icon;
    }));
  }
  const host = $("incarnate-selectors");
  if (!host || !INCARNATES) return;
  host.innerHTML = INCARNATES.slots.map((s) => {
    const cur = (build.incarnates[s.slot] || {}).full_name || "";
    // v34 item 6 (the honesty clause): a choice our math doesn't price says so
    // AT THE POINT OF CHOICE — no silent dead picks. `modeled` comes from the
    // server, computed from the engine's own INCARNATE_FX. A whole slot with
    // nothing modeled (Lore = pets, Interface = attack procs) says it once on
    // the label rather than repeating itself down every option.
    const anyModeled = (s.choices || []).some(c => c.modeled);
    const slotNote = anyModeled ? "" :
      ` <span class="inc-unmodeled" title="These are real choices and they work in game — our math just doesn't price this kind of effect yet, so the numbers above won't move. We don't show numbers we can't stand behind.">· not yet modeled</span>`;
    return `<label class="muted small">${s.slot}${slotNote}
      <select data-slot="${s.slot}" onchange="onIncarnate(this)">
        <option value="">— none —</option>
        ${s.choices.map((c) => `<option value="${c.full_name}"${c.full_name === cur ? " selected" : ""}>${
          c.display_name}${(anyModeled && !c.modeled) ? " (not yet modeled)" : ""}</option>`).join("")}
      </select>
    </label>`;
  }).join("");
}

window.onIncarnate = function (sel) {
  const slot = sel.dataset.slot;
  build._incarnatesManual = true;   // user hand-picked — don't let a re-solve clobber it
  if (!sel.value) {
    delete build.incarnates[slot];
  } else {
    build.incarnates[slot] = {
      full_name: sel.value,
      display_name: sel.options[sel.selectedIndex].text,
    };
  }
  recompute();
};

// ---------------------------------------------------------------------------
// Archetype / powerset selection
// ---------------------------------------------------------------------------
async function onArchetypeChange(e) {
  const at = e.target.value;
  build.archetype = at;
  build.primary = build.secondary = build.epic = null;
  build.pools = []; build.pools_display = [];
  build.powers = [];
  build.imported = false;   // fresh start — nothing to preserve
  if (!at) { renderPowers(); recompute(); return; }

  POWERSETS_CACHE = await api(`/powersets/${encodeURIComponent(at)}`);
  fillPowersetSelect($("sel-primary"), POWERSETS_CACHE.primary, "— primary —");
  fillPowersetSelect($("sel-secondary"), POWERSETS_CACHE.secondary, "— secondary —");
  // SINGLE-PATH ARCHETYPES (Kheldians): exactly one primary + one secondary exist —
  // don't make the user open a one-item dropdown; pick them automatically.
  if ((POWERSETS_CACHE.primary || []).length === 1) {
    $("sel-primary").selectedIndex = 1;
    $("sel-primary").dispatchEvent(new Event("change"));
  }
  if ((POWERSETS_CACHE.secondary || []).length === 1) {
    $("sel-secondary").selectedIndex = 1;
    $("sel-secondary").dispatchEvent(new Event("change"));
  }
  // Kheldians travel innately (Energy Flight / Shadow Step) — default to NO extra travel
  // power; picking one anyway stays available in the dropdown.
  const _wt = $("wiz-travel");
  if (_wt) _wt.value = (at === "Class_Peacebringer" || at === "Class_Warshade")
    ? "none" : (_wt.value === "none" ? "super_speed" : _wt.value);
  fillPowersetSelect($("sel-epic"), POWERSETS_CACHE.epic, "— epic/ancillary —");
  // No epic/patron pools for this AT (Kheldians)? Hide the moot dropdown and say why.
  {
    const epicList = POWERSETS_CACHE.epic || [];
    const wrap = $("sel-epic").closest("label") || $("sel-epic").parentElement;
    wrap.style.display = epicList.length ? "" : "none";
    let note = $("no-epic-note");
    if (!note) {
      note = document.createElement("p");
      note.id = "no-epic-note";
      note.className = "muted small";
      wrap.insertAdjacentElement("afterend", note);
    }
    note.style.display = epicList.length ? "none" : "";
    note.textContent = "This archetype has no Epic or Patron pools — its primary and " +
      "secondary carry more powers (and inherent travel) to make up for it.";
  }
  document.querySelectorAll(".pool-sel").forEach(s => {
    fillPowersetSelect(s, POWERSETS_CACHE.pools, "— pool —");
    s.disabled = false;
    s.onchange = () => onPoolChange();
  });
  [$("sel-primary"), $("sel-secondary"), $("sel-epic")].forEach(s => s.disabled = false);
  renderPowers();
  recompute();
}

function fillPowersetSelect(sel, list, placeholder) {
  sel.innerHTML = `<option value="">${placeholder}</option>` +
    (list || []).map(ps =>
      `<option value="${ps.full_name}">${ps.display_name}</option>`).join("");
}

async function loadPowers(psFullName) {
  if (POWERS_CACHE[psFullName]) return POWERS_CACHE[psFullName];
  const data = await api(`/powers/${encodeURIComponent(psFullName)}`);
  POWERS_CACHE[psFullName] = data.powers;
  return data.powers;
}

// When a powerset is chosen we expose its powers as an "add power" picker
async function addPowersetPowers(sel, slot) {
  const psFull = sel.value;
  const psDisplay = sel.options[sel.selectedIndex]?.text;
  if (slot === "primary") { build.primary = psFull; build.primary_display = psDisplay; }
  if (slot === "secondary") { build.secondary = psFull; build.secondary_display = psDisplay; }
  if (slot === "epic") { build.epic = psFull; build.epic_display = psDisplay; }
  if (psFull) await loadPowers(psFull);
  // VEAT branch chosen → also load its base set so the "Add from" row can offer it
  if (VEAT_BASE_SET[psFull]) await loadPowers(VEAT_BASE_SET[psFull]);
  renderPowers();
  recompute();
}

async function onPoolChange() {
  recordEdit();
  const sels = [...document.querySelectorAll(".pool-sel")];
  build.pools = []; build.pools_display = [];
  for (const s of sels) {
    if (s.value) {
      build.pools.push(s.value);
      build.pools_display.push(s.options[s.selectedIndex].text);
      await loadPowers(s.value);
    }
  }
  renderPowers();
  recompute();
}

// ---------------------------------------------------------------------------
// Powers + slots rendering
// ---------------------------------------------------------------------------
// VEAT dual set access: choosing a branch keeps the BASE set available (a Crab build may
// legally take base Wolf Spider powers — post-24 respec keeps both).
const VEAT_BASE_SET = {
  "Arachnos_Soldiers.Bane_Spider_Soldier": "Arachnos_Soldiers.Arachnos_Soldier",
  "Arachnos_Soldiers.Crab_Spider_Soldier": "Arachnos_Soldiers.Arachnos_Soldier",
  "Training_Gadgets.Bane_Spider_Training": "Training_Gadgets.Training_and_Gadgets",
  "Training_Gadgets.Crab_Spider_Training": "Training_Gadgets.Training_and_Gadgets",
  "Widow_Training.Night_Widow_Training": "Widow_Training.Widow_Training",
  "Widow_Training.Fortunata_Training": "Widow_Training.Widow_Training",
  "Teamwork.Widow_Teamwork": "Teamwork.Teamwork",
  "Teamwork.Fortunata_Teamwork": "Teamwork.Teamwork",
};

function chosenPowersets() {
  const list = [];
  if (build.primary) list.push(build.primary);
  if (build.secondary) list.push(build.secondary);
  for (const ps of [build.primary, build.secondary]) {
    const base = VEAT_BASE_SET[ps];
    if (base && !list.includes(base)) list.push(base);
  }
  build.pools.forEach(p => list.push(p));
  if (build.epic) list.push(build.epic);
  return list;
}

// ── RESPEC WORKSHEET ────────────────────────────────────────────────────────
// A loaded build with slots not earning bonuses shows a small labeled BAR at the top of the
// build ("Ready for respec?" / "Respec plan ready — review"). Clicking it opens the full
// worksheet as a POP-UP — before/after per power, a grocery list with checkboxes to track
// crafting + selling, apply-to-build, undo, "respec completed". Kept, but not clutter. The
// worksheet is saved to the character (survives closing the app) so a respec runs over days.
let RESPEC_HINT_DISMISSED = false;
let RESPEC_WORKSHEET = null;   // {character, plan, optimized, before, applied, checks}
let RESPEC_LAST_HINT = null;   // most recent under-investment hint (drives the "ready?" bar)
let RESPEC_VERSION_DRIFT = null; // save predates the current optimizer model (loadSave sets it)
let RESPEC_MODAL_OPEN = false;
function setRespecHintFresh() {
  RESPEC_HINT_DISMISSED = false; RESPEC_WORKSHEET = null; RESPEC_LAST_HINT = null;
  RESPEC_VERSION_DRIFT = null;
}
function restoreWorksheet(ws) { RESPEC_WORKSHEET = ws || null; }
function _who() { return (build.name || "").trim() || "this character"; }
function _persistWorksheet() {
  if (!RESPEC_WORKSHEET || !CURRENT_SAVE || !CURRENT_SAVE.id) return;
  fetch(`/saves/${encodeURIComponent(CURRENT_SAVE.id)}/respec`,
    { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ worksheet: RESPEC_WORKSHEET }) }).catch(() => {});
}
function _clearPersistedWorksheet() {
  if (!CURRENT_SAVE || !CURRENT_SAVE.id) return;
  fetch(`/saves/${encodeURIComponent(CURRENT_SAVE.id)}/respec`, { method: "DELETE" }).catch(() => {});
}

// Called every recompute: keep the small trigger bar in sync, and the pop-up if it's open.
function renderRespecUI(hint) {
  RESPEC_LAST_HINT = hint || null;
  renderRespecTrigger();
  if (RESPEC_MODAL_OPEN) renderRespecModalBody();
}

// The compact bar at the top of the build (not the whole sheet).
function _respecTriggerEl() {
  let el = $("respec-trigger");
  if (!el) {
    el = document.createElement("div");
    el.id = "respec-trigger";
    const host = $("powers-list");
    if (host && host.parentNode) host.parentNode.insertBefore(el, host);
  }
  return el;
}
function renderRespecTrigger() {
  const ws = RESPEC_WORKSHEET;
  const show = !!ws || ((RESPEC_LAST_HINT || RESPEC_VERSION_DRIFT) && !RESPEC_HINT_DISMISSED);
  const existing = $("respec-trigger");
  if (!show) { if (existing) existing.remove(); return; }
  let ico, label, extra = "";
  if (ws && ws.applied) {
    const pr = _respecProgress();
    ico = "🛠️"; label = "Respec in progress"; extra = `<span class="rt-prog">${pr.done}/${pr.total} done</span>`;
  } else if (ws) {
    ico = "🛠️"; label = "Respec plan ready — review";
  } else if (RESPEC_LAST_HINT) {
    const n = RESPEC_LAST_HINT.count;
    ico = "💡"; label = `Ready for respec? ${n} power${n > 1 ? "s" : ""} could gain set bonuses`;
  } else {
    // version drift only: the build is fine structurally, the OPTIMIZER got better
    ico = "🔭"; label = "Built under an older optimizer — see what's improved?";
  }
  const el = _respecTriggerEl();
  el.className = "respec-trigger" + (ws ? " rt-has-plan" : "");
  el.innerHTML = `<button class="rt-open" onclick="openRespecModal()">`
    + `<span class="rt-ico">${ico}</span> <span class="rt-label">${label}</span>${extra}`
    + `<span class="rt-go">open →</span></button>`
    + (ws ? "" : `<button class="rt-x" onclick="dismissRespecHint()" title="Dismiss">✕</button>`);
}
window.dismissRespecHint = function () {
  RESPEC_HINT_DISMISSED = true;
  // A dismissed version-drift offer stays dismissed for this save until the optimizer
  // model actually changes again (keyed save+model) — a remembered "no", not a nag.
  if (RESPEC_VERSION_DRIFT && CURRENT_SAVE && CURRENT_SAVE.id) {
    localStorage.setItem(
      `respecDriftDismissed:${CURRENT_SAVE.id}:m${RESPEC_VERSION_DRIFT.current_model}`, "1");
  }
  const el = $("respec-trigger"); if (el) el.remove();
};

// The pop-up.
window.openRespecModal = function () { RESPEC_MODAL_OPEN = true; renderRespecModalBody(); };
window.closeRespecModal = function () {
  RESPEC_MODAL_OPEN = false;
  const ov = $("respec-modal"); if (ov) ov.remove();
};
function renderRespecModalBody() {
  let ov = $("respec-modal");
  if (!ov) {
    ov = document.createElement("div"); ov.id = "respec-modal"; ov.className = "help-overlay";
    ov.addEventListener("click", (e) => { if (e.target === ov) closeRespecModal(); });
    document.body.appendChild(ov);
  }
  ov.classList.remove("hidden");
  ov.innerHTML = `<div class="respec-modal-card respec-card">`
    + (RESPEC_WORKSHEET ? _worksheetBodyHTML() : _hintBodyHTML()) + `</div>`;
}

function _hintBodyHTML() {
  const hint = RESPEC_LAST_HINT;
  let body;
  if (hint) {
    const names = (hint.powers || []).slice(0, 3).map(escHtml).join(", ");
    const more = hint.count > 3 ? "…" : "";
    body = `<b>${hint.count} power${hint.count > 1 ? "s" : ""}</b> have slots that aren't `
      + `earning set bonuses (${names}${more}). Build a full respec plan to see exactly what to change, `
      + `what it gains, and a grocery list of what to craft and what to unslot &amp; sell.`;
  } else {
    // version-drift offer: nothing is structurally wrong — the optimizer moved on
    const vd = RESPEC_VERSION_DRIFT || {};
    const from = vd.saved_model ? `optimizer v${vd.saved_model}` : "an older version of the optimizer";
    body = `This build was made under ${from}; the current one (v${vd.current_model || "?"}) knows `
      + `more — newer game data and better slotting rules. Build the plan to see whether a respec `
      + `is worth it: if nothing meaningful improves, it will say so.`;
  }
  return `<div class="rc-head"><span class="rc-ico">${hint ? "💡" : "🔭"}</span>`
    + `<span class="rc-title">Suggested respec for ${escHtml(_who())}</span>`
    + helpIcon('respec')
    + `<button class="rc-x" onclick="closeRespecModal()" title="Close">✕</button></div>`
    + `<div class="rc-body">${body}</div>`
    + `<div class="rc-actions"><button class="rc-apply" onclick="buildRespecPlan()">Build the respec plan →</button>`
    + `<button class="rc-cancel" onclick="closeRespecModal()">Not now</button></div>`;
}

// Fetch a FULL respec (preserve:false), turn it into a worksheet, persist, keep the pop-up open.
async function buildRespecPlan() {
  const ov = $("respec-modal");
  const go = ov && ov.querySelector(".rc-apply");
  if (go) { go.disabled = true; go.textContent = "⏳ Solving the respec…"; }
  const content = ($("preset-content") && $("preset-content").value) || "general";
  const role = ($("preset-role") && $("preset-role").value) || null;
  const presolve = build.powers.map(p => ({ full_name: p.full_name, slots: p.slots,
    earned_slot_count: p.earned_slot_count }));
  const res = await api("/build/solve", postJson({
    archetype: build.archetype, content, role, tier: build.tier || "premium",
    roles: (typeof selectedRoles === "function" ? selectedRoles() : []), pvp: build.pvp,
    preserve: false, primary_display: build.primary_display,
    secondary_display: build.secondary_display, powers: presolve,
  })).catch(() => null);
  const card = ov && ov.querySelector(".respec-modal-card");
  if (!res || !res.ok) {
    if (card) card.querySelector(".rc-body").innerHTML = "Couldn't build the plan just now — try Solve directly.";
    if (go) { go.disabled = false; go.textContent = "Build the respec plan →"; }
    return;
  }
  if (!res.respec_plan) {
    if (card) card.innerHTML = `<div class="rc-head"><span class="rc-ico">✓</span>`
      + `<span class="rc-title">${escHtml(_who())} is already well slotted</span>`
      + `<button class="rc-x" onclick="closeRespecModal()" title="Close">✕</button></div>`
      + `<div class="rc-body">A full respec wouldn't meaningfully improve this build — keep what you have.</div>`
      + `<div class="rc-actions"><button class="rc-cancel" onclick="closeRespecModal()">Close</button></div>`;
    RESPEC_HINT_DISMISSED = true; renderRespecTrigger();
    return;
  }
  RESPEC_WORKSHEET = {
    character: _who(), plan: res.respec_plan, optimized: res.powers,
    before: JSON.parse(JSON.stringify(build.powers)), applied: false, checks: {},
  };
  _persistWorksheet();
  renderRespecModalBody();   // the pop-up now shows the full worksheet
  renderRespecTrigger();     // the bar switches to "Respec plan ready — review"
}

function _fmtSets(arr, commons) {
  const parts = (arr || []).map(x => `${x.n}× ${escHtml(x.set)}`);
  if (commons) parts.push(`${commons} common IO${commons > 1 ? "s" : ""}`);
  return parts.length ? parts.join(" + ") : "unslotted";
}
function _respecProgress() {
  const ws = RESPEC_WORKSHEET; if (!ws) return { done: 0, total: 0 };
  const p = ws.plan;
  const total = (p.changes || []).length + (p.acquire || []).length + (p.sell || []).length;
  const done = Object.values(ws.checks || {}).filter(Boolean).length;
  return { done, total };
}

function _worksheetBodyHTML() {
  const ws = RESPEC_WORKSHEET; if (!ws) return "";
  const p = ws.plan, ck = ws.checks || {}, prog = _respecProgress();
  const gains = (p.gains || []).map(g =>
    `<span class="rc-gain">${escHtml(g.stat)} <b>+${g.delta}</b> <span class="muted">(${g.from}→${g.to})</span></span>`).join("");
  const changes = (p.changes || []).map((ch, i) => {
    const key = "c" + i, on = !!ck[key];
    return `<div class="rc-change ${on ? "rc-done" : ""}">`
      + `<label class="rc-ck"><input type="checkbox" ${on ? "checked" : ""} onchange="toggleRespecCheck('${key}')">`
      + `<b>${escHtml(ch.power)}</b></label>`
      + `<div class="rc-ba"><span class="rc-old">${_fmtSets(ch.before, ch.before_commons)}</span>`
      + `<span class="rc-arrow">→</span><span class="rc-new">${_fmtSets(ch.after, 0)}</span></div></div>`;
  }).join("");
  const acquire = (p.acquire || []).map((a, i) => {
    const key = "a" + i, on = !!ck[key];
    return `<li class="${on ? "rc-checked" : ""}"><label><input type="checkbox" ${on ? "checked" : ""} `
      + `onchange="toggleRespecCheck('${key}')"> ${escHtml(a.set)} <b>×${a.pieces}</b>`
      + `${a.rarity ? ` <span class="rc-tag rc-${escHtml(a.rarity)}">${escHtml(a.rarity)}</span>` : ""}</label></li>`;
  }).join("");
  const sell = (p.sell || []).map((s, i) => {
    const key = "s" + i, on = !!ck[key];
    return `<li class="${on ? "rc-checked" : ""}"><label><input type="checkbox" ${on ? "checked" : ""} `
      + `onchange="toggleRespecCheck('${key}')"> ${escHtml(s.set)} <b>×${s.pieces}</b> `
      + `<span class="muted small">— ${escHtml(s.advice || "")}</span></label></li>`;
  }).join("");
  const actions = ws.applied
    ? `<button class="rc-apply" onclick="completeRespec()">✓ Respec completed</button>`
      + `<button class="rc-cancel" onclick="undoRespec()">Undo respec</button>`
    : `<button class="rc-apply" onclick="applyRespecWorksheet()">Apply to build</button>`
      + `<button class="rc-cancel" onclick="discardRespecPlan()">Discard plan</button>`;
  return `<div class="rc-head"><span class="rc-ico">🛠️</span>`
    + `<span class="rc-title">Respec plan for ${escHtml(ws.character || _who())}</span>`
    + helpIcon('respec')
    + `<span class="rc-progress">${prog.done}/${prog.total} done</span>`
    + `<button class="rc-x" onclick="closeRespecModal()" title="Close (kept on this character)">✕</button></div>`
    + (ws.applied ? `<div class="rc-applied">✓ Applied to your build — work the grocery list in-game, then mark it completed (or Undo to revert).</div>` : "")
    + (gains ? `<div class="rc-gains">${gains}</div>` : "")
    + `<div class="rc-section"><div class="rc-label">What changes (${p.power_count} power${p.power_count > 1 ? "s" : ""})</div>${changes}</div>`
    + `<div class="rc-groceries">`
    + `<div class="rc-col"><div class="rc-label">🛒 Craft / buy</div><ul class="rc-list rc-checklist">${acquire || "<li class='muted'>nothing new</li>"}</ul></div>`
    + `<div class="rc-col"><div class="rc-label">💰 Unslot &amp; sell</div><ul class="rc-list rc-checklist">${sell || "<li class='muted'>nothing to remove</li>"}</ul></div>`
    + `</div>`
    + `<div class="rc-actions">${actions}</div>`;
}

window.toggleRespecCheck = function (key) {
  if (!RESPEC_WORKSHEET) return;
  RESPEC_WORKSHEET.checks[key] = !RESPEC_WORKSHEET.checks[key];
  _persistWorksheet();
  renderRespecModalBody();
  renderRespecTrigger();
};
window.applyRespecWorksheet = function () {
  const ws = RESPEC_WORKSHEET; if (!ws || !ws.optimized) return;
  ws.applied = true;
  build.powers = JSON.parse(JSON.stringify(ws.optimized));
  _persistWorksheet();
  renderPowers();
  recompute();          // re-renders trigger + pop-up (now applied) + stats
};
window.undoRespec = function () {
  const ws = RESPEC_WORKSHEET; if (!ws || !ws.before) return;
  ws.applied = false;
  build.powers = JSON.parse(JSON.stringify(ws.before));
  _persistWorksheet();
  renderPowers();
  recompute();
};
window.completeRespec = function () {
  RESPEC_WORKSHEET = null;
  RESPEC_HINT_DISMISSED = true;   // don't immediately re-nudge the build we just fixed
  _clearPersistedWorksheet();
  closeRespecModal();
  const el = $("respec-trigger"); if (el) el.remove();
};
window.discardRespecPlan = function () {
  RESPEC_WORKSHEET = null;
  RESPEC_HINT_DISMISSED = true;
  _clearPersistedWorksheet();
  closeRespecModal();
  const el = $("respec-trigger"); if (el) el.remove();
};
window.buildRespecPlan = buildRespecPlan;

// ── v35 UX batch: per-power LOCKS + assistant mode awareness ─────────────────
// (Joel's Build-Assistant work order, 2026-07-21.) A LOCK freezes a power's
// slotting: the server echoes a locked power byte-identical through ANY solve
// (battery-pinned). "Preserve my IO sets" is a MASTER SWITCH whose state is
// DERIVED from the locks — all hand-slotted powers locked = checked, none =
// unchecked, a mix = indeterminate — so checkbox and locks can never disagree
// (the checkmark law: UI state == engine state).
const _hasSetSlot = (pw) => (pw.slots || []).some(s => s && s.set_uid);
const _hasAnySlot = (pw) => (pw.slots || []).some(s => s);

// RETOOL = a build that already existed arrived on screen (imported or resumed
// from a save). FRESH = building from nothing (incl. tool-generated builds the
// user just asked for — there's no prior investment of theirs to protect).
function isRetool() {
  return build.powers.length > 0 && !!(build.imported || build._resumed);
}

window.togglePowerLock = function (idx) {
  const pw = build.powers[idx];
  if (!pw) return;
  pw._locked = !pw._locked;
  syncPreserveFromLocks();
  renderPowers();
  const st = $("gen-status");
  if (st) st.textContent = pw._locked
    ? `🔒 ${pw.display_name} locked — its slotting won't change until you unlock it.`
    : `🔓 ${pw.display_name} unlocked — a re-solve may now change its slotting.`;
};

function setAllLocks(on) {
  build.powers.forEach(pw => {
    if (_hasSetSlot(pw)) pw._locked = !!on;
    else if (!on) pw._locked = false;   // OFF means NOTHING is locked — manual locks clear too
  });
}

function syncPreserveFromLocks() {
  const cb = $("preserve-toggle");
  if (cb) {
    const elig = build.powers.filter(_hasSetSlot);
    const locked = elig.filter(pw => pw._locked);
    cb.checked = elig.length > 0 && locked.length === elig.length;
    cb.indeterminate = locked.length > 0 && locked.length < elig.length;
  }
  updateAssistantMode();
}

function lockedPowerCount() {
  return build.powers.filter(pw => pw._locked).length;
}

// The Build Assistant states what it does in the CURRENT mode — creating vs
// retooling read as different jobs, and the old panel only ever spoke to the
// first (Joel: identity questions "seem like a decision made when they first
// started, not one used for alterations").
function updateAssistantMode() {
  const retool = isRetool();
  const head = $("gen-head");
  if (head) head.textContent = retool ? "🔧 Improve this build" : "🔧 Build this for me";
  const intro = $("gen-intro");
  if (intro) intro.textContent = retool
    ? "This build already exists — the assistant RE-SLOTS it toward your goal and never touches 🔒 locked powers. The identity below is what the build already is; the goal box and steer chips adjust where the re-slot leans."
    : "Pick archetype + primary + secondary above, describe a goal, choose which build tiers you want, and Claude designs them — pick more than one to compare cost vs. payoff.";
  const pIntro = $("preset-intro");
  if (pIntro) pIntro.innerHTML = retool
    ? "<strong>What is this build for?</strong> Its content and role — the targets any re-slot solves toward."
    : "<strong>What are you building for?</strong> Pick a target and the solver optimizes for your archetype automatically — no description needed.";
  const idNote = $("retool-identity-note");
  if (idNote) idNote.classList.toggle("hidden", !retool);
  const sb = $("solve-btn");
  if (sb) {
    const n = lockedPowerCount();
    sb.textContent = !retool
      ? "🧮 Solve optimal slotting for goal (instant)"
      : n ? `🧮 Re-slot everything except your ${n} locked power${n === 1 ? "" : "s"} (instant)`
          : "🧮 Re-slot this whole build toward the goal (instant)";
  }
  updateGenBtnLabel();   // the Generate button's replace-warning tracks the mode
}

function renderPowers() {
  applyIdentityLock();          // keep archetype/powerset lock in sync (onArchetypeChange re-enables them)
  const host = $("powers-list");
  const sets = chosenPowersets();
  if (!sets.length) { host.innerHTML = `<p class="muted small">Select powersets to add powers.</p>`; return; }

  // Power ICON lookup (records carry it since the /powers endpoint attaches one).
  const iconOf = (fullName) => {
    for (const ps of Object.keys(POWERS_CACHE)) {
      const rec = (POWERS_CACHE[ps] || []).find(p => p.full_name === fullName);
      if (rec && rec.icon) return rec.icon;
    }
    return "";
  };

  // THE BRICK WALL: uniform-size power cards flowing left-to-right in pick order
  // (the L-badge carries the level), with the three info bricks as double-height
  // blocks in the same flow. Snug by construction — no columns, no pockets.
  // Generated builds carry no pick_level — derive one from the real pick ladder.
  const LADDER = [1, 1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28,
                  30, 32, 35, 38, 41, 44, 47, 49];
  let ladderI = 0;
  const cards = build.powers.map((pw, idx) => {
    // Inherents are auto-granted: no pick level, no ladder slot — they sort last
    // and their card badge reads "auto" instead of a level.
    if ((pw.full_name || "").startsWith("Inherent.")) return [pw, idx, null];
    const lv = pw.pick_level || LADDER[Math.min(ladderI++, LADDER.length - 1)];
    return [pw, idx, lv];
  });
  // Level ties (the two level-1 creation picks): secondary first, matching the game.
  const _secTie = (c) => (c[0].powerset_full_name === build.secondary ? 0 : 1);
  cards.sort((a, b) => ((a[2] ?? 999) - (b[2] ?? 999)) || (_secTie(a) - _secTie(b)));
  let html = "";
  if (cards.length) {
    // A pure uniform wall of power cards, then the INFO COURSE: the three summary
    // bricks as one full-width row at the bottom of the powers section.
    html += `<div class="powers-wall">`
      + cards.map(([pw, idx, lv]) => powerCardHtml(pw, idx, iconOf(pw.full_name), lv)).join("")
      + `</div>`
      // v34 ACCOLADES PANEL — Joel's placement CORRECTION 2 ("the layout it
      // created is bad"): the one-band strip wedged beside Stamina rendered
      // cramped and illegible (clipped rows, a horizontal scrollbar, checkboxes
      // drifting off their names). Legibility beats cleverness. It now lives in
      // the SUMMARY BAND with the Vitals / Set Bonuses / Uniques boxes, full
      // width of that course and sized to be read. No dead-space span maths any
      // more — the width is simply the course's width.
      + `<div class="info-course">`
      + `<div id="overview-card" class="overview-card hidden"></div>`
      + `<div id="bonuses-card" class="overview-card hidden"></div>`
      + `<div id="uniques-card" class="overview-card hidden"></div>`
      + `<div id="accolades-card" class="accolades-card"></div>`
      + `</div>`;
  }

  // "Add power" pickers — the choices, below the build
  html += `<div class="add-powers-row">`;
  for (const ps of sets) {
    const powers = (POWERS_CACHE[ps] || []).filter(p => p.slottable);
    if (!powers.length) continue;
    const psName = ps.split(".").slice(-1)[0].replace(/_/g, " ");
    html += `<div class="add-power"><label class="muted small">Add from ${psName}
      <select data-ps="${ps}" onchange="addPower(this)">
        <option value="">+ add power…</option>
        ${powers.map(p => `<option value="${p.full_name}">${p.display_name}</option>`).join("")}
      </select></label></div>`;
  }
  html += `</div>`;

  // One-time hint: the decision notes only answer skepticism if people find them
  // (field report: the "?" was found only by deliberate poking).
  try {
    if (!localStorage.getItem("hc_note_hint")
        && (build.powers || []).some(p => p.slot_plan && p.slot_plan.text)) {
      html = `<div id="note-hint" class="note-hint">💡 Every slotting note (like
        🎯 Full set or 🌐 Global mules) is clickable — it explains why the planner
        chose that slotting. <button class="mini" onclick="noteHintDone()">got it</button></div>` + html;
    }
  } catch (e) { /* localStorage unavailable — skip the hint */ }

  host.innerHTML = html;
  updateInfoCards(LAST_TOTALS);   // refill + re-dock the info bricks (masonry balance)
  updateEditBar();
  updateEpicBadge();
  renderConverterGuide();
}

// ── Totals-checkbox redesign (Joel's four-state visual language, completed
// 0.12.18 on his Maelwys-round-4 ruling): color + glyph coded, never color
// alone — and NO exclusivity anywhere. Every combination the old one-at-a-time
// rule blocked is real play (Build Up+Aim, Farsight+Group Invis+Power Boost,
// Meltdown+Shadow Meld); honesty in labeling replaced restriction:
//   locked (🔒 autos/passives/inherents — no off-state exists in-game)
//   toggle (⏻ default ON — mule hosts, circumstantial what-ifs)
//   cycle  (⟳ default OFF — a window its uptime math can sustain; shows the
//           real uptime/perma figure at the build's recharge)
//   burst  (💥 default OFF — a short strike window, ≤29s and not sustainable;
//           checking it is a BURST view, and the totals panel says so loudly)
// The cycle/burst split is LABELING ONLY (duration + the build's own uptime
// math decide; the 30–89s middle band earns whichever its uptime supports).
// Plain Click attacks (no self_effects) get no chip — a false control.
function _clickUptime(tk) {
  const rech = tk.base_recharge || 0;
  const dur = tk.buff_duration || 0;
  if (!rech || !dur) return null;
  // The game's formula: local slotted recharge (server-computed, post-ED) and
  // global recharge ADD in one denominator. Both matter — Hasten's own IOs
  // carry a third of its uptime.
  const globalRech = (LAST_TOTALS && LAST_TOTALS.recharge && LAST_TOTALS.recharge.value) || 0;
  const effRecharge = rech / (1 + globalRech / 100 + (tk.recharge_enh || 0));
  // Perma when the window covers cast-to-cast cycle (recharge starts on cast;
  // the cast itself is negligible next to these windows).
  return Math.max(0, Math.min(1, dur / effRecharge));
}
function _clickUptimeNote(tk) {
  const uptime = _clickUptime(tk);
  if (uptime == null) return "";
  return uptime >= 0.95
    ? " — perma at your current recharge when previewed"
    : ` — ~${Math.round(uptime * 100)}% uptime at your current recharge`;
}
// Burst vs cycle, per Joel's ruling: ≥90s windows (Hasten/Farsight class, 141
// powers) are cycles by duration; the ≤29s cluster (Build Up/Aim, 279) and the
// 30–89s middle band (Meltdown/Soul Drain, 175) earn whichever label the
// build's OWN uptime math supports — Parry at 3s recharge is effectively
// always-on and wears the cycle chip its math deserves.
function _isBurst(tk) {
  const dur = tk.buff_duration || 0;
  if (!dur || dur >= 90) return false;
  const uptime = _clickUptime(tk);
  if (uptime == null) return dur <= 29;   // no recharge data: the duration cluster decides
  return uptime < 0.5;
}
// A freshly solved/imported power often carries no explicit include_in_totals yet
// (unset, not false) — the checkbox must still communicate what the ENGINE actually
// assumes (engine.py mirrors this: undefined -> auto/toggle on, click off), not read
// as an accidental "off". Only an explicit true/false (a user's own edit) overrides it.
function _effectiveIncluded(pw) {
  if (pw.include_in_totals !== undefined && pw.include_in_totals !== null) {
    return !!pw.include_in_totals;
  }
  return !!(pw.totals_kind && pw.totals_kind.kind === "toggle");
}
function totalsChipHtml(pw, idx) {
  const tk = pw.totals_kind;
  if (!tk) return "";   // plain attack — no self-total to control, no false checkbox
  if (tk.kind === "locked") {
    return `<span class="totals-chip totals-locked" title="Always on — cannot be turned off in-game">
      <span class="tc-glyph" aria-hidden="true">🔒</span></span>`;
  }
  const included = _effectiveIncluded(pw);
  if (tk.kind === "toggle") {
    return `<label class="totals-chip totals-toggle"
        title="Counts this toggle's own effects in your totals — uncheck toggles you won't actually run (a mule host, or a circumstantial what-if like &quot;Weave off&quot;). Set bonuses count either way.">
      <span class="tc-glyph" aria-hidden="true">⏻</span>
      <input type="checkbox" ${included ? "checked" : ""}
        onchange="toggleInclude(${idx}, this.checked)"></label>`;
  }
  // click_buff — previews stack freely (0.12.18: exclusivity removed, every
  // blocked combination was real play), default off, visually split cycle vs
  // burst by the duration + uptime math. EXPLICIT check, not a fallthrough: an
  // unknown future kind must render as "no chip" (safe), never silently
  // borrow this branch's semantics (ideas.md caution).
  if (tk.kind !== "click_buff") return "";
  const note = _clickUptimeNote(tk);
  if (tk.amplifier) {
    // Power Boost class: previews as a MULTIPLIER on other checked powers'
    // buffable defense/ToHit, not as its own stat line.
    const pct = Math.round((tk.amp_scale || 0) * 100);
    return `<label class="totals-chip totals-amp ${included ? "active" : ""}"
        title="Preview this amplifier: while its window is up, your buffable defense/ToHit values are boosted +${pct}% strength (effects the game marks 'Ignores Buffs' are skipped). Stacks with your other previews — e.g. Power Boost + Farsight + Group Invisibility to check the soft cap${note}.">
      <span class="tc-glyph" aria-hidden="true">⚡</span>
      <input type="checkbox" ${included ? "checked" : ""}
        onchange="toggleInclude(${idx}, this.checked)"></label>`;
  }
  if (_isBurst(tk)) {
    return `<label class="totals-chip totals-burst ${included ? "active" : ""}"
        title="Preview this STRIKE WINDOW in your totals — a short burst (${tk.buff_duration}s), not sustained numbers. Previews stack freely; the totals panel flags the burst view while any are checked${note}.">
      <span class="tc-glyph" aria-hidden="true">💥</span>
      <input type="checkbox" ${included ? "checked" : ""}
        onchange="toggleInclude(${idx}, this.checked)"></label>`;
  }
  return `<label class="totals-chip totals-cycle ${included ? "active" : ""}"
      title="Preview this cycling buff's window in your totals — previews stack freely${note}.">
    <span class="tc-glyph" aria-hidden="true">⟳</span>
    <input type="checkbox" ${included ? "checked" : ""}
      onchange="toggleInclude(${idx}, this.checked)"></label>`;
}

// One taken power as a Sidekick-style card: power icon + name + level badge on top,
// the enhancement-icon row as the star, tools tucked right, set summary as fine print.
function powerCardHtml(pw, idx, icon, lv) {
  const cats = (pw.accepted_set_categories || []).join(", ") || "no set categories";
  // 2d (Joel's 0.12.20 eyeball walk): the full power NAME owns the card's top
  // line, untruncated — "for obvious reasons" — with the ⓘ ALWAYS visible
  // beside it (an affordance that only appears on hover fails discoverability
  // by definition). Level tag, chips, and controls move to their own row.
  const nameLine = `<div class="pc-head">
      <span class="pc-title" onclick="selectPower('${escHtml(pw.full_name)}')">
      ${icon ? `<img class="pc-ico" src="${icon}" alt="" loading="lazy"
                 onerror="this.style.display='none'">` : ""}
      <span class="pname">${escHtml(pw.display_name)}</span><span class="pc-info-glyph" title="IO set &amp; power details">ⓘ</span></span>
    </div>`;
  // v35 UX batch §4: the visible per-power LOCK. Shown on any power with real
  // slotting; state is the truth the solve honors (locked = byte-identical).
  const lockBtn = _hasAnySlot(pw)
    ? `<button class="mini lock-btn${pw._locked ? " locked" : ""}" onclick="togglePowerLock(${idx})"
         title="${pw._locked
      ? "Locked — this power's slotting won't change. Unlock it to let a re-solve touch it."
      : "Unlocked — a re-solve may change this power's slotting. Lock it to keep it exactly as-is."}">${pw._locked ? "🔒" : "🔓"}</button>`
    : "";
  const lockedCls = pw._locked ? " pc-locked" : "";
  if ((pw.full_name || "").startsWith("Inherent.")) {
    return `<div class="power-card${lockedCls}" title="${escHtml(pw.display_name)} — accepts: ${escHtml(cats)}\nInherent — the game grants this automatically; it is never a pick.">
      ${nameLine}
      <div class="pc-sub">
        <span class="pc-tools">
          ${totalsChipHtml(pw, idx)}
          ${lockBtn}
          <button class="mini" onclick="changeSlots(${idx}, -1)" title="return this power's last slot to the shared pool (67 added slots for the whole build)">−</button>
          <button class="mini" onclick="changeSlots(${idx}, 1)" title="spend a free slot from the shared pool here (67 added slots for the whole build)">+</button>
        </span>
      </div>
      <div class="slot-row">${pw.slots.map((s, si) => slotHtml(idx, si, s)).join("")}</div>
      ${setSummaryHtml(pw)}
      ${slotPlanHtml(pw)}
    </div>`;
  }
  const lvl = pw.pick_level || lv;
  return `<div class="power-card${lockedCls}" title="${escHtml(pw.display_name)} — accepts: ${escHtml(cats)}\n(click the name for full power info)">
    ${nameLine}
    <div class="pc-sub">
      ${lvl ? `<span class="pick-lvl" title="${pw.pick_level ? `Chosen at level ${lvl}` : `Suggested pick order — about level ${lvl}`}">${pw.pick_level ? "" : "~"}L${lvl}</span>` : ""}
      <span class="pc-tools">
        ${totalsChipHtml(pw, idx)}
        ${lockBtn}
        <button class="mini" onclick="changeSlots(${idx}, -1)" title="return this power's last slot to the shared pool (67 added slots for the whole build)">−</button>
        <button class="mini" onclick="changeSlots(${idx}, 1)" title="spend a free slot from the shared pool here (67 added slots for the whole build)">+</button>
        <button class="remove-power" onclick="removePower(${idx})" title="remove this power">✕</button>
      </span>
    </div>
    <div class="slot-row">${pw.slots.map((s, si) => slotHtml(idx, si, s)).join("")}</div>
    ${setSummaryHtml(pw)}
    ${slotPlanHtml(pw)}
  </div>`;
}

// ── Power Info: the Sidekick-style right-hand detail panel ───────────────────
// Fills the layout's third column with the selected power's real numbers: type,
// costs, cycle, live attack stats (proc-inclusive, from the last recompute), the
// enhancement categories it accepts, and what's slotted in it right now.
let SELECTED_POWER = null;

window.selectPower = function (fullName) {
  SELECTED_POWER = fullName;
  renderPowerInfo();
};
window.closePowerInfo = function () {
  SELECTED_POWER = null;
  SELECTED_ENH = null;
  const panel = $("power-info");
  if (panel) panel.classList.add("hidden");
  document.querySelector("main").classList.remove("has-info");
};
// The panel closes on Esc and outside-click, not only via its ✕ (the steady-
// mouse tax, UX note 5). Undo (Ctrl+Z) stays edits-only and ignores the panel.
document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape" && (SELECTED_POWER || SELECTED_ENH)) closePowerInfo();
});
document.addEventListener("click", (ev) => {
  if (!SELECTED_POWER && !SELECTED_ENH) return;
  const panel = $("power-info");
  if (panel && !panel.classList.contains("hidden")
      && !panel.contains(ev.target) && !ev.target.closest(".pc-title")
      && !ev.target.closest(".slot") && !ev.target.closest("#modal")) {
    closePowerInfo();
  }
});

// ── IO FULL-DETAIL CARD + SLOTTED-SET PROGRESS (feature pair, display-only) ──
// The authentic in-game text (client-bin extraction) for the piece under a
// slot, plus the parent set's roster/tier progress against THIS build — the
// vendor-tooltip experience. Shares the right-rail panel with power info.
// LIVE-RAIL RULE (Joel's pinned acceptance criterion): whatever rail view is
// open re-renders on every build edit — recompute() calls renderRail(), and
// the async renders are token-guarded so a stale fetch can never paint over a
// newer state. The card keys on the POWER'S FULL NAME, not its index, so
// adding/removing other powers can't silently re-point it at a different slot.
let SELECTED_ENH = null;   // {powerFull, slotIdx}
let RAIL_TOKEN = 0;        // bumps per render; stale awaits check and bail

// ── ENHANCEMENT-BOOSTER PREVIEW (Joel's design, display-only) ────────────────
// Ephemeral BY CONSTRUCTION: previews live OUTSIDE the build object, so
// auto-save can never persist them as owned — "not saved as owned" is
// structural, not a stripping step. Each entry remembers the piece it was
// set on; if a solve/import replaces the slot's piece, the stale preview
// self-invalidates instead of silently boosting the new piece. The solver
// never sees these: only buildPayload (calculate/validate) injects them,
// and every /build/solve call builds its payload from build.powers directly
// (the standing boundary: champions/solver never run on boosted values).
const PREVIEW_BOOSTS = {};   // "powerFull|slotIdx" -> {boost: 1..5, piece: uid}

// Attunement arrives two ways: the slot flag (imports) or the piece's own
// Attuned_* uid (solver-placed pieces carry no flag) — either blocks boosting.
function _slotAttuned(slot) {
  return !!(slot && (slot.attuned || /^Attuned_/.test(slot.piece_uid || "")));
}
function _previewBoostFor(powerFull, slotIdx, slot) {
  const e = PREVIEW_BOOSTS[powerFull + "|" + slotIdx];
  return (e && slot && !_slotAttuned(slot) && e.piece === slot.piece_uid) ? e.boost : 0;
}

window.stepBoostPreview = function (powerFull, slotIdx, delta) {
  const pw = build.powers.find(p => p.full_name === powerFull);
  const s = pw && (pw.slots || [])[slotIdx];
  if (!s || !s.piece_uid || _slotAttuned(s)) return;
  const key = powerFull + "|" + slotIdx;
  const owned = s.boost || 0;
  const cur = _previewBoostFor(powerFull, slotIdx, s) || owned;
  const next = Math.max(0, Math.min(5, cur + delta));
  if (next === owned) delete PREVIEW_BOOSTS[key];      // back to what you own
  else PREVIEW_BOOSTS[key] = { boost: next, piece: s.piece_uid };
  renderPowers();     // preview-styled level tags on the chits
  recompute();        // live totals at the previewed level (+ rail re-render)
};
window.clearBoostPreview = function (powerFull, slotIdx) {
  delete PREVIEW_BOOSTS[powerFull + "|" + slotIdx];
  renderPowers(); recompute();
};

// The set roster + tier ladder, shared verbatim between the IO detail card and
// the power-info set view (Feature B refinement) — one renderer, per the
// fix-at-the-rail-level rule.
function enhSetSectionHtml(st) {
  const chip = { "slotted-here": ["✔ here", "eh-here"],
                 "elsewhere": ["◐ elsewhere", "eh-else"],
                 "missing": ["· missing", "eh-miss"] };
  return `<div class="eh-roster">${st.roster.map(x => {
      const [lab, cls] = chip[x.status] || ["", ""];
      return `<div class="eh-piece ${cls}" title="${escHtml(x.title)}">
                <span class="eh-piece-name">${escHtml(x.title.split(":").pop().trim())}</span>
                <span class="eh-status">${lab}</span></div>`;
    }).join("")}</div>`
    + `<div class="eh-tiers">${st.tiers.map(t =>
        `<div class="eh-tier ${t.attained ? "eh-lit" : ""} ${t.next ? "eh-next" : ""}">
           <span class="eh-tier-n">(${t.pieces_required})</span>
           <span class="eh-tier-txt">${escHtml(t.bonus_title)}${t.values.length
             ? ` — ${escHtml(t.values.join(", "))}` : ""}${t.unpriced
             ? ` <span class="muted small">· not yet in totals</span>` : ""}</span>
           ${t.next ? `<span class="eh-tier-hint">← next piece</span>` : ""}
         </div>`).join("")}</div>`;
}

function _enhDetailPayload(pw, s, slotIdx) {
  // An active booster preview renders the card's help text at the previewed
  // level — the description's own numbers teach the value curve.
  const pv = slotIdx != null ? _previewBoostFor(pw.full_name, slotIdx, s) : 0;
  return {
    piece_uid: s.piece_uid, set_uid: s.set_uid || null,
    piece_name: s.piece_name || null,
    archetype: build.archetype,
    io_level: s.io_level || null, boost: pv || s.boost || 0,
    attuned: !!s.attuned,
    power_full_name: pw.full_name,
    powers: build.powers.map(p => ({ full_name: p.full_name, slots: p.slots })),
  };
}

window.openEnhInfo = function (powerIdx, slotIdx) {
  const pw = build.powers[powerIdx];
  const s = pw && (pw.slots || [])[slotIdx];
  if (!s || !s.piece_uid) return;
  SELECTED_POWER = null;
  SELECTED_ENH = { powerFull: pw.full_name, slotIdx };
  renderEnhInfo();
};

async function renderEnhInfo() {
  if (!SELECTED_ENH) return;
  const pw = build.powers.find(p => p.full_name === SELECTED_ENH.powerFull);
  const s = pw && (pw.slots || [])[SELECTED_ENH.slotIdx];
  if (!s || !s.piece_uid) { closePowerInfo(); return; }   // slot cleared under us
  const token = ++RAIL_TOKEN;
  const r = await api("/enhancement/detail",
                      postJson(_enhDetailPayload(pw, s, SELECTED_ENH.slotIdx))).catch(() => null);
  if (token !== RAIL_TOKEN || !SELECTED_ENH) return;      // superseded render
  if (!r || !r.ok) return;
  const panel = $("power-info");
  if (!panel) return;
  const lvl = s.attuned ? "attuned"
    : s.io_level ? `level ${s.io_level}${s.boost ? "+" + s.boost : ""}` : "";
  const p = r.piece, st = r.set;

  // Booster preview stepper (Joel's design): per-level +1..+5 so the value
  // curve is visible ("+3 reaches the soft cap; +4 and +5 buy nothing here").
  // Ineligible pieces say WHY. The description above re-renders at the
  // previewed level on recompute, so the card's own numbers teach the curve.
  const bp = p.boost_preview || {};
  const pf = SELECTED_ENH.powerFull, si = SELECTED_ENH.slotIdx;
  const pv = _previewBoostFor(pf, si, s);
  const owned = (!s.attuned && s.boost) || 0;
  let boostHtml = "";
  if (bp.boostable) {
    const shown = pv || owned;
    boostHtml = `<div class="eh-boost">
      <div class="eh-boost-head">Enhancement Boosters${pv ? ` <span class="eh-preview-tag">PREVIEW — not saved as owned</span>` : ""}</div>
      <div class="eh-boost-row">
        <button class="mini" onclick="stepBoostPreview('${escHtml(pf)}',${si},-1)">−</button>
        <span class="eh-boost-val${pv ? " previewing" : ""}">+${shown}</span>
        <button class="mini" onclick="stepBoostPreview('${escHtml(pf)}',${si},1)">+</button>
        ${pv ? `<button class="mini" onclick="clearBoostPreview('${escHtml(pf)}',${si})">back to owned (+${owned})</button>` : ""}
      </div>
      <p class="muted small">Boosters (+1 per booster, up to +5) come from merit
      vendors and the Auction House; in-game you combine them onto the slotted
      enhancement in the enhancement management screen, permanently. The
      trade-off: a boosted IO stops scaling down when you exemplar below its
      level, while an attuned one keeps scaling — boosting is a choice, not a
      straight upgrade.</p></div>`;
  } else if (bp.reason) {
    boostHtml = `<div class="eh-boost"><div class="eh-boost-head">Enhancement Boosters</div>
      <p class="muted small">${escHtml(bp.reason)}</p></div>`;
  }

  panel.innerHTML =
    `<h2><span>${escHtml(p.title)}</span>
       <button class="iconbtn pi-close" onclick="closePowerInfo()" title="close">✕</button></h2>`
    + (lvl ? `<div class="muted small">${escHtml(lvl)}${pv ? ` · <span class="eh-preview-tag">previewing +${pv}</span>` : ""}${st ? ` · set levels ${st.min_level}–${st.max_level}` : ""}</div>` : "")
    + `<p class="eh-desc">${escHtml(p.description)}</p>`
    + (p.unique_line ? `<p class="eh-note">${escHtml(p.unique_line)}</p>` : "")
    + (p.attuned_note ? `<p class="eh-note">${escHtml(p.attuned_note)}</p>` : "")
    + boostHtml
    + (st ? `<h3 class="eh-set-h">${escHtml(st.display)} <span class="muted small">${escHtml(st.category_label || "")} · ${st.slotted_here} of ${st.roster.length} in this power</span></h3>`
      + enhSetSectionHtml(st) : "");
  panel.classList.remove("hidden");
  document.querySelector("main").classList.add("has-info");
}

// One dispatcher for whichever rail view is open — recompute() calls this so
// both views track every build edit (slot swaps, +/- slots, undo, solve).
function renderRail() {
  if (SELECTED_ENH) renderEnhInfo();
  else if (SELECTED_POWER) renderPowerInfo();
}

async function renderPowerInfo() {
  const panel = $("power-info");
  if (!panel || !SELECTED_POWER) return;
  let rec = null;
  for (const ps of Object.keys(POWERS_CACHE)) {
    rec = (POWERS_CACHE[ps] || []).find(p => p.full_name === SELECTED_POWER);
    if (rec) break;
  }
  const pw = build.powers.find(p => p.full_name === SELECTED_POWER) || {};
  const name = (rec && rec.display_name) || pw.display_name || SELECTED_POWER.split(".").pop();
  const type = { 0: "Click", 1: "Auto (always on)", 2: "Toggle" }[
    (rec && rec.power_type) ?? pw.power_type] || "";
  // live attack numbers (proc damage included — the engine prices procs)
  const atk = ((LAST_TOTALS && LAST_TOTALS.offense && LAST_TOTALS.offense.attacks) || [])
    .find(a => a.name === name);
  const rows = [];
  if (type) rows.push(["Type", type]);
  if (rec && rec.level_available) rows.push(["Available", `level ${rec.level_available}`]);
  if (rec && rec.end_cost) rows.push(["End cost", rec.end_cost.toFixed(2)]);
  if (rec && rec.cast_time) rows.push(["Cast time", `${rec.cast_time.toFixed(2)}s`]);
  if (rec && rec.base_recharge) rows.push(["Base recharge", `${rec.base_recharge}s`]);
  if (atk) {
    rows.push(["Damage / hit", atk.damage]);
    if (atk.recharge != null) rows.push(["Recharge (slotted)", `${atk.recharge}s`]);
    if (atk.dpa) rows.push(["DPA (dmg/sec cast)", atk.dpa]);
    if (atk.dps_spam) rows.push(["Cycled DPS", atk.dps_spam]);
  }
  const cats = ((rec && rec.accepted_set_categories) || pw.accepted_set_categories || []);
  const slotted = (pw.slots || []).filter(Boolean);

  // Feature B refinement (Joel's GO): the merchant-style set view, grouped by
  // parent set. One set in the power → its card renders inline; a frankenslot
  // (2+ sets) → one collapsed row per set ("2/6 — next: +10% regen"),
  // expandable — the grouping IS the information there. Fetches are token-
  // guarded: an edit mid-fetch abandons this paint (live-rail rule).
  const bySet = new Map();   // set_uid -> [slots] (first slot anchors the fetch)
  slotted.forEach(s => {
    if (!s.set_uid) return;
    if (!bySet.has(s.set_uid)) bySet.set(s.set_uid, []);
    bySet.get(s.set_uid).push(s);
  });
  const sel = SELECTED_POWER;
  const token = ++RAIL_TOKEN;
  const entries = [...bySet.entries()];
  const details = await Promise.all(entries.map(([, group]) =>
    api("/enhancement/detail", postJson(_enhDetailPayload(pw, group[0]))).catch(() => null)));
  if (token !== RAIL_TOKEN || SELECTED_POWER !== sel) return;   // superseded
  const sets = details.filter(r => r && r.ok && r.set).map(r => r.set);
  // Pieces with no set card (HOs, D-Syncs, commons) get an honest count line
  // instead of vanishing: everything slotted minus the resolved sets' pieces.
  const resolvedPieces = entries.reduce((n, [, group], i) =>
    n + ((details[i] && details[i].ok && details[i].set) ? group.length : 0), 0);
  const commons = slotted.length - resolvedPieces;
  let setHtml = "";
  if (sets.length === 1) {
    const st = sets[0];
    setHtml = `<h3 class="eh-set-h">${escHtml(st.display)} <span class="muted small">${st.slotted_here} of ${st.roster.length} in this power</span></h3>`
      + enhSetSectionHtml(st);
  } else if (sets.length > 1) {
    setHtml = `<div class="muted small">Sets in this power</div>` + sets.map(st => {
      const nextT = st.tiers.find(t => !t.attained);
      const hint = nextT ? ` — next: ${nextT.values[0] || nextT.bonus_short || nextT.bonus_title}` : " — complete";
      return `<details class="pi-set-row">
        <summary>${escHtml(st.display)} <span class="muted small">${st.slotted_here}/${st.roster.length}${escHtml(hint)}</span></summary>
        ${enhSetSectionHtml(st)}</details>`;
    }).join("");
  }

  panel.innerHTML =
    `<h2>${rec && rec.icon ? `<img class="pi-ico" src="${rec.icon}" alt="">` : ""}
       <span>${escHtml(name)}</span>
       <button class="iconbtn pi-close" onclick="closePowerInfo()" title="close">✕</button></h2>`
    + (rows.length ? `<table>${rows.map(([k, v]) =>
        `<tr><td>${k}</td><td>${escHtml(String(v))}</td></tr>`).join("")}</table>` : "")
    + cardAttributionHtml(atk, LAST_TOTALS)
    + (cats.length ? `<div class="muted small">Allowed enhancements</div>
       <div class="pi-tags">${cats.map(c => `<span class="pi-tag">${escHtml(c)}</span>`).join("")}</div>` : "")
    + setHtml
    + (commons ? `<div class="muted small">plus ${commons} common/special piece${commons > 1 ? "s" : ""} (no set)</div>` : "")
    + (atk ? `<p class="pi-note">Damage numbers include slotted proc contributions and your
       global recharge — they update with every change.</p>` : "")
    + cardProvenanceFooterHtml();
  panel.classList.remove("hidden");
  document.querySelector("main").classList.add("has-info");
}

// A power's slots show as icons (set name only in the hover tooltip), which makes a
// build unrecognizable vs. Mids / the .mbd. Summarize the SETS in plain text under each
// power: "Enfeebled Operation ×5", "Numina's · Miracle · Regen Tissue", etc.
function setSummaryHtml(pw) {
  const filled = (pw.slots || []).filter(Boolean);
  if (!filled.length) return "";
  const order = [], count = {};
  for (const s of filled) {
    const n = s.set_name || "Common IO";
    if (!(n in count)) order.push(n);
    count[n] = (count[n] || 0) + 1;
  }
  const parts = order.map(n => `${escHtml(n)}${count[n] > 1 ? ` ×${count[n]}` : ""}`);
  const plain = order.map(n => `${n}${count[n] > 1 ? ` ×${count[n]}` : ""}`).join(" · ");
  return `<div class="set-summary" title="sets: ${escHtml(plain)}"><span class="muted small">sets:</span> ${parts.join(" · ")}</div>`;
}

// ── HELP SYSTEM ─────────────────────────────────────────────────────────────
// Reusable "?" icons that open a plain-language explanation of anything that isn't
// obvious — the slotting nomenclature, WHY a pattern beats the alternative, and the
// user's options. Content is a glossary keyed by topic; helpIcon(topic) drops a "?"
// anywhere and showHelp() pops the card.
const HELP = {
  "proc-bomb": { title: "💥 Proc bomb",
    what: "Instead of a matched set, the power holds several “chance for damage” procs, each from a different set.",
    why: "A proc rolls a fixed chance to fire every time you use the power (a procs-per-minute formula) and that chance does NOT grow with enhancement. On a fast-recharging or wide-area power, several procs add more damage than the ~95% a full damage set's slots would give. And because set BONUSES are build-wide, you still collect those by slotting sets in your other powers — so a proc bomb trades this one power's set bonuses (which you harvest elsewhere) for a big, enhancement-independent damage spike.",
    options: "Prefer set bonuses here instead? Slot a full set in this power and re-solve — the tool rebalances the rest of the build around it." },
  "committed": { title: "🎯 Full set",
    what: "Five or six pieces of a single enhancement set in one power.",
    why: "Reaching 5–6 pieces unlocks that set's higher bonuses (recharge, defense, HP…). Those bonuses are permanent and count toward your WHOLE character, not just this power — and you still strongly enhance the power itself. This is the backbone of most builds.",
    options: "Short on the rarer pieces? A 5-piece set still gives most of the bonuses; the last piece is often the smallest step." },
  "frankenslot": { title: "🧩 Frankenslot",
    what: "Mixing pieces from two or more different sets in one power, instead of committing to a single set.",
    why: "The FIRST two or three bonuses of most sets are the cheap, high-value ones — a little recovery here, some ranged defense there. A set's 5th and 6th bonuses are usually marginal by comparison. So two 3-piece sets in one power can grab the strong EARLY bonuses of BOTH sets, which often beats one 6-piece set whose top bonuses barely move the needle. Same six slots, more total set bonus.",
    options: "Want a single set's top-tier bonus (e.g. a full set's big recharge) here instead? Pick that set and re-solve." },
  "global-mules": { title: "🌐 Global mules",
    what: "A power holding several unique “global” IOs (Luck of the Gambler: +recharge, Steadfast: +3% defense, Numina: +regen…), one per slot.",
    why: "These uniques give a build-wide effect from a SINGLE slot — they are not set bonuses and need no matching pieces, and each can only be slotted once on your character. So the smart move is to park them in a low-priority power (Health, a defense toggle, Combat Jumping) where they cost you nothing, freeing your important powers for real sets.",
    options: "Nothing to change here usually — this is already an efficient use of an otherwise low-value power." },
  "respec": { title: "🛠️ Respec plan",
    what: "A concrete plan to re-slot this character: exactly which sets change in which powers, the stat gains, and a grocery list of what to craft/buy and what to unslot & sell.",
    why: "When a build has slots that aren't earning set bonuses, a full respec can convert that wasted investment into real defense, recharge, or damage. The plan shows the trade-off up front so you can decide before spending influence.",
    options: "Apply it now, or note the grocery list and do it later in-game — nothing is committed until you say so, and you can undo an applied respec. Your check-off progress is saved to the character." },
  "build-assistant": { title: "🔧 Build Assistant",
    what: "The general-purpose optimizer. Pick what you're building for — a Content preset (Fire Farm, iTrials, Team, General, EB/AV) and optionally a Role — and the solver chooses IO sets and fills every slot toward that goal instantly. No AI; it's deterministic math.",
    why: "It's the fastest way from a set of chosen powers to a finished, optimized build. Turn on “Preserve my IO sets” to complete an imported build without disturbing sets you already picked, or off for a full re-slot from scratch.",
    options: "On a character you resumed, the respec plan card (above the build) is the more tailored path — it compares your CURRENT slotting to the optimum and hands you a grocery list. The Build Assistant is the from-a-goal optimizer. On a wide window it sits to the right of your build; on a narrow one it stacks to the bottom." },
};
function helpIcon(topic) {
  return `<button class="help-i" onclick="showHelp('${topic}',event)" title="What's this?" aria-label="Explain">?</button>`;
}
window.showHelp = function (topic, ev) {
  if (ev) { ev.stopPropagation(); ev.preventDefault(); }
  const h = HELP[topic]; if (!h) return;
  let ov = $("help-overlay");
  if (!ov) {
    ov = document.createElement("div"); ov.id = "help-overlay"; ov.className = "help-overlay";
    ov.addEventListener("click", (e) => { if (e.target === ov) closeHelp(); });
    document.body.appendChild(ov);
  }
  ov.innerHTML = `<div class="help-card"><button class="help-x" onclick="closeHelp()" aria-label="Close">✕</button>`
    + `<h3>${escHtml(h.title)}</h3>`
    + (h.what ? `<p><b>What it is.</b> ${escHtml(h.what)}</p>` : "")
    + (h.why ? `<p><b>Why it's used.</b> ${escHtml(h.why)}</p>` : "")
    + (h.options ? `<p class="help-opt"><b>Your options.</b> ${escHtml(h.options)}</p>` : "")
    + `</div>`;
  ov.classList.remove("hidden");
};
window.closeHelp = function () { const ov = $("help-overlay"); if (ov) ov.classList.add("hidden"); };
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { closeHelp(); if (typeof closeRespecModal === "function") closeRespecModal(); }
});

// The WHY behind a power's slotting — proc-bomb / committed set / global mules — so the
// plan reads as deliberate, not as random scatter (Maelwys review, 2026-07-06). A compact
// chip keeps the brick wall uniform; the full sentence lives in the hover tooltip, and the
// "?" opens the full explanation of the pattern and why it beats the alternative.
const _PLAN_META = {
  "proc-bomb":    ["💥", "Proc bomb", "proc-bomb"],
  "committed":    ["🎯", "Full set", "committed"],
  // A partial single set (e.g. 4 of 6) — a real, deliberate commitment for the
  // early bonuses, but NOT a full set (Joel, 2026-07-20: don't call 3-of-6 "Full").
  "partial-set":  ["🎯", "Partial set", "committed"],
  "frankenslot":  ["🧩", "Frankenslot", "frankenslot"],
  "global-mules": ["🌐", "Global mules", "global-mules"],
  // Running auto/toggle hosting globals — reads as a working power, not dead
  // weight (Maelwys round 3: "Global mules" on Fire Shield implied unpriced).
  "global-host":  ["🌐", "Global host", "global-mules"],
  "mixed":        ["🌐", "Globals", "global-mules"],
  "procs":        ["💥", "Procs", "proc-bomb"],
  "ho-hybrid":    ["🧬", "Proc hybrid", "proc-bomb"],
  "placeholder":  ["▫", "Base slot", null],
};
function slotPlanHtml(pw) {
  const plan = pw.slot_plan;
  if (!plan || !plan.text) return "";
  const [ico, label, topic] = _PLAN_META[plan.kind] || ["🔧", "Slotting", null];
  // The WHOLE chip is the click target, not just the "?" glyph — the bare glyph
  // was a precision-aim tax nobody discovered (field report; also an
  // accessibility problem). The "?" stays for recognition; showHelp stops
  // propagation so it never double-fires.
  const extraCls = topic ? " slot-plan-click" : "";
  const clickAttrs = topic
    ? ` role="button" tabindex="0" onclick="noteHintDone();showHelp('${topic}',event)"`
    : "";
  // No "?" glyph: the whole chip is the one control (hover = summary, click =
  // reasoning). A second click target with its own tooltip was a duplicate
  // control with a mystery label (Joel's trim, 2026-07-08).
  return `<div class="slot-plan slot-plan-${escHtml(plan.kind)}${extraCls}"${clickAttrs} title="${escHtml(plan.text)}">`
    + `<span class="sp-ico">${ico}</span> <span class="sp-label">${label}</span></div>`;
}

// One-time discoverability hint for the note chips (dismisses forever on any
// chip click or the button).
window.noteHintDone = function () {
  try { localStorage.setItem("hc_note_hint", "1"); } catch (e) { /* private mode */ }
  const el = $("note-hint");
  if (el) el.remove();
};

const enhIconUrl = (img) => img ? `/static/icons/enh/${img}` : "";

function slotHtml(powerIdx, slotIdx, slot) {
  if (slot) {
    const url = enhIconUrl(slot.image);
    const inner = url
      ? `<img src="${url}" alt="${slot.piece_name}" loading="lazy"
           onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'slot-abbr',textContent:this.alt.slice(0,2)}))">`
      : `<span class="slot-abbr">${slot.piece_name.slice(0,2)}</span>`;
    // #6 level fidelity: "50+5" = a boosted IO; a level-53 HO shows plain "53".
    const plus = (!slot.attuned && slot.boost > 0) ? `+${slot.boost}` : "";
    const lvl = slot.io_level ? ` · level ${slot.io_level}${plus}${slot.attuned ? " (attuned)" : ""}`
                              : (plus ? ` · boosted ${plus}` : "");
    // Booster PREVIEW: the tag shows the previewed level exactly like an
    // imported boosted IO would ("50+3"), but visually distinct — previewed,
    // not owned (Joel's spec).
    const pv = _previewBoostFor(build.powers[powerIdx].full_name, slotIdx, slot);
    const tag = pv ? `${slot.io_level || 50}+${pv}`
      : slot.attuned ? "A" : (slot.io_level ? `${slot.io_level}${plus}` : "");
    const pvTitle = pv ? `\nPREVIEWING +${pv} boosters — not saved as owned` : "";
    return `<div class="slot filled${slot.unique?' unique':''}${pv?' slot-previewing':''}" title="${slot.set_name}: ${slot.piece_name}${lvl}${pvTitle}\n(click to change, ⓘ for full details, right-click to clear)"
      onclick="openSlot(${powerIdx},${slotIdx})"
      oncontextmenu="clearSlot(event,${powerIdx},${slotIdx})">${inner}${tag ? `<span class="slot-lvl${pv?' lvl-preview':''}">${tag}</span>` : ""}<span class="slot-info" title="full enhancement details" onclick="event.stopPropagation(); openEnhInfo(${powerIdx},${slotIdx})">ⓘ</span></div>`;
  }
  return `<div class="slot" title="empty slot — click to choose"
    onclick="openSlot(${powerIdx},${slotIdx})">+</div>`;
}

window.addPower = function (sel) {
  const psFull = sel.dataset.ps;
  const fullName = sel.value;
  if (!fullName) return;
  const p = (POWERS_CACHE[psFull] || []).find(x => x.full_name === fullName);
  if (!p) return;
  if (build.powers.some(x => x.full_name === fullName)) { sel.value=""; return; }
  recordEdit();
  build.powers.push({
    full_name: p.full_name,
    display_name: p.display_name,
    powerset_full_name: psFull,
    accepted_set_category_ids: p.accepted_set_category_ids || [],
    accepted_set_categories: p.accepted_set_categories || [],
    power_type: p.power_type,
    include_in_totals: p.power_type === 1 || p.power_type === 2,
    slotCount: 1,
    slots: [null],
  });
  sel.value = "";
  renderPowers();
  recompute();
};

window.removePower = function (idx) {
  recordEdit();
  build.powers.splice(idx, 1);
  renderPowers(); recompute();
};

window.changeSlots = function (idx, delta) {
  const pw = build.powers[idx];
  const n = Math.max(1, Math.min(6, pw.slotCount + delta));
  if (n === pw.slotCount) return;                       // clamped (1–6) — nothing to do
  if (n > pw.slotCount && _addedSlots() >= SLOT_BUDGET) {  // budget guard
    alert(`Slot budget full — ${SLOT_BUDGET}/${SLOT_BUDGET} added slots in use.\nRemove a slot from another power first, then add it here.`);
    return;
  }
  recordEdit();
  pw.slotCount = n;
  while (pw.slots.length < n) pw.slots.push(null);
  pw.slots.length = n;
  renderPowers(); recompute();
};

window.clearSlot = function (ev, powerIdx, slotIdx) {
  ev.preventDefault();
  if (!build.powers[powerIdx].slots[slotIdx]) return;   // already empty
  recordEdit();
  build.powers[powerIdx].slots[slotIdx] = null;
  renderPowers(); recompute();
  flashTotals();
};

window.toggleInclude = function (idx, checked) {
  recordEdit();
  // 0.12.18 (Joel's ruling on Maelwys round 4): NO exclusivity — previews
  // stack freely, because every combination the one-at-a-time rule blocked
  // was real play (Build Up+Aim, Farsight+Group Invis+Power Boost, Meltdown+
  // Shadow Meld). Honest labeling replaced restriction: the burst-view note
  // in the totals panel does the warning. The removal also retires the
  // stale-chip desync (a power silently unchecked without a repaint —
  // Maelwys's "still toggled on while not counted").
  build.powers[idx].include_in_totals = checked;
  renderPowers();   // chips carry state-dependent styling (.active) — repaint
  recompute();
};

// ── Edit history (Undo) + live slot budget ──────────────────────────────────
// The build editor is fully freeform (swap powers, add/remove slots, clear IOs).
// recordEdit() snapshots the build BEFORE each change so any edit is reversible,
// and the slot tally makes the 67-added-slot budget visible while you move slots.
let EDIT_HISTORY = [];
const SLOT_BUDGET = 67;   // added slots beyond the 1 free base per power (matches the solver)
function _snapshotBuild() {
  return JSON.parse(JSON.stringify({
    powers: build.powers, pools: build.pools, pools_display: build.pools_display,
    epic: build.epic, epic_display: build.epic_display, incarnates: build.incarnates,
  }));
}
function recordEdit() {                 // call BEFORE any build-mutating edit
  EDIT_HISTORY.push(_snapshotBuild());
  if (EDIT_HISTORY.length > 60) EDIT_HISTORY.shift();
  updateEditBar();
}
function _addedSlots() {
  return (build.powers || []).reduce((n, p) => n + Math.max(0, (p.slotCount || 1) - 1), 0);
}
function updateEditBar() {
  const ub = $("undo-btn"); if (ub) ub.disabled = !EDIT_HISTORY.length;
  const tally = $("slot-tally");
  if (tally) {
    const used = _addedSlots();
    // Teach the shared-pool model at the moment it matters: whenever slots are
    // free, say so and say what to do with them (field-report UX note 5).
    const free = SLOT_BUDGET - used;
    tally.textContent = `${used} / ${SLOT_BUDGET} slots`
      + (free > 0 && (build.powers || []).length
         ? ` — ${free} free: click + on a power to spend` : "");
    tally.classList.toggle("over", used > SLOT_BUDGET);
  }
}
window.undoEdit = function () {
  if (!EDIT_HISTORY.length) return;
  Object.assign(build, EDIT_HISTORY.pop());
  document.querySelectorAll(".pool-sel").forEach((s, i) => { s.value = build.pools[i] || ""; });
  if ($("sel-epic")) $("sel-epic").value = build.epic || "";
  renderPowers(); recompute(); updateEditBar();
};
// Ctrl+Z anywhere on the page = the Undo button (field ask: a mis-click on a slot
// icon should be one keystroke to take back). Skipped while typing in a field so
// text editing keeps its native undo; the set-picker dialog closes first if open.
document.addEventListener("keydown", (e) => {
  if (!(e.ctrlKey || e.metaKey) || e.key.toLowerCase() !== "z" || e.shiftKey || e.altKey) return;
  const t = e.target;
  if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
  if (!EDIT_HISTORY.length) return;
  e.preventDefault();
  const modal = $("modal");
  if (modal && !modal.classList.contains("hidden")) modal.classList.add("hidden");
  undoEdit();
});

// Patron Power Pools (Mace/Mu/Soul/Leviathan Mastery) must be unlocked by completing a Patron
// arc in-game, unlike Ancillary pools — flag the epic selector when one is chosen.
function isPatronEpic(fullName) {
  return /(?:Mace|Mu|Soul|Leviathan)_Mastery/.test(fullName || "");
}
function updateEpicBadge() {
  const note = $("patron-note"); if (!note) return;
  const epic = build.epic || ($("sel-epic") && $("sel-epic").value) || "";
  note.classList.toggle("hidden", !isPatronEpic(epic));
}

// ── Enhancement-converter guidance ──────────────────────────────────────────
// Teach players to MAKE expensive IOs via converters instead of buying 15-20M pieces. Rules
// (Homecoming wiki): In-Set = 3 conv (same set), By Rarity = 1 conv (any set of same rarity),
// By Category = 2 conv (same aspect, crosses Uncommon↔Rare, never Purple/PvP/Winter).
// Enhancement-converter PLANNER — for the pricey IOs in the build, the concrete cheapest path to
// make each via converters (By-Set 3 / By-Rarity 1 / By-Category 2). The backend classifies each
// set's rarity + category + pool sizes and applies the Homecoming rules (no cheap→purple, Category
// never reaches purple/PvP/Winter, ATOs only By-Set), returning per-set steps + a converter/merit est.
const _CONV_TAG = { purple: "Very Rare", pvp: "PvP", winter: "Winter",
  superior_ato: "Superior ATO", ato: "ATO", standard: "Set IO" };
const _CONV_CHART =
  `<table class="conv-modes"><tr><th>Convert…</th><th>Cost</th><th>Gets you</th></tr>`
  + `<tr><td>By-Set</td><td>3</td><td>another piece of the <b>same set</b></td></tr>`
  + `<tr><td>By-Rarity</td><td>1</td><td>any set of the <b>same rarity</b> (purple→purple, PvP→PvP…)</td></tr>`
  + `<tr><td>By-Category</td><td>2</td><td>same <b>aspect</b>, crosses Uncommon↔Rare — <b>never</b> purple/PvP/Winter</td></tr></table>`
  + `<div class="muted small">Converters: 3 = 1 Reward Merit (any merit vendor, L10+) or drops. Common IOs / SO / DO / TO can't be converted.</div>`;

async function renderConverterGuide() {
  const host = $("conv-guide-body"); if (!host) return;
  const hasSets = (build.powers || []).some(p => (p.slots || []).some(s => s && s.set_uid));
  if (!hasSets) {
    host.innerHTML = _CONV_CHART + `<div class="muted small conv-sub">Slot some IO sets first — then this
      shows the cheapest converter path to make each pricey piece, instead of buying it for 10–20M.</div>`;
    return;
  }
  host.innerHTML = _CONV_CHART + `<div class="muted small conv-sub">Planning converter paths…</div>`;
  let res;
  try { res = await api("/converter/plan", postJson({ powers: build.powers })); }
  catch (e) { host.innerHTML = _CONV_CHART; return; }
  const plans = (res && res.plans) || [];
  const sm = (res && res.summary) || {};
  // The WHOLE recommended fit, grouped by rarity so EVERY IO is covered (not just the pricey ones)
  // — a complete "gear this build cheaply" checklist with per-section + grand totals.
  const header = `<div class="conv-total">🧾 <b>Gear this recommended build</b> — ${sm.set_count || plans.length} IO sets, `
    + `≈ <b>${sm.total_converters || 0} converters</b> (~<b>${sm.total_merits || 0} merits</b>) instead of buying them.`
    + ((sm.shopping || []).length ? `<div class="muted small">Cheap seeds to buy: ${sm.shopping.map(escHtml).join(" · ")}.</div>` : "")
    + `</div>`;
  let sections = "";
  for (const [rar, label] of _CONV_SECTIONS) {
    const grp = plans.filter(p => p.rarity === rar);
    if (!grp.length) continue;
    const sc = grp.reduce((a, p) => a + (p.est_converters || 0), 0);
    sections += `<div class="conv-sect"><div class="conv-sect-h">${label}`
      + ` <span class="muted small">· ${grp.length} set${grp.length > 1 ? "s" : ""} · ≈${sc} conv (~${Math.round(sc / 3)} merits)</span></div>`
      + `<div class="conv-list">${grp.map(_convCard).join("")}</div></div>`;
  }
  host.innerHTML = _CONV_CHART + header + (sections || `<div class="muted small conv-sub">No IO sets slotted yet.</div>`);
}

// Rarity sections in acquisition order (hardest first) + a shared per-set card renderer.
const _CONV_SECTIONS = [["purple", "Very Rare (purple)"], ["pvp", "PvP"], ["superior_ato", "Superior ATO"],
  ["ato", "Archetype (ATO)"], ["winter", "Winter"], ["standard", "Set IOs (Rare / Uncommon)"]];
function _convCard(p) {
  return `<div class="conv-item"><div class="conv-head"><b>${escHtml(p.set)}</b> `
    + `<span class="conv-tag ${p.rarity}">${_CONV_TAG[p.rarity] || p.rarity}</span> `
    + `<span class="muted small">${escHtml(p.category)} · lvl ${p.level}`
    + `${(p.pieces || []).length ? ` · ${p.pieces.length} piece${p.pieces.length > 1 ? "s" : ""}` : ""} · ≈${p.est_converters} conv (~${p.est_merits} merits)</span></div>`
    + `<div class="conv-headline">${escHtml(p.headline)}</div>`
    + `<ol class="conv-steps">${(p.steps || []).map(s => `<li>${escHtml(s)}</li>`).join("")}</ol></div>`;
}

// ── Interactive converter tool: "I want this IO → how" (reverse) and "I have this IO → what it
// can become" (forward), for ANY archetype's sets. Backed by /converter/catalog|to|from.
let _CONV_CAT = null;          // {sets, byCat, byUid}
let _convMode = "want";

async function _loadConvCatalog() {
  if (_CONV_CAT) return _CONV_CAT;
  const res = await api("/converter/catalog");
  const sets = (res && res.sets) || [];
  const byCat = {};
  for (const s of sets) (byCat[s.category] = byCat[s.category] || []).push(s);
  _CONV_CAT = { sets, byCat, byUid: Object.fromEntries(sets.map(s => [s.uid, s])) };
  return _CONV_CAT;
}

async function renderConverterTool() {
  const host = $("conv-tool"); if (!host || host.dataset.init) return;   // build once, keep state
  host.dataset.init = "1";
  const cat = await _loadConvCatalog();
  const cats = Object.keys(cat.byCat).sort();
  host.innerHTML =
    `<div class="conv-tool-modes">`
    + `<button class="conv-mode-btn" data-mode="want" onclick="setConvMode('want')">🎯 I want an IO — how do I get it</button>`
    + `<button class="conv-mode-btn" data-mode="have" onclick="setConvMode('have')">🔁 I have an IO — what can it become</button>`
    + `<button class="conv-mode-btn" data-mode="haul" onclick="setConvMode('haul')">🧺 Farm haul → my build's needs</button></div>`
    + `<div class="conv-pickers">`
    + `<select id="conv-cat" onchange="convPickCat()"><option value="">— category —</option>`
    + cats.map(c => `<option>${escHtml(c)}</option>`).join("") + `</select>`
    + `<select id="conv-set" onchange="convPickSet()" disabled><option value="">— set —</option></select>`
    + `<select id="conv-piece" onchange="convPickPiece()" disabled><option value="">— any piece —</option></select>`
    + `<button id="conv-haul-add" style="display:none" onclick="convHaulAdd()">+ add drop</button></div>`
    + `<div id="conv-haul-list" class="conv-haul-list" style="display:none"></div>`
    + `<div id="conv-result" class="conv-result"></div>`;
  setConvMode(_convMode);
}
let _convHaul = [];   // [{uid, name, count}] — the drops you walked out of the farm with
window.setConvMode = function (mode) {
  _convMode = mode;
  document.querySelectorAll(".conv-mode-btn").forEach(b => b.classList.toggle("on", b.dataset.mode === mode));
  const pc = $("conv-piece"); if (pc) pc.style.display = mode === "want" ? "" : "none";
  const ha = $("conv-haul-add"); if (ha) ha.style.display = mode === "haul" ? "" : "none";
  const hl = $("conv-haul-list"); if (hl) hl.style.display = mode === "haul" ? "" : "none";
  if (mode === "haul") { renderConvHaul(); return; }
  const uid = $("conv-set") && $("conv-set").value;
  if (uid) convPickSet(); else { const r = $("conv-result"); if (r) r.innerHTML = ""; }
};

window.convHaulAdd = function () {
  const uid = $("conv-set") && $("conv-set").value;
  if (!uid) return;
  const s = _CONV_CAT.byUid[uid];
  const e = _convHaul.find(x => x.uid === uid);
  if (e) e.count += 1; else _convHaul.push({ uid, name: s.name, count: 1 });
  renderConvHaul();
};
window.convHaulRemove = function (uid) {
  _convHaul = _convHaul.filter(x => x.uid !== uid);
  renderConvHaul();
};

function renderConvHaul() {
  const hl = $("conv-haul-list"); if (!hl) return;
  const chips = _convHaul.length
    ? `<div style="margin:4px 0"><span class="muted small">Your haul:</span> ` + _convHaul.map(h =>
        `<span class="conv-haul-chip">${escHtml(h.name)} ×${h.count} `
        + `<a href="#" onclick="convHaulRemove('${h.uid}');return false">✕</a></span>`).join(" ")
      + ` <button onclick="convHaulMatch()">⚖ Match against my build</button></div>`
    : `<div class="muted small" style="margin:4px 0">Add drops with the pickers above — or just type them below, straight off your salvage window.</div>`;
  // Paste box survives re-renders: keep whatever the user typed.
  const prev = $("conv-haul-paste") ? $("conv-haul-paste").value : "";
  hl.innerHTML = chips
    + `<div class="conv-haul-pastebox">`
    + `<textarea id="conv-haul-paste" rows="3" placeholder="Paste or type your drops — one per line or comma-separated. Counts work: 16x Multi-Strike · Armageddon · 2 Titanium Coating · Devastation x3"></textarea>`
    + `<button onclick="convHaulParse()">📋 Parse list</button>`
    + `<span id="conv-haul-parse-note" class="muted small"></span></div>`;
  if ($("conv-haul-paste")) $("conv-haul-paste").value = prev;
  if (!_convHaul.length) { const r = $("conv-result"); if (r) r.innerHTML = ""; }
}

window.convHaulParse = function () {
  const box = $("conv-haul-paste"); if (!box) return;
  const sets = Object.values(_CONV_CAT.byUid);
  const unknown = [];
  let added = 0;
  for (let raw of box.value.split(/[\n,;]+/)) {
    raw = raw.trim(); if (!raw) continue;
    // counts: "16x Name", "16 Name", "Name x16", "Name ×16"
    let count = 1, name = raw;
    let mm = raw.match(/^(\d+)\s*[x×]?\s+(.+)$/i);
    if (mm) { count = +mm[1]; name = mm[2]; }
    else if ((mm = raw.match(/^(.+?)\s*[x×]\s*(\d+)$/i))) { name = mm[1]; count = +mm[2]; }
    // In-game recipes read "Set Name: Piece Name" (and often "Recipe: Set: Piece") —
    // the SET is what routing needs; strip the piece and any Recipe/level prefix.
    name = name.replace(/^recipe:\s*/i, "").split(":")[0];
    name = name.replace(/\(level \d+\)/i, "").trim().toLowerCase();
    // match: exact → starts-with → contains (unique only)
    let hit = sets.find(s => s.name.toLowerCase() === name)
      || sets.find(s => s.name.toLowerCase().startsWith(name));
    if (!hit) {
      const part = sets.filter(s => s.name.toLowerCase().includes(name));
      if (part.length === 1) hit = part[0];
    }
    if (!hit) { unknown.push(raw); continue; }
    const e = _convHaul.find(x => x.uid === hit.uid);
    if (e) e.count += count; else _convHaul.push({ uid: hit.uid, name: hit.name, count });
    added += count;
  }
  box.value = unknown.join("\n");
  renderConvHaul();
  const note = $("conv-haul-parse-note");
  if (note) note.textContent = added
    ? `added ${added} drop(s)` + (unknown.length ? ` — ${unknown.length} not recognized (left in the box; check spelling or pick via the dropdowns)` : "")
    : (unknown.length ? "nothing recognized — set names need to match the in-game set (e.g. 'Multi-Strike', 'Titanium Coating')" : "");
};

window.convHaulMatch = async function () {
  const r = $("conv-result");
  if (!(build.powers || []).some(p => (p.slots || []).some(Boolean))) {
    r.innerHTML = `<div class="muted">Load or Solve a build first — the matchmaker assigns drops to THIS build's needed sets.</div>`;
    return;
  }
  r.innerHTML = `<div class="muted">Matching…</div>`;
  const res = await api("/converter/assign", postJson({
    powers: build.powers, haul: _convHaul.map(h => ({ set_uid: h.uid, count: h.count })) }));
  if (!res || !res.ok) { r.innerHTML = `<div class="muted">Matchmaker failed.</div>`; return; }
  const rows = (res.assignments || []).map(a =>
    `<tr><td>${a.craft_first ? "🔨 " : ""}${escHtml(a.drop_set)}</td><td>→ <b>${escHtml(a.target_set)}</b>`
    + ` <span class="muted small">(${escHtml((a.target_pieces || []).join(", "))})</span></td>`
    + `<td>≈${a.est_converters} conv (~${a.est_merits} merits)</td>`
    + `<td class="muted small">${escHtml(a.route)}</td></tr>`).join("");
  const sellCount = {};
  (res.sell || []).forEach(s => { sellCount[s.drop_set] = (sellCount[s.drop_set] || 0) + 1; });
  const sell = Object.entries(sellCount).map(([n, c]) => `${escHtml(n)}${c > 1 ? " ×" + c : ""}`).join(", ");
  const keepCount = {};
  (res.keep || []).forEach(k => { keepCount[k.drop_set] = (keepCount[k.drop_set] || 0) + 1; });
  const keep = Object.entries(keepCount).map(([n, c]) => `${escHtml(n)}${c > 1 ? " ×" + c : ""}`).join(", ");
  const unseeded = (res.unseeded || []).slice(0, 10).map(u => escHtml(u.set)).join(", ");
  const ncraft = (res.assignments || []).filter(a => a.craft_first).length;
  r.innerHTML =
    `<div class="conv-card"><b>⚖ ${res.totals.seeded} of ${res.totals.drops} drops become seeds`
    + ` — ≈${res.totals.est_converters} converters (~${res.totals.est_merits} merits) total</b>`
    + (ncraft ? `<div class="muted small">🔨 Recipe drops must be CRAFTED before converting `
      + `(converters only work on built enhancements) — craft the ${ncraft} seed recipe(s) `
      + `below first (common salvage + crafting fee at any invention table).</div>` : "")
    + (rows ? `<table class="conv-assign-table">${rows}</table>` : "")
    + (keep ? `<div class="small">💎 <b>Keep / craft & sell high</b> (purple·PvP·Winter class — valuable even though this build doesn't need them; never vendor): ${keep}</div>` : "")
    + (sell ? `<div class="small">💰 <b>Sell as-is</b> (no needed set reachable at sane cost — fund the rest): ${sell}</div>` : "")
    + (unseeded ? `<div class="muted small">🛒 Still need seeds for: ${unseeded}${(res.unseeded || []).length > 10 ? "…" : ""} — see the build plan above for each.</div>` : "")
    + `</div>`;
};
window.convPickCat = function () {
  const c = $("conv-cat").value, setSel = $("conv-set");
  const sets = (_CONV_CAT.byCat[c] || []);
  setSel.innerHTML = `<option value="">— set —</option>`
    + sets.map(s => `<option value="${s.uid}">${escHtml(s.name)} · ${_CONV_TAG[s.rarity] || s.rarity}</option>`).join("");
  setSel.disabled = !c;
  $("conv-piece").innerHTML = `<option value="">— any piece —</option>`; $("conv-piece").disabled = true;
  $("conv-result").innerHTML = "";
};
window.convPickSet = function () {
  const uid = $("conv-set").value;
  if (!uid) { $("conv-result").innerHTML = ""; return; }
  const s = _CONV_CAT.byUid[uid];
  if (_convMode === "want") {
    const pc = $("conv-piece");
    pc.innerHTML = `<option value="">— any piece —</option>` + s.pieces.map(p => `<option>${escHtml(p)}</option>`).join("");
    pc.disabled = false;
    _convReverse(uid, "");
  } else { _convForward(uid); }
};
window.convPickPiece = function () { _convReverse($("conv-set").value, $("conv-piece").value); };

async function _convReverse(uid, piece) {
  const res = await api("/converter/to", postJson({ set_uid: uid, piece }));
  const p = res && res.plan; if (!p) { $("conv-result").innerHTML = ""; return; }
  $("conv-result").innerHTML = _convCard(p);
}

async function _convForward(uid) {
  const res = await api("/converter/from", postJson({ set_uid: uid }));
  const o = res && res.options; if (!o) { $("conv-result").innerHTML = ""; return; }
  const dest = s => `<button class="conv-dest" onclick="convGoto('${s.uid}')">${escHtml(s.name)} `
    + `<span class="conv-tag ${s.rarity}">${_CONV_TAG[s.rarity] || s.rarity}</span></button>`;
  const rr = o.by_rarity.sets, huge = rr.length > 30;
  $("conv-result").innerHTML =
    `<div class="conv-fwd">`
    + `<div class="conv-fwd-grp"><b>By-Set</b> <span class="muted small">(3 conv) — another piece of this set:</span>`
    + `<div class="conv-pieces">${o.by_set.pieces.map(p => `<span class="conv-piece-chip">${escHtml(p)}</span>`).join("")}</div></div>`
    + `<div class="conv-fwd-grp"><b>By-Category</b> <span class="muted small">(2 conv) — same aspect, any rarity except purple/PvP/Winter:</span>`
    + (o.by_category.note ? `<div class="muted small">${escHtml(o.by_category.note)}</div>`
        : `<div class="conv-dests">${o.by_category.sets.map(dest).join("") || "<span class='muted small'>none at this level</span>"}</div>`)
    + `</div>`
    + `<div class="conv-fwd-grp"><b>By-Rarity</b> <span class="muted small">(1 conv) — any of ${rr.length} sets of the same rarity`
    + (huge ? " (huge pool — prefer By-Category/By-Set)" : "") + `:</span>`
    + `<div class="conv-dests">${rr.slice(0, 30).map(dest).join("")}${huge ? "<span class='muted small'>…</span>" : ""}</div></div>`
    + `</div>`;
}
window.convGoto = function (uid) {   // step to a destination set (forward chaining toward a goal)
  const s = _CONV_CAT.byUid[uid];
  $("conv-cat").value = s.category; convPickCat();
  $("conv-set").value = uid; convPickSet();
};

// In-game, Archetype / Primary / Secondary are fixed at character creation — NO respec changes
// them (only a reroll from level 1 does). Lock them for an EXISTING character (imported, or being
// respec'd); leave pools/epic/powers/slots open, since a respec CAN rewrite those. The signal is
// build._mode (persisted in saves): "new" = open plan; "respec"/"import" = a real character.
function identityLocked() { return build._mode === "respec" || build._mode === "import"; }
function applyIdentityLock() {
  const locked = identityLocked();
  ["sel-archetype", "sel-primary", "sel-secondary"].forEach(id => {
    const el = $(id); if (el) el.disabled = locked;
  });
  const note = $("identity-lock"); if (note) note.classList.toggle("hidden", !locked);
}
window.rerollCharacter = function () {
  if (!confirm("Start a brand-new character from level 1?\n\nArchetype and powersets can't be changed on an existing character — only a reroll can. This clears the current powers & slotting (your saved character stays intact unless you save over it).")) return;
  startFromScratch();   // sets build._mode = "new" and opens the new-character wizard
};

// ---------------------------------------------------------------------------
// Enhancement picker modal (SLOT ENFORCEMENT happens here)
// ---------------------------------------------------------------------------
let MODAL_SETS = [];
let MODAL_COMMONS = [];
let MODAL_SPECIALS = [];

window.openSlot = async function (powerIdx, slotIdx) {
  activeSlot = { powerIdx, slotIdx };
  const pw = build.powers[powerIdx];
  // Feature A affordance: a filled slot offers the FULL DETAIL card (the
  // authentic in-game text + set progress) alongside the swap picker.
  const cur = $("modal-current");
  if (cur) {
    const s = (pw.slots || [])[slotIdx];
    if (s && s.piece_uid) {
      cur.innerHTML = `<span class="muted small">Currently slotted:</span>
        <b>${escHtml(s.piece_name || s.piece_uid)}</b>
        <button class="mc-detail" onclick="closeModal(); openEnhInfo(${powerIdx},${slotIdx})">ⓘ Full details</button>`;
      cur.classList.remove("hidden");
    } else {
      cur.classList.add("hidden");
    }
  }
  $("modal-title").textContent = `Enhancement for: ${pw.display_name}`;
  $("modal-sub").textContent =
    `Showing ONLY sets matching this power's categories: ` +
    (pw.accepted_set_categories.join(", ") || "none") +
    ` — plus the single enhancements (common IOs, Hamidon Origins, D-Syncs) it accepts.`;
  $("modal-search").value = "";
  $("modal").classList.remove("hidden");

  // Ask backend for ONLY the sets whose category fits this power (full_name
  // lets it also work out which single enhancements the power accepts).
  const res = await api("/sets/for-power", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accepted_set_category_ids: pw.accepted_set_category_ids,
                           full_name: pw.full_name }),
  });
  MODAL_SETS = res.sets || [];
  MODAL_COMMONS = res.commons || [];
  MODAL_SPECIALS = res.specials || [];
  renderModalSets();
};

// The "single enhancements" block: common crafted IOs + HO/Titan/Hydra/D-Sync
// specials the power accepts. Rendered as collapsible rows in the same style as
// sets — identical copies stack freely, so no per-set piece rules apply here.
function singlesHtml(q) {
  const rows = [];
  const commons = MODAL_COMMONS.filter(c => !q || c.name.toLowerCase().includes(q));
  if (commons.length) {
    rows.push({
      head: "Common IOs", meta: `${commons.length} kinds · crafted, level 50 · no set bonuses`,
      icon: commons[0].image,
      pieces: commons.map(c => ({ fn: `pickCommon(${JSON.stringify(c.uid)})`,
        image: c.image, name: `${c.name} IO`, sub: (c.enhances || []).join("/") })),
    });
  }
  const fams = {};
  for (const s of MODAL_SPECIALS) {
    if (q && !s.name.toLowerCase().includes(q)) continue;
    (fams[s.family] = fams[s.family] || []).push(s);
  }
  for (const fam of Object.keys(fams).sort()) {
    const list = fams[fam];
    rows.push({
      head: fam, meta: `${list.length} kinds · multi-aspect · identical copies stack freely`,
      icon: list[0].image,
      pieces: list.map(s => ({ fn: `pickSpecial(${JSON.stringify(s.uid)})`,
        image: s.image, name: s.name, sub: (s.enhances || []).join("/") })),
    });
  }
  if (!rows.length) return "";
  let html = `<div class="set-group"><h4>Single enhancements (no set)</h4>`;
  for (const r of rows) {
    const icon = enhIconUrl(r.icon);
    html += `<div class="set-item">
      <div class="si-head" onclick="this.nextElementSibling.classList.toggle('open')">
        ${icon ? `<img class="si-icon" src="${icon}" alt="" loading="lazy">` : ""}
        <div>
          <span class="si-name">${r.head}</span>
          <div class="si-meta">${r.meta}</div>
        </div>
      </div>
      <div class="piece-list">
        ${r.pieces.map(p => {
          const pIcon = enhIconUrl(p.image);
          return `
          <div class="piece" onclick='${p.fn}'>
            ${pIcon ? `<img class="piece-icon" src="${pIcon}" alt="" loading="lazy">` : ""}
            <span>${p.name}</span>
            <span class="muted">${p.sub}</span>
          </div>`;
        }).join("")}
      </div>
    </div>`;
  }
  return html + `</div>`;
}

function renderModalSets() {
  const q = ($("modal-search").value || "").toLowerCase();
  const host = $("modal-sets");
  const singles = singlesHtml(q);
  if (!MODAL_SETS.length && !singles) {
    host.innerHTML = `<p class="muted">No enhancement sets fit this power's
      categories, and it accepts no single enhancements we know.</p>`;
    return;
  }
  if (!MODAL_SETS.length) {
    host.innerHTML = singles + `<p class="muted">No enhancement sets fit this
      power's categories — the single enhancements above are what it takes.</p>`;
    return;
  }
  const groups = {};
  for (const s of MODAL_SETS) {
    if (q && !s.name.toLowerCase().includes(q)) continue;
    (groups[s.category] = groups[s.category] || []).push(s);
  }
  let html = "";
  for (const cat of Object.keys(groups).sort()) {
    html += `<div class="set-group"><h4>${cat}</h4>`;
    for (const s of groups[cat]) {
      const setIcon = enhIconUrl(s.image);
      html += `<div class="set-item">
        <div class="si-head" onclick="this.nextElementSibling.classList.toggle('open')">
          ${setIcon ? `<img class="si-icon" src="${setIcon}" alt="" loading="lazy">` : ""}
          <div>
            <span class="si-name">${s.name}</span>
            <div class="si-meta">${s.piece_count} pieces · lvl ${s.level_min}-${s.level_max} · ${s.category}</div>
          </div>
        </div>
        <div class="piece-list">
          ${s.pieces.map((p, pi) => {
            const pIcon = enhIconUrl(p.image || s.image);
            // In-game rule: each SET piece slots at most once per power (the
            // stack-freely rule covers commons/HOs/D-Syncs only). Pieces this
            // power already holds are shown but not pickable — honest, not
            // hidden (field report: the picker let the same LotG in twice).
            const dup = _pieceSlottedHere(p.uid, pi === undefined ? null : pi, s.uid);
            return `
            <div class="piece ${p.unique?'unique':''}${dup?' piece-dup':''}"
              ${dup ? `title="Already slotted in this power — the game won't let a set piece repeat within one power."`
                    : `onclick='pickPiece(${JSON.stringify(s.uid)}, ${JSON.stringify(s.name)}, ${pi})'`}>
              ${pIcon ? `<img class="piece-icon" src="${pIcon}" alt="" loading="lazy">` : ""}
              <span>${p.name}</span>
              <span class="muted">${dup ? "✔ slotted here" : (p.enhances||[]).join("/")}</span>
            </div>`;
          }).join("")}
        </div>
      </div>`;
    }
    html += `</div>`;
  }
  host.innerHTML = (singles + html) || `<p class="muted">Nothing matches "${q}".</p>`;
}

// v35 UX batch §3 (Joel's ruling): hand edits to individual IOs recompute
// totals IMMEDIATELY — there is no apply button anywhere on that path (verified:
// every pick/clear below already calls recompute()). This flash makes the
// immediacy VISIBLE: the totals panel pulses once when a hand edit lands.
function flashTotals() {
  const el = $("stats");
  if (!el) return;
  el.classList.remove("totals-flash");
  void el.offsetWidth;             // restart the animation
  el.classList.add("totals-flash");
}

// Manual single-enhancement picks (#7). Slot shapes mirror what imports and the
// optimizer already produce, so every downstream consumer (engine totals,
// validation, Mids export, trims) treats hand picks identically.
window.pickCommon = function (uid) {
  const c = MODAL_COMMONS.find(x => x.uid === uid);
  if (!c || !activeSlot) return;
  const { powerIdx, slotIdx } = activeSlot;
  recordEdit();
  build.powers[powerIdx].slots[slotIdx] = {
    set_uid: null, set_name: "Common IO",
    piece_uid: c.uid, piece_name: `${c.name} IO`,
    category_id: null, enhances: c.enhances, unique: false,
    image: c.image || "",
    io_level: 50,             // crafted commons are built at 50; boosts store at 50
  };
  closeModal();
  renderPowers();
  recompute();
  flashTotals();
};

window.pickSpecial = function (uid) {
  const s = MODAL_SPECIALS.find(x => x.uid === uid);
  if (!s || !activeSlot) return;
  const { powerIdx, slotIdx } = activeSlot;
  recordEdit();
  build.powers[powerIdx].slots[slotIdx] = {
    set_uid: null, set_name: s.family,
    piece_uid: s.uid, piece_name: s.name,
    category_id: null, enhances: s.enhances, unique: false,
    image: s.image || "",
    _ho: true,                // grade-flat value — never level-scaled, never swapped out
  };
  closeModal();
  renderPowers();
  recompute();
  flashTotals();
};

// In-game rule: a SET piece slots at most once per power. Checks the active
// power's OTHER slots for the piece (the slot being edited may hold it — a
// re-pick of the same piece into the same slot is a no-op, not a duplicate).
function _pieceSlottedHere(pieceUid, _pi, _setUid) {
  if (!activeSlot) return false;
  const { powerIdx, slotIdx } = activeSlot;
  return (build.powers[powerIdx].slots || []).some((sl, i) =>
    sl && i !== slotIdx && sl.piece_uid === pieceUid);
}

window.pickPiece = function (setUid, setName, pieceIdx) {
  const s = MODAL_SETS.find(x => x.uid === setUid);
  const piece = s.pieces[pieceIdx];
  // Defense in depth behind the disabled picker row: the game won't allow a
  // set piece twice in one power, so neither do we.
  if (_pieceSlottedHere(piece.uid)) return;
  const { powerIdx, slotIdx } = activeSlot;
  recordEdit();
  build.powers[powerIdx].slots[slotIdx] = {
    set_uid: s.uid,
    set_name: setName,
    piece_uid: piece.uid,
    piece_name: piece.name,
    category_id: s.category_id,
    enhances: piece.enhances,
    unique: piece.unique,
    image: piece.image || s.image || "",
    // buy level = the set's max (Mids data stores levels 0-based) — shown as the
    // tag under the icon, same as common IOs
    io_level: s.level_max != null ? Math.min(50, s.level_max + 1) : null,
  };
  closeModal();
  renderPowers();
  recompute();
  flashTotals();
};

function closeModal() { $("modal").classList.add("hidden"); activeSlot = null; }

// ---------------------------------------------------------------------------
// Stats + validation
// ---------------------------------------------------------------------------
async function recompute() {
  renderEndgameWarnings();   // warn if a leveling character previews epic/incarnate content
  const hasPowers = build.powers.length > 0;
  const jb = $("journey-btn");   // the header road icon rides with having a plan
  if (jb) jb.style.display = hasPowers ? "" : "none";
  const ob = $("opt-btn");   // AI refine — hidden entirely when the AI seam is off
  if (ob) ob.style.display = (hasPowers && AI_ON) ? "block" : "none";
  const sb = $("solve-btn");
  if (sb) sb.style.display = hasPowers ? "block" : "none";
  const hint = $("fit-hint");   // explains Solve-vs-AI — pointless without the AI option
  if (hint) hint.style.display = (hasPowers && AI_ON) ? "block" : "none";
  const presLbl = $("preserve-toggle-label");
  // v35: locks/preserve apply to any RETOOL build — imported OR resumed (Joel's
  // mode ruling; a from-scratch/AI build has no prior investment to keep).
  const showPres = hasPowers && isRetool();
  if (presLbl) presLbl.style.display = showPres ? "flex" : "none";
  const klLbl = $("keeplayout-label");
  if (klLbl) klLbl.style.display = showPres ? "flex" : "none";
  updateAssistantMode();   // header/intro/labels track the CREATE-vs-RETOOL mode
  const rb = $("reset-btn");
  if (rb) rb.style.display = (hasPowers && IMPORTED_POWERS) ? "block" : "none";
  const cb = $("changes-btn");
  if (cb) cb.style.display = (hasPowers && IMPORTED_POWERS && CHANGES_AVAILABLE) ? "block" : "none";
  const payload = buildPayload();
  const [totals, validation] = await Promise.all([
    api("/build/calculate", postJson(payload)),
    api("/build/validate", postJson(payload)),
  ]);
  renderStats(totals);
  renderValidation(validation);
  LAST_TOTALS = (totals && (totals.totals || totals)) || null;  // feed the tray rotation + notes
  LAST_CALC = totals || null;   // v36: carries inherent_mechanics for the offense block
  build._accoladeHp = (LAST_TOTALS && LAST_TOTALS.accolade_hp) || 0;  // v34: live accolade HP for the panel line
  updateInfoCards(LAST_TOTALS);
  // Server-corrected pick levels (older saves carry naive assignments — e.g. both
  // Poison powers badged level 1). Adopt them and repaint the wall once.
  let repaint = false;
  if (totals && totals.pick_levels) {
    build.powers.forEach(p => {
      const lv = totals.pick_levels[p.full_name];
      if (lv && p.pick_level !== lv) { p.pick_level = lv; repaint = true; }
    });
  }
  // Slotting rationale (transparency chips) for whatever is on screen — so a Resumed or
  // Imported build shows them, not just a freshly-solved one.
  if (totals) {
    const plans = totals.slot_plans || {};
    const kinds = totals.power_kinds || {};
    build.powers.forEach(p => {
      const plan = plans[p.full_name] || null;
      if (JSON.stringify(p.slot_plan || null) !== JSON.stringify(plan)) {
        p.slot_plan = plan; repaint = true;
      }
      const kind = kinds[p.full_name] || null;
      if (JSON.stringify(p.totals_kind || null) !== JSON.stringify(kind)) {
        p.totals_kind = kind; repaint = true;
      }
    });
  }
  if (repaint) renderPowers();
  // Live-rail rule (Joel's pinned acceptance criterion): every recompute —
  // which every build edit triggers — re-renders whichever rail view is open,
  // so the IO card's roster/tiers and power-info's set view never go stale.
  renderRail();
  // Respec: show the active worksheet if there is one, else a factual under-investment nudge.
  renderRespecUI(totals && totals.respec_hint);
  refreshBuildViews();   // keep the always-visible respec-order + tray sections live
  if (ACCOLADES_ROWS && ACCOLADES_ROWS.length) renderAccolades();  // keep the panel synced (HP line + alignment greying)
}

// ── Accolades panel (v34 scaffold, DISPLAY-ONLY) ─────────────────────────────
// Joel's scope ruling: the ENTIRE accolade roster ships (badge-only rows too) —
// a full goal tracker that happens to price the rows that have prices — with a
// scrollbar and a search field. Tiering: build-affecting passives on top, click
// accolades next, badge-only last, each honestly marked.
// Data-source ruling: roster/effects/descriptions come from the GAME (the
// client bins via /accolades), never the wiki. Attainment guidance is absent
// BY DESIGN today — Phase-0 proved the client carries what an accolade grants,
// not how it is earned; those pop-ups await a labelled guidance-tier source.
// NOTHING here touches totals: a checkmark is a display-only note in this
// scaffold. The apply-all preview + real totals/labels are the v34 model half.
let ACCOLADES_ROWS = null;
let ACCOLADES_CHECKED = new Set();
let ACCOLADES_FILTER = "";

// ⚠ ONLY A SUCCESS IS EVER CACHED (Joel's walk-3 failure, root-caused
// 2026-07-16). The old body was:
//     if (ACCOLADES_ROWS) return ACCOLADES_ROWS;
//     ACCOLADES_ROWS = (r && r.ok) ? r.rows : [];
// One failed fetch cached `[]` — which is TRUTHY, so the guard returned the
// empty array FOREVER, for the life of the page, with no retry. Every
// downstream feature then silently no-opped: the panel hid itself
// (`if (!rows.length)`), the preselect ticked nothing, the provenance line said
// "accolades: none ticked" and the attributed lines vanished — all while the
// server was healthy and serving 28 rows. Joel hit it because a 5080 RESTART
// (mine, seconds before I told him it was ready) failed the one fetch his page
// made; my own checks always loaded after the restart, so I never saw it.
// `null` = never loaded, retry. An array = a real answer, cache it (even if the
// roster is legitimately empty). A transient failure returns empty for THIS
// call and leaves the cache untouched so the next call retries.
let ACCOLADES_LOAD_FAILED = false;
async function loadAccolades() {
  if (ACCOLADES_ROWS !== null) return ACCOLADES_ROWS;
  const r = await api("/accolades").catch(() => null);
  if (r && r.ok && Array.isArray(r.rows)) {
    ACCOLADES_ROWS = r.rows;
    ACCOLADES_LOAD_FAILED = false;
    return ACCOLADES_ROWS;
  }
  ACCOLADES_LOAD_FAILED = true;   // surfaced in the panel; retried on next call
  return [];
}

// Joel's grey-out ruling, made GAME-TRUE (2026-07-17, "check the game"): each
// accolade record carries an alignment gate (activate_requires). A character is
// one alignment, so an accolade for the OTHER side is dormant — greyed out. This
// is why only one of a hero/villain twin ever applies (Portal Jockey greyed on a
// villain, Born In Battle greyed on a hero); the no-gate accolades (Labyrinth
// Conqueror, Mazebreaker) are never greyed and legally STACK, and same-alignment
// accolades all stack too. Returns the off-alignment ("hero"/"villain") or null.
function _accInactiveAlign(a) {
  const al = charAlignment();
  return (a.alignment && a.alignment !== al) ? a.alignment : null;
}

function _accRow(a) {
  const on = ACCOLADES_CHECKED.has(a.key);
  const off = _accInactiveAlign(a);   // this accolade's side ≠ the character's
  const note = a.tier === "click" ? `not in passive totals`
    : a.tier === "badge_only" ? `no build effect` : "";
  // Correction 2's whole point is LEGIBILITY: the checkbox, the name and the
  // effect stay together on one readable line, the name is allowed to wrap
  // rather than be clipped, and nothing overflows sideways.
  const mine = charAlignment();
  const tip = off
    ? `${off === "villain" ? "Villain" : "Hero"}-side accolade — your ${mine === "villain" ? "villain" : "hero"} character can't have it. Switch sides with the alignment button if this character is a ${off}.`
    : a.display + (a.description ? " — " + a.description : "");
  return `<div class="acc-row ${a.tier}${off ? " greyed" : ""}" data-acc="${escHtml(a.key)}">
      <input class="acc-check" type="checkbox" id="accbx-${escHtml(a.key)}" ${on ? "checked" : ""}
        ${off ? "disabled" : ""} onchange="toggleAccolade('${escHtml(a.key)}')">
      <label class="acc-body" for="accbx-${escHtml(a.key)}" title="${escHtml(tip)}">
        <span class="acc-name">${escHtml(a.display)}</span>${
        off ? `<span class="acc-note">${off}-side only</span>`
        : note ? `<span class="acc-note">${note}</span>`
             : `<span class="acc-eff">${escHtml(a.effect_short || "")}</span>`}</label>
      <button class="acc-info" onclick="accHowTo('${escHtml(a.key)}')"
        title="How to earn it">ⓘ</button></div>`;
}

// (The dead-space span maths that lived here is GONE with placement correction
// 2 — the panel is a full-width member of the summary course now, so its width
// is the course's width and needs no computation, no resize retrigger, and no
// unverifiable ResizeObserver. The simplest layout that is legible wins.)

function renderAccolades() {
  const card = $("accolades-card");
  if (!card) return;
  const rows = ACCOLADES_ROWS || [];
  // A LOAD FAILURE MUST NOT LOOK LIKE "no accolades exist" (walk-3 root cause:
  // the whole feature vanished silently and read as "not built yet"). If the
  // roster couldn't load, SAY SO and offer the retry — never hide.
  if (!rows.length && ACCOLADES_LOAD_FAILED && build.powers.length) {
    card.classList.remove("hidden");
    card.innerHTML = `<div class="acc-head"><span class="ovc-head">ACCOLADES</span></div>
      <div class="acc-empty">Couldn't load the accolade list — the app couldn't reach the
      server (a restart or a hiccup). <button class="linkbtn" onclick="retryAccolades()">Try
      again</button></div>`;
    return;
  }
  if (!rows.length || !build.powers.length) { card.classList.add("hidden"); return; }
  card.classList.remove("hidden");
  const f = ACCOLADES_FILTER.trim().toLowerCase();
  const shown = f ? rows.filter(a => (a.display || "").toLowerCase().includes(f)
                                  || (a.description || "").toLowerCase().includes(f)) : rows;
  const groups = [["passive", "Affects this build"], ["click", "Click powers"],
                  ["badge_only", "Badges"]];
  let body = "";
  for (const [tier, label] of groups) {
    const g = shown.filter(a => a.tier === tier);
    if (!g.length) continue;
    body += `<div class="acc-group">${label} (${g.length})</div>` + g.map(_accRow).join("");
  }
  if (!body) body = `<div class="acc-empty">No accolade matches “${escHtml(ACCOLADES_FILTER)}”.</div>`;
  const nPassiveChecked = [...ACCOLADES_CHECKED].filter(k =>
    (rows.find(a => a.key === k) || {}).tier === "passive").length;
  const hp = build._accoladeHp || 0;
  const applied = nPassiveChecked
    ? `<span class="acc-applied">✓ ${nPassiveChecked} in your numbers${hp ? ` (+${hp} HP)` : ""}</span>`
    : `<span class="acc-hint">tick the ones your character has — checked accolades feed the totals</span>`;
  card.innerHTML =
    `<div class="acc-head">
       <span class="ovc-head">ACCOLADES <span class="acc-count">${ACCOLADES_CHECKED.size}/${rows.length}</span></span>
       <input id="acc-search" class="acc-search" type="search" placeholder="Search accolades…"
         value="${escHtml(ACCOLADES_FILTER)}" oninput="accSearch(this.value)">
       <button class="acc-preview-btn" onmouseenter="accPreview(true)" onmouseleave="accPreview(false)"
         onfocus="accPreview(true)" onblur="accPreview(false)"
         title="Hold to see every build-affecting accolade applied at once — a preview, nothing is committed">👁 Preview all</button>
       ${applied}
     </div>
     <div class="acc-scroll">${body}</div>`;
  const inp = $("acc-search");
  if (inp && ACCOLADES_FILTER) { inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); }
}

// v34 item 3: the apply-all PREVIEW. Ephemeral BY CONSTRUCTION (booster-preview
// pattern) — it recomputes stats with every build-affecting accolade applied
// WITHOUT touching ACCOLADES_CHECKED, so releasing restores exactly what was
// checked. Nothing is committed; the button is press-and-hold.
async function accPreview(on) {
  const passive = (ACCOLADES_ROWS || []).filter(a => a.tier === "passive").map(a => a.key);
  if (!passive.length) return;
  const payload = buildPayload();
  payload.accolades = on ? passive : [...ACCOLADES_CHECKED];
  const totals = await api("/build/calculate", postJson(payload)).catch(() => null);
  if (!totals) return;
  const card = $("stats");
  if (card) card.classList.toggle("acc-previewing", on);
  renderStats(totals);
  const lt = (totals && (totals.totals || totals)) || null;
  if (lt) { build._accoladeHp = lt.accolade_hp || 0; }
}

// v34 item 4: the attain-it pop-up. Text is GAME-SOURCED ONLY (Joel's no-wiki
// amendment): the client's own badge prose where the data proves the binding,
// Joel's live-game badge-window text where it doesn't, and an honest
// "not yet documented from game data" where neither covers it — never borrowed
// prose. The source is shown so the user knows which they're reading.
function accHowTo(k) {
  const a = (ACCOLADES_ROWS || []).find(x => x.key === k);
  if (!a) return;
  // Joel's pop-up content spec (his walk, 2026-07-16): the pop-up's job is to
  // show WHAT THE ACCOLADE TRACKS and how you acquire it — a to-do list, like a
  // badge saying "you have healed 100k and can now display Surgeon". The grants
  // line stays, but small and secondary.
  const undocumented = !a.attain_source || a.attain_source === "undocumented";
  const chain = a.badge_chain || [];
  let body;
  if (chain.length) {
    body = `${a.attain_summary ? `<p>${escHtml(a.attain_summary)}</p>` : ""}
      <p class="acc-howto-lead">How to acquire — earn these badges:</p>
      <ul class="acc-chain">${chain.map(b =>
        `<li><strong>${escHtml(b.badge)}</strong><span>${escHtml(b.tracks)}</span></li>`).join("")}</ul>
      ${a.attain_note ? `<p class="muted small">${escHtml(a.attain_note)}</p>` : ""}`;
  } else if (!undocumented && (a.attain || a.attain_summary)) {
    // a sourced answer that ISN'T a badge chain — e.g. "this badge is not
    // defined in the game, it cannot be earned". That is a real answer and must
    // render; the earlier fallback printed a's empty `attain` and produced a
    // BLANK pop-up, which is worse than saying nothing.
    body = `<p${a.attain_unobtainable ? ' class="acc-undoc"' : ''}>`
      + `${escHtml(a.attain || a.attain_summary)}</p>`
      + (a.attain_note ? `<p class="muted small">${escHtml(a.attain_note)}</p>` : "");
  } else {
    body = `<p class="acc-undoc">Requirements not yet documented from game data.</p>
       <p class="muted small">We only show what a source we trust actually says. The
       game client carries this accolade's effects but not its badge requirements,
       so this one is pending an in-game check.</p>`;
  }
  const src = {"game (clientmessages-en.bin)": "the game client's own badge text",
               "joel-live-game (badge window)": "the in-game badge window",
               "wiki-hc": "the Unofficial Homecoming Wiki — not yet confirmed in game"}[a.attain_source];
  if (src) body += `<p class="muted small acc-src">Source: ${escHtml(src)}.</p>`;
  const eff = a.effect_short
    ? `<p class="acc-grants muted small">Grants: ${escHtml(a.effect_short)}</p>` : "";
  // same overlay pattern as the respec modal (dynamically created .help-overlay,
  // backdrop click closes) — reuse, don't invent a second modal system
  let ov = $("acc-howto");
  if (!ov) {
    ov = document.createElement("div");
    ov.id = "acc-howto"; ov.className = "help-overlay";
    ov.addEventListener("click", (e) => { if (e.target === ov) closeAccHowTo(); });
    document.body.appendChild(ov);
  }
  ov.innerHTML = `<div class="respec-modal-card respec-card">
      <div class="rc-head"><span class="rc-ico">🏅</span>
        <span class="rc-title">${escHtml(a.display)}</span>
        <button class="rc-x" onclick="closeAccHowTo()" title="Close">✕</button></div>
      <div class="rc-body">${eff}${body}</div></div>`;
}
window.closeAccHowTo = function () {
  const ov = $("acc-howto"); if (ov) ov.remove();
};

// The character's alignment (hero/villain) — the same reskin the Hero/Villain
// side card set at entry. Accolades gate on it (game rule).
function charAlignment() {
  try { return localStorage.getItem("cohAlignment") || "hero"; }
  catch (e) { return "hero"; }
}

// v34 item 5: the standard accolades a generated level-50 build assumes — now
// ALIGNMENT-AWARE (Joel's "check the game"). The server flags both the hero
// standard set and their villain equivalents; we preselect the four that match
// THIS character's alignment, so a villain build assumes Born In Battle / Invader
// / High Pain Threshold / Marshal, not the hero names it can't use.
async function preselectStandardAccolades() {
  const rows = await loadAccolades();
  const al = charAlignment();
  for (const a of rows) {
    if (a.standard_assumed && (!a.alignment || a.alignment === al)) {
      ACCOLADES_CHECKED.add(a.key);
    }
  }
}

// the retry the poisoned cache never had
window.retryAccolades = async function () {
  ACCOLADES_ROWS = null; ACCOLADES_LOAD_FAILED = false;
  await loadAccolades();
  await preselectStandardAccolades();
  renderAccolades();
  recompute();
};

function accSearch(v) { ACCOLADES_FILTER = v; renderAccolades(); }
function toggleAccolade(k) {
  if (ACCOLADES_CHECKED.has(k)) ACCOLADES_CHECKED.delete(k); else ACCOLADES_CHECKED.add(k);
  // v34 item 2: a checkmark means "this is in the numbers you're looking at".
  // Only accolades our math prices (the passive tier) move totals; ticking a
  // click/badge row is remembered but changes nothing, and the row says so.
  const row = (ACCOLADES_ROWS || []).find(a => a.key === k);
  if (row && row.tier === "passive") recompute();
  renderAccolades();
}

// ── Attribution v1 — v34 UI deliverable 4, stat-level ───────────────────────
// "Attributed lines, not buried numbers": where a source lands in a stat, it
// gets a NAMED line under that stat. Joel's template case is the Musculature
// finding — an Alpha that raises damage but was invisible in the DPS block.
// Every number here comes from the engine's own ledger (totals._accolade_ledger,
// totals.damage_buff), never recomputed client-side — a second computation is a
// second source of truth, and that is the defect this feature exists to kill.
function attributionRowsHtml(statName, t) {
  const rows = [];
  if (statName === "Max HP") {
    const led = t.accolade_ledger || [];
    const hp = Math.round(t.accolade_hp || 0);
    if (hp) {
      const names = led.map(x => x.display || x.name).filter(Boolean);
      rows.push({label: "↳ Accolades", val: `+${hp} HP`,
                 title: names.length ? `From: ${names.join(", ")}` : ""});
    }
  }
  return rows.map(r =>
    `<div class="o-row attr-row" ${r.title ? `title="${escHtml(r.title)}"` : ""}>
       <span>${r.label}</span><span>${escHtml(r.val)}</span></div>`).join("");
}

// The NAMED sources of the engine's global +damage% regime — read from the
// engine's own ledger (totals.damage_buff_sources), never guessed. The total
// can be the SUM of several incarnates (Alpha + Hybrid Assault), so every
// contributor is named — assuming a single source was the exact misattribution
// Joel's "from game data, not a guess" directive caught (v34 item 5).
function damageSourceLabel(t) {
  const srcs = (t && t.damage_buff_sources) || [];
  if (srcs.length) {
    return srcs.map(s => `${escHtml(s.slot)} (${escHtml(s.name)})`).join(" + ");
  }
  // ledger absent (older cache) but a buff exists: name it honestly, no guess
  return (t && t.damage_buff) ? "Incarnate (peak)" : null;
}

// The DPS block's named contributions (the Musculature case). Build-scope, so
// it shows the raw build +damage% (the game's per-attack cap is a card-scope
// concern — see cardAttributionHtml).
function dpsAttributionHtml(t) {
  const dmg = (t && t.damage_buff) || 0;
  if (!dmg) return "";
  const label = damageSourceLabel(t);
  if (!label) return "";
  return `<div class="o-row attr-row" title="A global +damage% the engine applies to every attack (incarnate peak values). This is the line that used to be invisible.">
      <span>↳ ${label}</span><span>+${(dmg * 100).toFixed(1)}% damage</span></div>`;
}

// ── Per-power-card provenance — v34 item 5 (Joel's ruling 2026-07-17 + the
// 5:35 AM amendment's three laws). Two truthful layers, nothing invented:
//   1. CARD-SCOPE attribution: a named line appears under a card's numbers
//      ONLY when a global regime provably multiplies into THIS power's own
//      numbers — today the engine's +damage% regime (Alpha/incarnate damage).
//      Law 1 (READ, NEVER RE-ADD): it reads the engine's per-attack ledger
//      (atk.global_dmg_raw / global_dmg_eff), never a client recompute.
//      Law 3 (GAME BOUNDARIES): it shows the EFFECTIVE value the engine
//      applied after the game's damage cap, and says so when raw ≠ effective.
//      Build-level globals that never touch this power's own numbers
//      (accolade +MaxHP/+MaxEnd class) are NEVER faked into a per-card share
//      (law 2) — they get the footer instead.
//   2. The FOOTER: every ⓘ card states, in one honest line, that build-wide
//      bonuses live in Build Vitals — so no card is silent about what it
//      does not show. When incarnates are off, it also says these numbers
//      are WITHOUT them (the not-yet-acquired story, visible).
function cardAttributionHtml(atk, t) {
  if (!atk) return "";
  const raw = atk.global_dmg_raw || 0;
  const eff = atk.global_dmg_eff || 0;
  if (raw <= 0 || eff <= 0) return "";   // no global damage, or capped away here
  const src = damageSourceLabel(t) || "Incarnate (peak)";  // named, not guessed
  const rP = (raw * 100).toFixed(1), eP = (eff * 100).toFixed(1);
  const capped = eff + 1e-6 < raw;       // the game's damage cap bit this power
  const body = capped
    ? `↳ ${escHtml(src)} +${rP}% damage — the game's damage cap holds it to +${eP}% on this power`
    : `↳ ${escHtml(src)} +${eP}% damage — included in these numbers`;
  return `<div class="pi-attr" title="Read from the engine's own per-attack ledger; the game's damage cap is applied where it bites. Untick the incarnate preview and this line (and the numbers) drop.">${body}</div>`;
}

function cardProvenanceFooterHtml() {
  const incOn = !!(build && build.include_incarnates);
  const accN = (typeof ACCOLADES_CHECKED !== "undefined") ? ACCOLADES_CHECKED.size : 0;
  const bits = [];
  bits.push(accN
    ? `build-wide bonuses (accolades: ${accN} applied) don't change this power's own numbers — they live in Build Vitals`
    : `build-wide bonuses (accolades, when ticked) don't change this power's own numbers — they live in Build Vitals`);
  if (!incOn) bits.push(incarnatesUnlocked()
    ? `incarnates are off, so these numbers are without them — the preview toggle is in Build Vitals`
    : `incarnates unlock at level 50, so these numbers are without them`);
  return `<div class="pi-prov muted small">${bits.join(" · ")}</div>`;
}

// ── "What's in these numbers" — v34 UI deliverable 1 ────────────────────────
// Joel's standing question, killed permanently: it was never clear whether the
// Epic picks and incarnate recommendations actually reached the totals. This
// line says so, at the top of Build Vitals, driven by LIVE engine state (never
// a hardcoded sentence) so it updates the instant any regime toggles.
// The law it serves: UI state == engine state, with provenance.
function provenanceLineHtml(t) {
  const parts = [];
  // Epic picks are ordinary slotted powers — they have always been in totals.
  parts.push(`<span class="prov-in">✓ powers, slotting, set bonuses & Epic picks</span>`);

  // Accolades: the panel's checkmarks ARE the source of truth (item 2).
  const n = (typeof ACCOLADES_CHECKED !== "undefined") ? ACCOLADES_CHECKED.size : 0;
  const accHp = (t && t.accolade_hp) ? Math.round(t.accolade_hp) : 0;
  parts.push(n
    ? `<span class="prov-in">✓ accolades: ${n} applied${accHp ? ` (+${accHp} HP)` : ""}</span>`
    : `<span class="prov-off">accolades: none ticked</span>`);

  // Incarnates: excluded from passive totals unless the peak toggle is on. When
  // a leveling character previews them below 50, say so honestly (endgame
  // preview) rather than implying they're already available.
  const incOn = !!(build && build.include_incarnates);
  const incPreview = incOn && !incarnatesUnlocked();
  parts.push(incOn
    ? (incPreview
        ? `<span class="prov-off">incarnates: peak values folded in — endgame preview (unlock at 50)</span>`
        : `<span class="prov-in">✓ incarnates: peak values folded in</span>`)
    : (incarnatesUnlocked()
        ? `<span class="prov-off">incarnates: off — tick “Include incarnates (peak)” to preview</span>`
        : `<span class="prov-off">incarnates: off — unlock at level 50</span>`));

  // Amplifiers: their own toggle since the split (item 3).
  if (build && build.include_amplifiers)
    parts.push(`<span class="prov-in">✓ amplifiers</span>`);

  return `<div class="prov-line" title="Exactly what is and is not folded into the numbers below — it updates the moment you change any of them.">${parts.join(" · ")}</div>`;
}

// ── Overview bar: the build's vitals in one horizontal line (Sidekick-style) ─
// Color logic: defense vs the current-meta 35 (green ≥35, amber ≥25), resistance
// vs the AT cap fraction, recharge green ≥70. Dim = not there yet, never red — the
// bar is a dashboard, not a nag.
function _ovCell(label, val, cls) {
  return `<span class="ov-cell ${cls}"><span class="ov-num">${val}</span><span class="ov-lab">${label}</span></span>`;
}
function _ovDef(v) { return v >= 35 ? "ov-good" : v >= 25 ? "ov-mid" : "ov-dim"; }
function updateOverviewBar(t) {
  loadAccolades().then(renderAccolades);
  // The vitals live in the OVERVIEW CARD — the gap-filling brick renderPowers
  // docks at the end of the shortest level column.
  const card = $("overview-card");
  if (!card) return;
  if (!t || !build.powers.length) { card.classList.add("hidden"); return; }
  const num = (x) => Math.round((x && typeof x === "object" ? x.value : x) || 0);
  const d = t.defense || {}, r = t.resistance || {}, off = t.offense || {};
  const rcap = Math.round(((t.caps || {}).resistance || 75));
  const _resCls = (v) => v >= rcap - 5 ? "ov-good" : v >= rcap * 0.6 ? "ov-mid" : "ov-dim";
  const rech = num(t.recharge);
  // A real table: damage types across the top, DEF and RES as rows. One glance.
  const dv = { sl: Math.min(num(d.Smashing), num(d.Lethal)), fc: Math.min(num(d.Fire), num(d.Cold)),
               en: Math.min(num(d.Energy), num(d.Negative)), mel: num(d.Melee),
               rng: num(d.Ranged), aoe: num(d.AoE) };
  const rv = { sl: Math.min(num(r.Smashing), num(r.Lethal)), fc: Math.min(num(r.Fire), num(r.Cold)),
               en: Math.min(num(r.Energy), num(r.Negative)) };
  const td = (v, cls) => `<td class="${cls}">${v}</td>`;
  card.innerHTML =
    `<div class="ovc-head">BUILD VITALS</div>
     ${provenanceLineHtml(t)}
     <table class="ov-table">
       <tr><th></th><th>S/L</th><th>F/C</th><th>E/N</th><th>Mel</th><th>Rng</th><th>AoE</th></tr>
       <tr><th>DEF %</th>${td(dv.sl, _ovDef(dv.sl))}${td(dv.fc, _ovDef(dv.fc))}${td(dv.en, _ovDef(dv.en))}
           ${td(dv.mel, _ovDef(dv.mel))}${td(dv.rng, _ovDef(dv.rng))}${td(dv.aoe, _ovDef(dv.aoe))}</tr>
       <tr><th>RES %</th>${td(rv.sl, _resCls(rv.sl))}${td(rv.fc, _resCls(rv.fc))}${td(rv.en, _resCls(rv.en))}
           <td class="ov-dim">—</td><td class="ov-dim">—</td><td class="ov-dim">—</td></tr>
     </table>
     <div class="ov-buildline">
       <span>Recharge <b class="${rech >= 70 ? "ov-good" : rech >= 40 ? "ov-mid" : "ov-dim"}">+${rech}%</b></span>
       <span>Recovery <b>+${num(t.recovery)}%</b></span>
       <span>HP <b>+${num(t.max_hp)}%</b></span>
       <span>DPS <b>${num(off.st_dps)}</b> ST / <b>${num(off.aoe_dps)}</b> AoE</span>
     </div>`;
  card.classList.remove("hidden");
}

// Active set bonuses, aggregated: "+7.5% Recharge ×5" style, biggest stacks first.
function updateBonusesCard(t) {
  const card = $("bonuses-card");
  if (!card) return;
  const list = (t && t.applied_bonuses) || [];
  if (!list.length || !build.powers.length) { card.classList.add("hidden"); return; }
  const counts = {};
  list.forEach(b => {
    const label = (Array.isArray(b.text) ? b.text[0] : b.text) || `${b.set} ${b.pieces}pc`;
    counts[label] = (counts[label] || 0) + 1;
  });
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const capped = (t.rule_of_five_capped || []).length;
  const top = entries.slice(0, capped ? 6 : 7);   // fits the double-height brick exactly
  card.innerHTML = `<div class="ovc-head">SET BONUSES <span class="muted">(${list.length} active)</span></div>`
    + top.map(([label, n]) =>
        `<div class="ovc-line ovc-clip">${n > 1 ? `<b>×${n}</b> ` : ""}${escHtml(label)}</div>`).join("")
    + (entries.length > top.length ? `<div class="ovc-line ovc-dim">… +${entries.length - top.length} more</div>` : "")
    + (capped ? `<div class="ovc-line ovc-dim">⚠ ${capped} bonus${capped > 1 ? "es" : ""} lost to the rule of five</div>` : "");
  card.classList.remove("hidden");
}

// The meta-invariant uniques layer (per the master corpus: same ~9 uniques in both
// eras) — a checklist of what this build carries.
const _UNIQUE_CHECKS = [
  ["LotG +Recharge", s => (s.set_name || "").includes("Luck of the Gambler") && (s.piece_name || "").includes("Recharge")],
  ["Steadfast +Def", s => (s.set_name || "").includes("Steadfast") && (s.piece_name || "").includes("Def")],
  ["Glad Armor +Def", s => (s.set_name || "").includes("Gladiator's Armor") && (s.piece_name || "").includes("Def")],
  ["Shield Wall +Res", s => (s.set_name || "").includes("Shield Wall") && (s.piece_name || "").includes("Res")],
  ["Panacea proc", s => (s.set_name || "").includes("Panacea") && (s.piece_name || "").includes("+")],
  ["Miracle +Rec", s => (s.set_name || "").includes("Miracle") && (s.piece_name || "").includes("Recovery")],
  ["Numina +Reg/Rec", s => (s.set_name || "").includes("Numina") && (s.piece_name || "").includes("+")],
  ["Perf Shifter +End", s => (s.set_name || "").includes("Performance Shifter") && (s.piece_name || "").toLowerCase().includes("chance")],
  ["Reactive scaling Res", s => (s.set_name || "").includes("Reactive Defenses") && (s.piece_name || "").includes("Scaling")],
];
function updateUniquesCard() {
  const card = $("uniques-card");
  if (!card) return;
  if (!build.powers.length) { card.classList.add("hidden"); return; }
  const slots = build.powers.flatMap(p => (p.slots || []).filter(Boolean));
  const rows = _UNIQUE_CHECKS.map(([name, test]) => {
    const n = slots.filter(test).length;
    return `<div class="ovc-line ${n ? "" : "ovc-dim"}">${n ? "✓" : "·"} ${escHtml(name)}${n > 1 ? ` <b>×${n}</b>` : ""}</div>`;
  });
  card.innerHTML = `<div class="ovc-head">UNIQUES CARRIED</div>` + rows.join("");
  card.classList.remove("hidden");
}

// One call fills every info brick. (The wall is snug by construction — uniform
// bricks in a row-flow grid — so no balancing pass is needed anymore.)
function updateInfoCards(t) {
  updateOverviewBar(t);
  updateBonusesCard(t);
  updateUniquesCard();
}
let LAST_TOTALS = null;
let LAST_CALC = null;   // full /build/calculate response (v36 inherent mechanics)

function buildPayload() {
  return {
    archetype: build.archetype,
    primary: build.primary, primary_display: build.primary_display,
    secondary: build.secondary, secondary_display: build.secondary_display,
    pools: build.pools, pools_display: build.pools_display,
    epic: build.epic, epic_display: build.epic_display,
    incarnates: Object.fromEntries(
      Object.entries(build.incarnates).map(([k, v]) => [k, v.display_name])),
    incarnates_full: Object.fromEntries(
      Object.entries(build.incarnates).map(([k, v]) => [k, v.full_name])),
    include_incarnates: build.include_incarnates,
    include_external: build.include_external,
    // v34 item 2: the accolade panel's checkmarks ARE the source of truth for
    // which accolades feed the displayed totals (UI state == engine state).
    accolades: [...ACCOLADES_CHECKED],
    // the character's alignment gates which accolades actually apply (game rule)
    alignment: charAlignment(),
    pvp: build.pvp,
    suppression: build.suppression,
    powers: build.powers.map(p => ({
      full_name: p.full_name,
      display_name: p.display_name,
      accepted_set_category_ids: p.accepted_set_category_ids,
      accepted_set_categories: p.accepted_set_categories,
      include_in_totals: p.include_in_totals,
      pick_level: p.pick_level,
      // Booster previews ride into calculate/validate ONLY — solve payloads
      // are built elsewhere from build.powers directly, so the solver never
      // optimizes on previewed levels (the standing boost boundary).
      slots: (p.slots || []).map((s, si) => {
        const pv = _previewBoostFor(p.full_name, si, s);
        return pv ? Object.assign({}, s, { boost: pv }) : s;
      }),
    })),
  };
}
const postJson = (obj) => ({
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify(obj),
});

function renderStats(t) {
  const resCap = (t.caps && t.caps.resistance_hard_cap) || 75;
  $("res-cap-label").textContent = `hard cap ${resCap}%`;
  $("res-cap-chip").textContent = `Resistance hard cap ${resCap}%`;
  $("defense-bars").innerHTML = Object.entries(t.defense)
    .map(([k, v]) => barRow(k, v, "def")).join("");
  $("resistance-bars").innerHTML = Object.entries(t.resistance)
    .map(([k, v]) => barRow(k, v, "res")).join("");

  const other = [
    ["Recharge (global)", t.recharge],
    ["Recovery", t.recovery],
    ["Regeneration", t.regeneration],
    ["Max HP", t.max_hp],
    ["ToHit", t.tohit],
    ["Accuracy", t.accuracy],
  ];
  // HP / regen / recovery carry a per-AT hard cap: show the capped value + a CAP
  // badge and the wasted overage, so the build doesn't silently overstate.
  // Field report (Maelwys): "+% Max HP" alone answers nothing — show the RESULTANT
  // hit points (capped), regen in HP/sec, and recovery in end/sec, like the game does.
  $("other-stats").innerHTML = other.map(([k, d]) => {
    const badge = d.at_cap ? ' <span class="aoe-tag">CAP</span>' : "";
    const over = (d.over_cap > 0) ? ` <span class="over">(+${d.over_cap} over)</span>` : "";
    let abs = "";
    if (k === "Max HP" && d.hp_final) {
      abs = ` <span class="muted small">= ${Math.round(d.hp_final)} HP`
        + (d.hp_at_cap && d.hp_uncapped > d.hp_final
            ? ` (capped; ${Math.round(d.hp_uncapped)} uncapped)` : "")
        + `</span>`;
    } else if (k === "Regeneration" && d.hp_per_sec) {
      abs = ` <span class="muted small">= ${d.hp_per_sec} HP/s</span>`;
    } else if (k === "Recovery" && t.endurance && t.endurance.recovery_per_sec) {
      abs = ` <span class="muted small">= ${t.endurance.recovery_per_sec} end/s</span>`;
    }
    return `<div class="o-row"><span>${k}${badge}</span><span>+${d.value}%${over}${abs}</span></div>`
      + attributionRowsHtml(k, t);
  }).join("");
  // v30 bonus extras (the back-filled families) — only nonzero rows, so builds
  // without these bonuses see nothing new. KB protection is points, not %.
  const bx = t.bonus_extras || {};
  const extraRows = [];
  if (bx.kb_protection && bx.kb_protection.value) {
    extraRows.push(`<div class="o-row"><span>KB protection</span><span>mag ${bx.kb_protection.value}</span></div>`);
  }
  if (bx.slow_resist && bx.slow_resist.value) {
    extraRows.push(`<div class="o-row"><span>Slow resistance</span><span>+${bx.slow_resist.value}%</span></div>`);
  }
  const mezNames = {Confused: "Confuse", Held: "Hold", Stunned: "Stun",
                    Immobilized: "Immobilize", Sleep: "Sleep", Terrorized: "Fear"};
  Object.entries(bx.mez_duration || {}).forEach(([m, v]) => {
    if (v) extraRows.push(`<div class="o-row"><span>${mezNames[m] || m} duration</span><span>+${v}%</span></div>`);
  });
  [["movement", "Movement speed"], ["range", "Range"], ["end_discount", "Endurance discount"],
   ["slow_strength", "Slow strength"], ["kb_strength", "Knockback strength"]].forEach(([k, lab]) => {
    if (bx[k] && bx[k].value) extraRows.push(`<div class="o-row"><span>${lab}</span><span>+${bx[k].value}%</span></div>`);
  });
  if (extraRows.length) {
    $("other-stats").innerHTML += extraRows.join("");
  }
  renderOffense(t.offense, t);
  // Endurance honesty rule (Σ-checkbox redesign): say so when the checked toggle
  // set + attack chain drains faster than recovery sustains.
  let note = t.note || "";
  if (t.strength_preview) {
    const sp = t.strength_preview;
    const fams = Object.entries(sp.families || {})
      .map(([f, v]) => `${f.toLowerCase()} +${Math.round(v * 100)}%`).join(", ");
    note = `⚡ Previewing ${sp.sources.join(" + ")}: buffable ${fams} strength `
      + `during its window — a burst view, not sustained totals. `
      + (note || "");
  }
  // LOUD burst-view flag (Joel's ruling: honest labeling instead of
  // restriction) — checked strike-window buffs mean these totals show an
  // alpha moment, not what the build sustains.
  const bursts = (build.powers || []).filter(p =>
    p.totals_kind && p.totals_kind.kind === "click_buff"
    && !p.totals_kind.amplifier && p.include_in_totals === true
    && _isBurst(p.totals_kind)).map(p => p.display_name);
  if (bursts.length) {
    note = `💥 BURST VIEW: ${bursts.join(" + ")} — a strike window `
      + `(${bursts.length > 1 ? "windows" : "window"} of seconds), not `
      + `sustained totals. Uncheck to see what the build holds all fight. `
      + (note || "");
  }
  const nBoostPv = Object.keys(PREVIEW_BOOSTS).length;
  if (nBoostPv) {
    note = `🔺 Previewing enhancement boosters on ${nBoostPv} piece${nBoostPv > 1 ? "s" : ""} `
      + `— these totals include the boosted values, but the boosts are not saved as owned. `
      + (note || "");
  }
  if (t.endurance && t.endurance.sustainable === false) {
    const warn = `⚠ Your checked toggles + attack chain drain ${t.endurance.drain_per_sec} `
      + `end/s against ${t.endurance.recovery_per_sec} end/s recovery (no incarnates assumed)`
      + (t.endurance.empty_after_sec
          ? ` — empty in ~${t.endurance.empty_after_sec}s of nonstop attacking; long fights `
            + `throttle your real output after that.`
          : ".");
    note = note ? `${note} ${warn}` : warn;
  }
  // v35: the travel toggle's drain is always shown, never silently dropped (the
  // hover-blaster gap) — with an honest note on whether the fight math counts it.
  if (t.endurance && t.endurance.travel_toggle_drain_per_sec) {
    const tr = `✈ Travel toggle: ${t.endurance.travel_toggle_drain_per_sec} end/s `
      + (t.endurance.travel_in_combat
          ? "(counted in combat — you fight from range)."
          : "(not counted in combat — grounded playstyle; pick \"from range\" and it counts).");
    note = note ? `${note} ${tr}` : tr;
  }
  $("stats-note").textContent = note;
}

// Damage/DPS + debuff/buff + pet summary. Hidden when there's no offense at all.
function renderOffense(off, t) {
  const sec = $("offense-section");
  const hasAny = off && (off.attack_count || (off.pets && off.pets.length)
    || (off.debuffs && off.debuffs.length) || (off.buffs && off.buffs.length));
  if (!hasAny) { sec.classList.add("hidden"); return; }
  sec.classList.remove("hidden");
  const sign = p => (p > 0 ? `+${p}` : `${p}`);
  let html = "";
  if (off.attack_count) {
    if (off.aoe_count) {
      html += `<div class="o-row o-head"><span>AoE throughput <span class="muted small">(farm DPS — ${off.aoe_count} AoE${off.aoe_count === 1 ? "" : "s"} cycled, per target)</span></span><span class="dps">${off.aoe_dps}</span></div>`;
      html += `<div class="o-row"><span>AoE alpha <span class="muted small">(one full AoE volley)</span></span><span>${off.aoe_burst}</span></div>`;
    }
    html += `<div class="o-row o-head"><span>Single-target DPS <span class="muted small">(best-attack chain — EB/AV)</span></span><span class="dps">${off.st_dps}</span></div>`;
    // v34 #4: the Musculature case — a global +damage% that reaches every attack
    // but had no line of its own. It gets named right under the DPS it feeds.
    html += dpsAttributionHtml(t);
    html += `<div class="o-row"><span>Top attack (damage / animation)</span><span>${off.top_dpa}</span></div>`;
    const top = (off.attacks || []).slice(0, 6).map(a =>
      `<div class="o-atk"><span>${a.name}${a.is_aoe ? ' <span class="aoe-tag">AoE</span>' : ''}</span>`
      + `<span class="muted small">${a.damage} dmg · ${a.cast_time}s · ${a.recharge}s rech · ${a.dpa} DPA</span></div>`).join("");
    if (top) html += `<div class="o-atks">${top}</div>`;
  }
  if (off.pets && off.pets.length) {
    html += `<div class="o-sub">Pet damage <span class="muted small">(per pet · squad size not multiplied)</span></div>`
      + off.pets.map(p => `<div class="o-atk"><span>${p.name}</span>`
        + `<span class="muted small">~${p.dps_each} DPS each · ${p.attack_count} atk · via ${p.from_power}</span></div>`).join("");
    // v34 #13: the pet-directed damage-buff ledger — attribution is display of the
    // engine's ledger, never new math (the three laws). Each source names its scope
    // and uptime; Pack Mentality carries its stated stack assumption. The
    // pets-always-hit simplification is an honest known boundary (Joel option B).
    const pbs = off.pet_damage_buff_sources;
    if (pbs && pbs.length) {
      html += `<div class="o-sub">Pet damage buffs <span class="muted small">(applied to the pet DPS above)</span></div>`
        + pbs.map(s => `<div class="o-row"><span>${s.name}`
          + `<span class="muted small"> · ${s.scope}${s.uptime != null && s.uptime < 1 ? ` · ${Math.round(s.uptime * 100)}% uptime` : ""}</span></span>`
          + `<span class="buf">+${s.pct}%</span></div>`
          + (s.note ? `<div class="o-note muted small">↳ ${s.note}</div>` : "")).join("")
        + `<div class="o-note muted small">Pets are modeled as always hitting — pet accuracy is not yet modeled (buff ToHit not credited).</div>`;
    }
  }
  if ((off.debuffs || []).length) {
    html += `<div class="o-sub">Enemy debuffs <span class="muted small">(base, per application)</span></div>`
      + off.debuffs.map(d => `<div class="o-row"><span>${d.effect}${d.type && d.type !== "all" ? " (" + d.type + ")" : d.type === "all" ? " (all)" : ""}</span><span class="deb">${sign(d.pct)}%</span></div>`).join("");
  }
  if ((off.buffs || []).length) {
    html += `<div class="o-sub">Ally buffs <span class="muted small">(base, per application)</span></div>`
      + off.buffs.map(d => `<div class="o-row"><span>${d.effect}${d.type && d.type !== "all" ? " (" + d.type + ")" : d.type === "all" ? " (all)" : ""}</span><span class="buf">${sign(d.pct)}%</span></div>`).join("");
  }
  // v36 (first-class display deliverable): the Inherent Mechanics block —
  // every meter family the AT (or slotted sets) carries, with its honest
  // status: scored (basis stated) / shown-not-scored / not yet modeled.
  const im = (LAST_CALC && LAST_CALC.inherent_mechanics) || [];
  if (im.length) {
    const tag = { scored: "scored", dormant: "shown, not scored", not_yet: "not yet modeled" };
    html += `<div class="o-row o-head" style="margin-top:8px"><span>Inherent mechanics</span></div>`
      + im.map(m => `<div class="o-row im-row im-${m.status}"><span><b>${escHtml(m.family)}</b>`
        + ` <span class="im-tag">${tag[m.status] || m.status}</span>`
        + ` <span class="muted small">${escHtml(m.basis)}</span></span></div>`).join("");
  }
  $("offense-stats").innerHTML = html;
}

function barRow(label, d, kind) {
  const cap = d.cap;
  const widthPct = Math.min(d.value / cap * 100, 100);
  const capped = d.at_cap;
  // Defense can exceed its soft cap; show the overage. Resistance can't.
  const over = (kind === "def" && d.over_cap > 0) ? ` <span class="over">(+${d.over_cap})</span>` : "";
  // AoE-88 honesty (Joel's Stalker eyeball): when this row includes
  // suppressible out-of-combat defense (Hide/Stealth class), the server sends
  // the in-combat value too — print the fight number right beside the
  // headline one so an "impossible" 77-88% never stands alone.
  const fight = (typeof d.in_combat === "number")
    ? ` <span class="over" title="Includes out-of-combat stealth defense that suppresses the moment you fight — in combat this is ${d.in_combat}%.">⚔ ${d.in_combat}%</span>` : "";
  return `<div class="bar-row">
    <span class="bar-label">${label}</span>
    <div class="bar-track">
      <div class="bar-fill ${kind} ${capped?'capped':''}" style="width:${widthPct}%"></div>
    </div>
    <span class="bar-val ${capped?'capped':''}">${d.value}%${over}${fight}</span>
  </div>`;
}

function renderValidation(v) {
  const host = $("validation");
  let html = "";
  if ((v.errors || []).length) {
    html += v.errors.map(e => `<div class="v-err">✖ ${e}</div>`).join("");
  }
  if ((v.warnings || []).length) {
    html += v.warnings.map(w => `<div class="v-warn">⚠ ${w}</div>`).join("");
  }
  if (!html) html = `<div class="v-ok">✓ No validation issues.</div>`;
  // Coaching — common-build-mistakes advice (soft, non-blocking): shown below hard errors/warnings.
  if ((v.coaching || []).length) {
    html += `<div class="v-coach-head">💡 Coaching — worth a look (not errors):</div>`
      + v.coaching.map(c => `<div class="v-coach">• ${escHtml(c)}</div>`).join("");
  }
  host.innerHTML = html;
}

// ---------------------------------------------------------------------------
// AI assistant
// ---------------------------------------------------------------------------
function renderSuggested() {
  const qs = [
    "How close am I to the defense soft cap?",
    "What enhancement sets fit my open slots?",
    "What's the best Fire/Cold resistance set for this build?",
    "Where can I add global recharge with Luck of the Gambler?",
    "Review my build for survivability gaps.",
  ];
  $("suggested").innerHTML = qs.map(q =>
    `<button onclick="suggest(this)">${q}</button>`).join("");
}
window.suggest = function (btn) { $("ai-question").value = btn.textContent; };

async function askAI() {
  const question = $("ai-question").value.trim();
  if (!question) return;
  const out = $("ai-response");
  out.classList.add("muted");
  out.textContent = "Asking Claude Code… (this calls the local CLI and may take a moment)";
  try {
    const res = await api("/ai/query", postJson({
      current_build: buildPayload(), question,
    }));
    out.classList.remove("muted");
    if (res.ok) {
      out.innerHTML = renderMarkdown(res.response || "(no response)");
    } else {
      // errors / not-logged-in messages: keep as plain text
      out.textContent = res.response || "(no response)";
    }
  } catch (e) {
    out.textContent = "Error contacting AI bridge: " + e;
  }
}

// ---------------------------------------------------------------------------
// Export current build to a Mids Reborn .mbd file
// ---------------------------------------------------------------------------
async function exportMids() {
  if (!build.archetype || !build.powers.length) {
    alert("Pick an archetype and add at least one power before exporting.");
    return;
  }
  const payload = buildPayload();
  payload.name = "CoH Planner Build";
  try {
    const res = await api("/build/export", postJson(payload));
    if (!res.ok) { alert("Export failed."); return; }
    const blob = new Blob([JSON.stringify(res.mbd, null, 1)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = res.filename || "build.mbd";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
  } catch (e) {
    alert("Export error: " + e);
  }
}

// ---------------------------------------------------------------------------
// Import a Mids .mbd: parse server-side -> load into the builder -> critique.
// Then the user sets a goal/role/tier and Solves to get an improved build; the
// before/after diff is shown, and they can export the improved .mbd.
// ---------------------------------------------------------------------------
let IMPORT_BEFORE = null;   // snapshot {totals, slots} for the before/after diff
let IMPORTED_POWERS = null; // deep copy of the imported powers+slots, for "reset & try again"
let CHANGES_AVAILABLE = false; // a solve has changed the imported build → offer the "what changed" window

async function importMids(e) {
  const file = e.target.files && e.target.files[0];
  e.target.value = "";   // allow re-importing the same file
  if (!file) return;
  // WALK REPORT (2026-07-20): the entry screen used to hide BEFORE the OS file
  // dialog opened, so a cancelled or failed-to-appear dialog stranded the user on
  // the bare planner with every import card gone — "the ability to browse is
  // GONE". The entry now hides only HERE, after a file was actually chosen;
  // cancel keeps you exactly where you were, controls intact.
  hideEntry();
  const report = $("import-report");
  report.classList.remove("hidden");
  report.innerHTML = `<p class="muted small">Reading <strong>${escHtml(file.name)}</strong>…</p>`;
  let text;
  try { text = await file.text(); } catch (err) { report.innerHTML = `<p class="v-err">Couldn't read the file: ${err}</p>`; return; }
  importBuildText(text);
}

// Shared tail of every import route (file picker, auto-found in-game save):
// parse server-side, load into the builder, snapshot for diff/reset, critique.
async function importBuildText(text) {
  const report = $("import-report");
  report.classList.remove("hidden");
  let res;
  try {
    res = await api("/build/import", postJson({ mbd: text, pvp: build.pvp }));
  } catch (err) { report.innerHTML = `<p class="v-err">Import failed: ${err}</p>`; return; }
  if (!res.ok) { report.innerHTML = `<p class="v-err">${res.response || "Import failed."}</p>`; return; }

  await applyImportedBuild(res.build);
  build._mode = "import";        // a real, created character → lock its archetype/powersets
  applyIdentityLock();
  // snapshot the imported build for a later before/after diff + reset/try-again
  IMPORT_BEFORE = { totals: res.totals, slots: snapshotSlots(res.build), name: res.name };
  IMPORTED_POWERS = JSON.parse(JSON.stringify(build.powers));
  renderImportReport(res);
  recompute();   // reveal the Reset button now that an imported build exists
}

// ── In-game build discovery: scan the Homecoming accounts folders ────────────
function _ageOf(epoch) {
  const s = Math.max(0, (Date.now() / 1000) - epoch);
  if (s < 3600) return `${Math.max(1, Math.round(s / 60))} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

async function ingameScan(root) {
  const box = $("ingame-found");
  box.classList.remove("hidden");
  box.innerHTML = `<p class="muted small">🔍 Looking for your Homecoming characters…</p>`;
  const url = root ? `/ingame/scan?root=${encodeURIComponent(root)}` : "/ingame/scan";
  const r = await api(url).catch(() => null);
  renderIngameFound(r);
}

function renderIngameFound(r) {
  const box = $("ingame-found");
  if (!r || !r.ok || !(r.files || []).length) {
    box.innerHTML =
      `<p class="muted small">Couldn't find a Homecoming <code>accounts</code> folder with build saves in the
       usual places. If you've run <code>/build_save_file</code> in game, paste your game folder here
       (e.g. <code>C:\\Games\\Homecoming</code>):</p>`
      + `<div class="ingame-root-row"><input id="ingame-root" placeholder="C:\\Games\\Homecoming">`
      + `<button class="linkbtn" id="ingame-root-go">Search there</button></div>`;
    $("ingame-root-go").addEventListener("click", () => {
      const root = $("ingame-root").value.trim();
      if (root) ingameScan(root);
    });
    $("ingame-root").addEventListener("keydown", (e) => {
      if (e.key === "Enter") { const root = e.target.value.trim(); if (root) ingameScan(root); }
    });
    return;
  }
  box.innerHTML =
    `<p class="muted small">Found ${r.files.length} character save${r.files.length > 1 ? "s" : ""} — click one to import:</p>`
    + r.files.slice(0, 12).map((f, i) =>
        `<button class="ingame-file" data-i="${i}">🎭 <b>${escHtml(f.character)}</b>`
        + ` <span class="muted small">${escHtml(f.account || "")} · saved ${_ageOf(f.modified)}</span></button>`).join("")
    + (r.files.length > 12 ? `<p class="muted small">…and ${r.files.length - 12} more (newest shown).</p>` : "");
  box.querySelectorAll(".ingame-file").forEach(btn => btn.addEventListener("click", async () => {
    const f = r.files[+btn.dataset.i];
    // same stranding class as the file-picker route: hide the entry only AFTER
    // the file actually read — a failed read leaves the cards (and this list) up
    const rr = await api("/ingame/read", postJson({ path: f.path })).catch(() => null);
    if (!rr || !rr.ok) { alert((rr && rr.response) || "Couldn't read that file — try the file picker."); return; }
    hideEntry();
    importBuildText(rr.text);
  }));
}

// Restore the imported build exactly as it came in, so the user can try a
// different goal/role/options without re-importing the file.
function resetToImported() {
  if (!IMPORTED_POWERS) return;
  // reset means reset (0.12.20 eyeball rule): the import didn't carry custom
  // targets, exposure, travel answers, or boost previews — restoring "exactly
  // as it came in" clears them too, same as every other start-over path.
  resetBuildScopedState();
  build.powers = JSON.parse(JSON.stringify(IMPORTED_POWERS));
  build.imported = true;
  setAllLocks($("preserve-toggle") ? $("preserve-toggle").checked : true);
  syncPreserveFromLocks();     // v35: locks re-seed with the restored build
  CHANGES_AVAILABLE = false;   // back to the imported build — nothing changed to show
  renderPowers();
  recompute();
  const out = $("ai-response");
  if (out) { out.classList.add("muted"); out.innerHTML = "Reset to your imported build. Adjust the goal/options and Solve again."; }
  const status = $("gen-status");
  if (status) status.textContent = "↺ Reset to imported build.";
}
window.resetToImported = resetToImported;

// Per-power set summary, for diffing what the solver changes.
function snapshotSlots(b) {
  const m = {};
  for (const p of b.powers || []) {
    const sets = {};
    for (const s of p.slots || []) {
      const n = s && (s.set_name || s.piece_name) || "—";
      sets[n] = (sets[n] || 0) + 1;
    }
    m[p.full_name] = { display: p.display_name, sets, count: (p.slots || []).length };
  }
  return m;
}

// A build's pools + epic are IMPLICIT in its powers (Pool.Fighting.Weave, Epic.*.Scorpion_Shield…).
// Derive them from the powers so the top-of-page dropdowns ALWAYS reflect the real build — needed by
// every path that generates powers (import, respec-at-50, autopick), not just import. Relying on a
// separate `pools`/`epic` field left the selectors blank (a solved/respec'd build doesn't populate
// them), so a build using 4 pools + an epic rendered with empty "— pool —" / "— epic —" selects.
// `fallbackPools`/`fallbackEpic` are used only when the powers carry no pool/epic (e.g. a bare kit).
async function syncPoolsEpicFromPowers(powers, fallbackPools, fallbackEpic) {
  const epicPs = (powers || []).map(p => p.powerset_full_name || "")
    .find(ps => ps.startsWith("Epic.")) || fallbackEpic || "";
  if (epicPs) {
    $("sel-epic").value = epicPs; build.epic = epicPs;
    build.epic_display = $("sel-epic").selectedOptions[0]?.text; await loadPowers(epicPs);
  } else {
    $("sel-epic").value = ""; build.epic = null; build.epic_display = null;
  }
  const poolSels = [...document.querySelectorAll(".pool-sel")];
  const usedPools = [];
  for (const p of (powers || [])) {
    const ps = p.powerset_full_name || "";
    if (ps.startsWith("Pool.") && !usedPools.includes(ps)) usedPools.push(ps);
  }
  build.pools = (usedPools.length ? usedPools : (fallbackPools || [])).slice(0, 4);
  build.pools_display = [];
  for (let i = 0; i < poolSels.length; i++) {
    poolSels[i].value = build.pools[i] || "";
    if (build.pools[i]) { build.pools_display.push(poolSels[i].selectedOptions[0]?.text); await loadPowers(build.pools[i]); }
  }
}

async function applyImportedBuild(b) {
  // FORWARD-COMPAT (2026-07-20, dead-air order #2.3): normalize an older/partial
  // save ONCE, up front, so EVERY downstream consumer (syncPoolsEpicFromPowers,
  // the powers map, renderPowers) sees clean data. A null or full_name-less power
  // entry would otherwise throw before the load finished and deaden the page.
  b = b || {};
  b.powers = (b.powers || []).filter((p) => p && p.full_name);
  resetTrayPanels();          // swapping in a new build → drop the prior tray/order panels
  setRespecHintFresh();       // a new build gets a fresh respec evaluation (undo any dismiss)
  resetBuildScopedState();    // a swapped-in build is a DIFFERENT character — no leaked
  //                             custom targets / exposure / travel / previews (state-
  //                             lifecycle rule; callers that carry answers re-set them after)
  // archetype cascade (loads powerset options)
  $("sel-archetype").value = b.archetype || "";
  await onArchetypeChange({ target: { value: b.archetype || "" } });
  // primary / secondary / epic
  if (b.primary) { $("sel-primary").value = b.primary; build.primary = b.primary;
    build.primary_display = $("sel-primary").selectedOptions[0]?.text; await loadPowers(b.primary); }
  if (b.secondary) { $("sel-secondary").value = b.secondary; build.secondary = b.secondary;
    build.secondary_display = $("sel-secondary").selectedOptions[0]?.text; await loadPowers(b.secondary); }
  // Sync the Pool + Epic dropdowns to whatever powers the build actually uses.
  await syncPoolsEpicFromPowers(b.powers || [], b.pools, b.epic);
  // powers + slots (b.powers already normalized at the top; every field defaults
  // so a missing key degrades to a sensible value rather than crashing)
  build.powers = (b.powers || []).map((p) => ({
    full_name: p.full_name, display_name: p.display_name,
    powerset_full_name: p.powerset_full_name,
    accepted_set_category_ids: p.accepted_set_category_ids || [],
    accepted_set_categories: p.accepted_set_categories || [],
    power_type: p.power_type,
    include_in_totals: p.power_type === 1 || p.power_type === 2,
    pick_level: p.pick_level, level_available: p.level_available,
    earned_slot_count: p.earned_slot_count,
    slots: p.slots || [], slotCount: (p.slots || []).length,
    _locked: !!p._locked,     // v35: lock choices ride saves (resume = same choices)
  }));
  // incarnates
  build.incarnates = {};
  for (const [slot, v] of Object.entries(b.incarnates || {})) build.incarnates[slot] = v;
  document.querySelectorAll("#incarnate-selectors select").forEach((s) => {
    const v = build.incarnates[s.dataset.slot]; if (v) s.value = v.full_name;
  });
  build.level_reached = b.level_reached || null;   // restore where the player was in-game
  build.imported = true;    // an imported build → RETOOL mode; locks protect its sets
  // v35 §4: seed the visible locks. A save that already KNOWS about locks keeps
  // its own choices (resume = the same decisions you left with); anything else
  // (fresh import, pre-lock save) seeds from the master switch (default ON) —
  // every hand-slotted power arrives locked, the user unlocks exceptions.
  const savedLocks = (b.powers || []).some(
    p => p && Object.prototype.hasOwnProperty.call(p, "_locked"));
  if (!savedLocks) {
    setAllLocks($("preserve-toggle") ? $("preserve-toggle").checked : true);
  }
  syncPreserveFromLocks();
  renderPowers();
  recompute();
}

function renderImportReport(res) {
  const report = $("import-report");
  report.classList.remove("hidden");
  const ICON = { good: "✓", warn: "⚠", info: "•" };
  const items = (res.critique || []).map(c =>
    `<li class="crit-${c.kind}">${ICON[c.kind] || "•"} ${c.text}</li>`).join("");
  report.innerHTML = `
    <div class="import-head"><strong>Imported: ${res.name}</strong>
      <span class="muted small">critique below — set a goal/role/tier, then Solve to improve it</span></div>
    <ul class="crit-list">${items}</ul>
    ${res.note ? `<p class="muted small">${res.note}</p>` : ""}
    <p class="muted small">Keep your powers and just re-slot (🧮 Solve on the right) — or do a
      clean-sheet rebuild that also re-picks powers (damage-aware), shown before you commit:</p>
    <button id="respec-preview-btn" class="respec-preview-btn" onclick="previewRespec()">🔧 Preview a full respec</button>
    <div id="respec-preview" class="respec-preview hidden"></div>`;
}

// Full-respec PREVIEW: re-pick powers (damage-aware autopicker, seeded from the imported AT +
// sets) -> solve + proc-bomb -> compute totals, and SHOW a before/after diff WITHOUT applying,
// so the user commits only after seeing what a respec would do. (The user's requested flow:
// import what you have -> offer a full respec -> show what it can do -> then commit.)
let PROPOSED_RESPEC = null;

async function previewRespec() {
  const at = build.archetype, pri = build.primary, sec = build.secondary;
  if (!at || !pri || !sec) { alert("Import or start a build first."); return; }
  const content = ($("preset-content") && $("preset-content").value) || "general";
  const role = ($("preset-role") && $("preset-role").value) || "damage";
  const btn = $("respec-preview-btn");
  if (btn) { btn.disabled = true; btn.textContent = "Building a full respec…"; }
  try {
    const ap = await api("/build/autopick", postJson({ archetype: at, primary: pri, secondary: sec,
      role, content, exposure: build._exposure || "flex", travel: "speed",
      custom_targets: build._custom_targets || null }));
    if (!ap || !ap.ok) throw new Error((ap && ap.error) || "auto-pick failed");
    const pw = ap.powers.filter(p => !p.full_name.startsWith("Incarnate"))
                        .map(p => ({ full_name: p.full_name, slots: [] }));
    const sol = await api("/build/solve", postJson({ archetype: at, powers: pw, content, role, preserve: false }));
    if (!sol || !sol.ok) throw new Error((sol && sol.response) || "solve failed");
    const calc = await api("/build/calculate", postJson({ archetype: at, powers: sol.powers, pvp: build.pvp }));
    PROPOSED_RESPEC = { powers: sol.powers, totals: (calc && calc.totals) || calc || {},
                        warnings: sol.warnings || [] };
    renderRespecPreview();
  } catch (e) {
    const host = $("respec-preview");
    if (host) { host.classList.remove("hidden"); host.innerHTML = `<p class="v-err">Couldn't build a respec: ${(e && e.message) || e}</p>`; }
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "🔧 Preview a full respec"; }
  }
}
window.previewRespec = previewRespec;

function _statVal(t, kind, key) {
  if (!t || !t[kind]) return 0;
  return key ? ((t[kind][key] && t[kind][key].value) || 0) : (t[kind].value || 0);
}

function renderRespecPreview() {
  const host = $("respec-preview");
  if (!host || !PROPOSED_RESPEC) return;
  const before = (IMPORT_BEFORE && IMPORT_BEFORE.totals) || {};
  const after = PROPOSED_RESPEC.totals || {};
  const dispOf = (fn) => fn.split(".").slice(-1)[0].replace(/_/g, " ");
  const skip = (f) => f.startsWith("Incarnate") || f.startsWith("Inherent") || /\.(Boxing|Brawl|Sprint|Rest|Hurdle|Swift|Health|Stamina)$/.test(f);
  const impFns = new Set((IMPORTED_POWERS || []).map(p => p.full_name).filter(f => !skip(f)));
  const propFns = new Set(PROPOSED_RESPEC.powers.map(p => p.full_name).filter(f => !skip(f)));
  const added = [...propFns].filter(f => !impFns.has(f)).map(dispOf);
  const removed = [...impFns].filter(f => !propFns.has(f)).map(dispOf);
  const rows = [["S/L resist", "resistance", "Smashing"], ["Fire resist", "resistance", "Fire"],
    ["Melee def", "defense", "Melee"], ["Ranged def", "defense", "Ranged"],
    ["AoE def", "defense", "AoE"], ["Recharge", "recharge", null]];
  const statHtml = rows.map(([lbl, kind, key]) => {
    const b = _statVal(before, kind, key), a = _statVal(after, kind, key), d = a - b;
    const cls = d > 0.5 ? "delta-up" : d < -0.5 ? "delta-down" : "delta-flat";
    return `<tr><td>${lbl}</td><td class="muted">${b.toFixed(1)}%</td><td>${a.toFixed(1)}%</td>`
      + `<td class="${cls}">${d >= 0 ? "+" : ""}${d.toFixed(1)}</td></tr>`;
  }).join("");
  const warns = (PROPOSED_RESPEC.warnings || []).filter(w => w.kind === "warn")
    .map(w => `<li class="crit-warn">⚠ ${w.text}</li>`).join("");
  host.classList.remove("hidden");
  host.innerHTML = `
    <div class="rp-head"><strong>🔧 Full respec — preview only (nothing applied yet)</strong></div>
    <div class="rp-grid">
      <div><div class="rp-sub">Power changes</div>
        ${added.length ? `<div class="rp-add"><strong>+ Added:</strong> ${added.join(", ")}</div>` : ""}
        ${removed.length ? `<div class="rp-rem"><strong>− Dropped:</strong> ${removed.join(", ")}</div>` : ""}
        ${(!added.length && !removed.length) ? `<div class="muted small">Same power picks — only slotting changes (auras proc-bombed, etc.).</div>` : ""}
      </div>
      <div><div class="rp-sub">Key stats — before → after</div>
        <table class="rp-stats"><tr><th></th><th>now</th><th>respec</th><th>Δ</th></tr>${statHtml}</table></div>
    </div>
    ${warns ? `<div class="rp-sub">Flags on the respec</div><ul class="crit-list">${warns}</ul>`
            : `<div class="rp-clean">✓ No build-quality flags on the respec.</div>`}
    <div class="rp-actions">
      <button class="rp-apply" onclick="applyProposedRespec()">✓ Apply this respec</button>
      <button class="rp-keep" onclick="document.getElementById('respec-preview').classList.add('hidden')">Keep my current build</button>
    </div>`;
  host.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function applyProposedRespec() {
  if (!PROPOSED_RESPEC) return;
  build.powers = PROPOSED_RESPEC.powers;
  build.imported = false;            // it's a fresh respec now, not the imported build
  await syncPoolsEpicFromPowers(PROPOSED_RESPEC.powers);   // reflect its pool/epic in the dropdowns
  CHANGES_AVAILABLE = false;
  renderPowers();
  recompute();
  const host = $("respec-preview");
  if (host) host.classList.add("hidden");
  const status = $("gen-status");
  if (status) status.textContent = "✓ Applied the full respec — export it, or tweak the goal and re-solve.";
}
window.applyProposedRespec = applyProposedRespec;

// ---------------------------------------------------------------------------
// Power colors / glow -> Homecoming .powerCust
// ---------------------------------------------------------------------------
function hexToRgb(h) {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(h || "");
  return m ? [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)] : [255, 255, 255];
}
function rgbCss(rgb) { return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`; }

// Distinct powersets in the build, with display names.
function buildPowersets() {
  const seen = new Map();
  for (const p of build.powers) {
    if (!seen.has(p.powerset_full_name)) {
      const label = p.powerset_full_name.split(".").slice(-1)[0].replace(/_/g, " ");
      seen.set(p.powerset_full_name, label);
    }
  }
  return [...seen.entries()];   // [[full, label], ...]
}

function renderPowerColorRows() {
  const host = $("pc-powersets");
  if (!host) return;
  const sets = buildPowersets();
  if (!sets.length) { host.innerHTML = `<p class="muted small">Add powers first.</p>`; return; }
  const def1 = document.querySelector(".pc-default .pc-c1").value;
  const def2 = document.querySelector(".pc-default .pc-c2").value;
  host.innerHTML = sets.map(([full, label]) => `
    <div class="pc-scheme" data-ps="${full}">
      <label class="pc-ov"><input type="checkbox" class="pc-override"> ${label}</label>
      <label>Primary <input type="color" class="pc-c1" value="${def1}" disabled></label>
      <label>Glow <input type="color" class="pc-c2" value="${def2}" disabled></label>
      <select class="pc-bright" disabled>
        <option value="dark">Dark</option><option value="default" selected>Default</option><option value="bright">Bright</option>
      </select>
    </div>`).join("");
  host.querySelectorAll(".pc-scheme").forEach(row => {
    const cb = row.querySelector(".pc-override");
    cb.addEventListener("change", () => {
      row.querySelectorAll("input[type=color],select").forEach(el => { el.disabled = !cb.checked; });
    });
  });
}

function collectColorSchemes() {
  const d = document.querySelector(".pc-default");
  const def = { c1: hexToRgb(d.querySelector(".pc-c1").value),
                c2: hexToRgb(d.querySelector(".pc-c2").value),
                brightness: d.querySelector(".pc-bright").value };
  const by = {};
  document.querySelectorAll("#pc-powersets .pc-scheme").forEach(row => {
    if (row.querySelector(".pc-override").checked) {
      by[row.dataset.ps] = { c1: hexToRgb(row.querySelector(".pc-c1").value),
                             c2: hexToRgb(row.querySelector(".pc-c2").value),
                             brightness: row.querySelector(".pc-bright").value };
    }
  });
  const powers = build.powers.map(p => ({ full_name: p.full_name, powerset_full_name: p.powerset_full_name }));
  return { powers, default: def, by_powerset: by };
}

async function previewPowerColors() {
  if (!build.powers.length) { $("pc-preview").innerHTML = `<p class="muted small">Add powers first.</p>`; return; }
  try {
    const res = await api("/build/powercust", postJson(collectColorSchemes()));
    if (!res.ok) { $("pc-preview").innerHTML = `<p class="v-err">${res.response}</p>`; return null; }
    const byName = {}; build.powers.forEach(p => { byName[p.full_name] = p.display_name; });
    $("pc-preview").innerHTML = res.preview.map(p =>
      `<div class="pc-swatch"><span class="pc-dot" style="background:${rgbCss(p.c1)}"></span>`
      + `<span class="pc-dot glow" style="background:${rgbCss(p.c2)}"></span>`
      + `<span class="pc-pwr">${byName[p.full_name] || p.full_name}</span></div>`).join("");
    return res;
  } catch (e) { $("pc-preview").innerHTML = `<p class="v-err">Preview error: ${e}</p>`; return null; }
}

async function downloadPowerCust() {
  const res = await previewPowerColors();
  if (!res || !res.ok) return;
  const blob = new Blob([res.text], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = res.filename || "coh_colors.powerCust";
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(a.href);
  $("pc-howto").innerHTML =
    `✓ Saved <strong>${res.filename}</strong> (${res.count} powers). To use it: drop it in `
    + `<code>C:\\Games\\Homecoming\\powercust\\</code>, then in-game open <strong>Powers → `
    + `Customize</strong> and click <strong>Load</strong> (or preview your character in `
    + `<strong>Titan Icon</strong>). If colors don't apply, tell me — we may need the power's numeric id.`;
}

// ---------------------------------------------------------------------------
// "Build this for me" — generate a full build with Claude and apply it
// ---------------------------------------------------------------------------
// Tier metadata mirrors ai_build.TIER_META (used for the pending placeholders).
const TIERS = [
  { key: "budget",   label: "Budget",   cost: "Cheapest & efficient",
    blurb: "SOs / common IOs and cheap sets. Meets the goal at minimal influence cost." },
  { key: "balanced", label: "Balanced", cost: "Middle of the road",
    blurb: "Strong common IO sets + LotG global recharge. No purples / ATOs / Winter / PvP IOs." },
  { key: "premium",  label: "Premium",  cost: "Top-end, where it counts",
    blurb: "Purples, Superior ATOs, Winter & PvP IOs — used only where they noticeably beat the cheaper option. Maximizes impact per slot, not spend." },
];
let LAST_TIERS = {};   // tier key -> resolved build result
let PENDING_FOCUS = null;   // confirmed-priority text from interpret-goal
let INTERP_MATCHED = [];    // [{label, focus}] currently shown as confirm chips

// Player-facing "what should we base this build on?" roles. These bias the
// solver toward set categories + stat kinds that pay off for that play style.
// Multi-select: blend as many as fit. Keys must match solver.ROLE_DEFS.
const ROLE_OPTIONS = [
  { key: "survival",  label: "🛡 Survive",  desc: "Lean toward defense, resistance, HP & regen sets — stay alive longer." },
  { key: "damage",    label: "⚔ Damage",   desc: "Lean toward damage sets and faster attack recharge — kill faster." },
  { key: "healing",   label: "💚 Healing",  desc: "Lean toward healing sets and regen/recovery — keep the team topped up." },
  { key: "buffing",   label: "📈 Buffing",  desc: "Lean toward to-hit/defense buff & endurance sets — empower allies." },
  { key: "debuffing", label: "📉 Debuffing", desc: "Lean toward to-hit/defense debuff & slow sets — weaken enemies." },
  { key: "recharge",  label: "⏱ Recharge", desc: "Lean toward recharge bonuses — powers ready more often." },
];

function selectedRoles() {
  return [...document.querySelectorAll(".role-cb")]
    .filter(cb => cb.checked).map(cb => cb.value);
}

function renderRoleChips() {
  const host = $("role-chips");
  if (!host) return;
  host.innerHTML = ROLE_OPTIONS.map(r =>
    `<label class="role-chip" title="${r.desc}">`
    + `<input type="checkbox" class="role-cb" value="${r.key}"> ${r.label}</label>`).join("");
}

// Which tiers the user ticked (in canonical order).
function selectedTiers() {
  const on = new Set([...document.querySelectorAll(".tier-cb")]
    .filter(cb => cb.checked).map(cb => cb.value));
  return TIERS.filter(t => on.has(t.key));
}

function updateGenBtnLabel() {
  const n = selectedTiers().length;
  const btn = $("gen-btn");
  if (!btn) return;
  // RETOOL honesty: generating is a FROM-SCRATCH act — it names its consequence
  // (Joel's §2 rule: buttons say what happens, not the mechanism).
  const suffix = (typeof isRetool === "function" && isRetool())
    ? " (fresh from scratch — replaces this build)" : "";
  btn.textContent = n === 0 ? "Select at least one build tier"
    : n === 1 ? `Generate the ${selectedTiers()[0].label} build${suffix}`
    : `Generate ${n} builds${suffix}`;
  btn.disabled = n === 0;
}

// Step 1: interpret the goal against the lexicon and ask the user to confirm
// BEFORE spending time — so none is wasted on a misread goal.
async function confirmGoalThenGenerate() {
  const status = $("gen-status");
  if (!build.archetype || !build.primary || !build.secondary) {
    status.textContent = "Select an archetype, primary, and secondary first.";
    return;
  }
  if (!selectedTiers().length) {
    status.textContent = "Tick at least one build tier (Budget / Balanced / Premium).";
    return;
  }
  const goal = $("gen-goal").value.trim();
  if (!goal) { status.textContent = "Enter a goal first."; return; }

  status.textContent = "Interpreting your goal…";
  let interp;
  try {
    interp = await api("/ai/interpret-goal", postJson({ goal,
      primary: build.primary_display || build.primary,
      secondary: build.secondary_display || build.secondary }));
  } catch (e) {
    status.textContent = "Couldn't interpret the goal: " + e; return;
  }
  INTERP_MATCHED = interp.matched || [];
  renderConfirm();
  $("gen-confirm").classList.remove("hidden");
  status.textContent = "Confirm the interpretation to generate.";
}

function joinList(a) {
  return a.length <= 1 ? (a[0] || "")
    : a.length === 2 ? `${a[0]} and ${a[1]}`
    : `${a.slice(0, -1).join(", ")}, and ${a[a.length - 1]}`;
}

// Build the priority text sent to generation from the (possibly edited) chips.
function buildFocus(matched) {
  if (!matched.length) {
    return "No specific priorities; build a well-rounded, generally strong "
      + "character for this archetype and powersets.";
  }
  return "CONFIRMED PRIORITIES (the user verified these — honor them, in roughly "
    + "this order):\n" + matched.map(m => `- ${m.label}: ${m.focus}`).join("\n");
}

function renderConfirm() {
  const labels = INTERP_MATCHED.map(m => m.label);
  $("gen-confirm-text").textContent = labels.length
    ? `Based on your request, you want: ${joinList(labels)}. Remove any that don't fit, then generate.`
    : "No priorities left — I'll build a well-rounded character. Edit your goal to steer it, or generate as-is.";
  $("gen-confirm-chips").innerHTML = INTERP_MATCHED.map((m, i) =>
    `<span class="chip removable">${m.label}<button class="chip-x" title="Remove this priority" onclick="removeChip(${i})">×</button></span>`).join("");
  PENDING_FOCUS = buildFocus(INTERP_MATCHED);
}

window.removeChip = function (i) {
  INTERP_MATCHED.splice(i, 1);
  renderConfirm();
};

// Step 2: user confirmed — ONE LLM call picks the powers, the deterministic
// solver slots all tiers. Fast (~10-30s total) and no slotting guesswork.
async function generateBuild() {
  const status = $("gen-status");
  $("gen-confirm").classList.add("hidden");
  if (!build.archetype || !build.primary || !build.secondary) {
    status.textContent = "Select an archetype, primary, and secondary first.";
    return;
  }
  const goal = $("gen-goal").value.trim();
  if (!goal) { status.textContent = "Enter a goal first."; return; }

  const tiers = selectedTiers();
  const btn = $("gen-btn");
  btn.disabled = true;
  LAST_TIERS = {};
  initTierCompare(goal, tiers);
  tiers.forEach(t => setTierCard(t.key, { pending: true }));
  status.textContent = "Claude is picking the powers; the solver slots them "
    + "optimally per tier — ~10–30s.";
  try {
    const res = await api("/ai/generate-solved", postJson({
      archetype: build.archetype, primary: build.primary,
      secondary: build.secondary, goal, roles: selectedRoles(), pvp: build.pvp,
    }));
    if (!res.ok) {
      status.textContent = res.response || "Generation failed.";
      tiers.forEach(t => setTierCard(t.key, { ok: false, response: res.response }));
      btn.disabled = false; return;
    }
    const byTier = {};
    (res.tiers || []).forEach(tr => { byTier[tr.tier] = tr; });
    tiers.forEach(t => {
      const tr = byTier[t.key];
      if (tr) { LAST_TIERS[t.key] = tr; setTierCard(t.key, tr); }
      else setTierCard(t.key, { ok: false, response: "tier not returned" });
    });
  } catch (e) {
    status.textContent = "Error generating build: " + e;
    btn.disabled = false; return;
  }
  const okCount = Object.values(LAST_TIERS).filter(t => t.ok).length;
  btn.disabled = false;
  if (tiers.length === 1 && okCount === 1) {
    status.textContent = `✓ ${tiers[0].label} build ready.`;
    loadTier(tiers[0].key);
  } else {
    status.textContent = `✓ ${okCount} of ${tiers.length} build(s) ready — compare and load one.`;
  }
}

// ----- tier comparison overlay -----
function tierStatLine(t) {
  if (!t) return "";
  const defCapped = Object.values(t.defense).filter(d => d.at_cap).length;
  const topDef = Object.entries(t.defense).sort((a, b) => b[1].value - a[1].value)[0];
  const topRes = Object.entries(t.resistance).sort((a, b) => b[1].value - a[1].value)[0];
  const row = (label, val) => `<div class="ts-row"><span>${label}</span><span>${val}</span></div>`;
  const aoe = t.offense && t.offense.aoe_count ? row("AoE DPS", `${t.offense.aoe_dps}`) : "";
  const dps = t.offense && t.offense.st_dps ? row("ST DPS", `${t.offense.st_dps}`) : "";
  return row("Def soft-capped", `${defCapped} type${defCapped === 1 ? "" : "s"}`)
    + row("Top defense", `${topDef[0]} ${topDef[1].value}%`)
    + row("Top resistance", `${topRes[0]} ${topRes[1].value}%`)
    + row("Recharge", `+${t.recharge.value}%`)
    + row("Recovery", `+${t.recovery.value}%`)
    + aoe + dps
    + row("Set bonuses", `${t.applied_bonus_count || 0}`);
}

function initTierCompare(goal, tiers) {
  tiers = tiers && tiers.length ? tiers : TIERS;
  $("tier-title").textContent = tiers.length === 1
    ? "Generating your build" : "Compare builds — pick one to load";
  $("tier-sub").textContent = `Goal: ${goal}`;
  const host = $("tier-cards");
  host.style.gridTemplateColumns = `repeat(${tiers.length}, 1fr)`;
  host.innerHTML = tiers.map(t =>
    `<div class="tier-card tier-${t.key}" id="tc-${t.key}"></div>`).join("");
  tiers.forEach(t => setTierCard(t.key, { idle: true }));
  $("tier-modal").classList.remove("hidden");
}

function setTierCard(key, res) {
  const meta = TIERS.find(t => t.key === key);
  const el = $(`tc-${key}`);
  if (!el) return;
  const head = `<div class="tc-head"><span class="tc-name">${meta.label}</span>
      <span class="tc-cost">${meta.cost}</span></div>
    <p class="tc-blurb muted small">${meta.blurb}</p>`;
  if (res.idle) {
    el.innerHTML = head + `<p class="muted small">Waiting…</p>`;
  } else if (res.pending) {
    el.innerHTML = head + `<p class="muted small tc-spin">⏳ Designing this build…</p>`;
  } else if (!res.ok) {
    el.classList.add("err");
    el.innerHTML = head + `<p class="muted small">Failed: ${res.response || "unknown error"}</p>`;
  } else {
    el.classList.remove("err");
    const nPowers = (res.powers || []).length;
    const nAdj = (res.warnings || []).length;
    el.innerHTML = head
      + `<div class="tc-stats">${tierStatLine(res.totals)}</div>
         <p class="tc-summary small">${res.summary || ""}</p>
         <div class="tc-meta muted small">${nPowers} powers${nAdj ? ` · ${nAdj} item(s) auto-adjusted` : ""}</div>
         <button class="tc-load" onclick="loadTier('${key}')">Load this build →</button>`;
  }
}

window.loadTier = async function (key) {
  const t = LAST_TIERS[key];
  if (!t || !t.ok) return;
  $("tier-modal").classList.add("hidden");
  build.tier = t.tier;
  await applyGeneratedBuild(t);
  const m = t.tier_meta || {};
  const adj = (t.warnings || []).length;
  $("gen-status").textContent =
    `✓ Loaded the ${m.label || t.tier} build${adj ? ` (${adj} item(s) adjusted)` : ""}.`;
  const out = $("ai-response");
  out.classList.remove("muted");
  let md = `**${m.label || t.tier} build — ${m.cost || ""}.** `;
  md += t.summary ? `${t.summary}\n\n` : "\n\n";
  if (adj) md += "**Adjustments made (invalid/unfound items dropped):**\n" +
    t.warnings.map((w) => `- ${w}`).join("\n");
  out.innerHTML = renderMarkdown(md);
};

// Put a button into a clearly-working state (so a slow action never looks dead),
// returning a restore() that puts its label/state back.
function setWorking(btn, label) {
  const orig = btn.textContent;
  btn.disabled = true;
  btn.classList.add("btn-working");
  btn.textContent = label;
  return () => { btn.disabled = false; btn.classList.remove("btn-working"); btn.textContent = orig; };
}

// Honest long-solve feedback (Joel's 2026-07-15 order — the 30-second-build
// field report): NO fake progress bars (a bar that lies about % is a UI-state
// lie). Indeterminate pulse + LIVE elapsed seconds + plain-language copy that
// levels with the user once a solve runs long. Measured reality: most combos
// solve in ~1s, but some power combinations are genuinely hard for the exact
// solver (Fire/Icy Dominator: 13s server-side, reproducibly) — the wait is
// real work, and the copy says so instead of leaving a silent void.
// Universal: every long-running solve click routes its status element here.
function startSolvePulse(el, baseText) {
  if (!el) return () => {};
  const t0 = Date.now();
  const paint = () => {
    const s = Math.round((Date.now() - t0) / 1000);
    el.textContent = `⏳ ${baseText}… ${s}s`
      + (s >= 6 ? " — some power combinations take up to a minute of real math; still working, not stuck." : "");
  };
  paint();
  const timer = setInterval(paint, 1000);
  return () => clearInterval(timer);
}

async function optimizeBuild() {
  const status = $("gen-status");
  if (!build.archetype || !build.primary || !build.secondary || !build.powers.length) {
    status.textContent = "Generate or build something first, then optimize.";
    return;
  }
  const goal = $("gen-goal").value.trim();
  if (!goal) { status.textContent = "Enter a goal to optimize toward."; return; }
  // Optimize is a from-scratch AI REDESIGN — it does NOT preserve your sets. For
  // an imported build, warn before discarding the player's invested slotting.
  if (build.imported && !confirm(
      "⚡ Optimize redesigns the WHOLE build with AI and will replace your current "
      + "IO sets — it does NOT preserve them, and may relocate or drop expensive "
      + "sets you already slotted.\n\nTo keep your sets and only fill the gaps, "
      + "click “🧮 Solve” with “Preserve my IO sets” "
      + "checked instead.\n\nContinue with a full AI redesign anyway?")) {
    status.textContent = "Optimize cancelled — use 🧮 Solve to keep your sets.";
    return;
  }
  const optBtn = $("opt-btn");
  const restore = setWorking(optBtn, "⏳ Optimizing with AI… (~1–2 min, please wait)");
  status.textContent = "Optimizing toward your goal… Claude reviews the current "
    + "totals and refines. This runs in the background — it can take a minute or two.";
  try {
    const res = await api("/ai/refine-build", postJson({
      archetype: build.archetype, primary: build.primary,
      secondary: build.secondary, goal, tier: build.tier || "balanced",
      build: buildPayload(),
    }));
    if (!res.ok) { status.textContent = res.response || "Optimize failed."; return; }
    await applyGeneratedBuild(res);
    const adj = (res.warnings || []).length;
    status.textContent = `✓ Build optimized and applied${adj ? ` (${adj} adjusted)` : ""}.`;
    const out = $("ai-response");
    out.classList.remove("muted");
    let md = res.summary ? `**Optimization:** ${res.summary}\n\n` : "";
    if (res.totals_before) {
      md += `**Totals before this pass:**\n\n` + res.totals_before
        + "\n\n_(New totals are in the Stats panel — compare.)_\n\n";
    }
    out.innerHTML = renderMarkdown(md || "Optimized build applied.");
  } catch (e) {
    status.textContent = "Error optimizing: " + e;
  } finally {
    restore();
  }
}

// Constraint solver: re-slot the CURRENT powers optimally toward the goal's
// targets (deterministic, no AI). Keeps your power picks, replaces the slotting.
const PERK_FOCUSES = [
  ["hp", "More HP"], ["recovery", "Better endurance recovery"],
  ["regen", "Faster HP regen"], ["recharge", "More recharge"],
  ["defense", "More defense"], ["resistance", "More resistance"],
];

async function previewPreset() {
  const el = $("preset-targets");
  if (!el) return;
  const content = $("preset-content").value, role = $("preset-role").value;
  if (!content && !role) { el.textContent = ""; return; }
  if (!build.archetype) { el.textContent = "Pick an archetype first."; return; }
  el.textContent = "…";
  try {
    const res = await api("/build/preset", postJson({
      archetype: build.archetype, content, role }));
    if (res && res.ok) {
      const tag = (res.labels || []).join(" · ");
      el.innerHTML = `<strong>🎯 ${tag}</strong> → ${res.summary || "—"}`
        + (res.perk_focus ? ` · spare slots → ${res.perk_focus}` : "");
    } else { el.textContent = ""; }
  } catch { el.textContent = ""; }
}

let LAST_ASSESS_ROUTES = [];

async function renderAssessment(presolvePowers, ctx) {
  const out = $("ai-response");
  const card = document.createElement("div");
  card.className = "assess-card";
  card.innerHTML = `<div class="muted small">⏳ Checking alternative routes…</div>`;
  out.appendChild(card);
  try {
    const res = await api("/build/assess", postJson({
      archetype: build.archetype, content: ctx.content || null, role: ctx.role || null,
      goal: ctx.goal || "", tier: build.tier || "premium", roles: selectedRoles(),
      pvp: build.pvp, preserve: ctx.preserve, keep_layout: ctx.keep_layout,
      powers: presolvePowers }));
    if (!res || !res.ok) { card.remove(); return; }
    LAST_ASSESS_ROUTES = res.alternatives || [];
    card.innerHTML = assessHtml(res);
  } catch { card.remove(); }
}

function assessHtml(res) {
  const fmtD = d => `${d.d >= 0 ? "+" : ""}${d.d}%`;
  let h = `<div class="assess-head">🤔 <strong>Does this match your priorities?</strong></div>`;
  h += `<div class="assess-line muted small">Optimized for: ${res.optimized || "—"}.</div>`;
  const short = (res.achieved || []).filter(a => !a.met);
  if (short.length) {
    h += `<div class="assess-line small">⚠ Falling short: `
      + short.map(a => `<b>${a.stat}</b> ${a.have}/${a.want}%`).join(", ")
      + ` <span class="muted">(powerset/slot ceiling)</span>.</div>`;
  }
  if ((res.alternatives || []).length) {
    h += `<div class="assess-line small">Prioritize differently? Each route is <b>pre-solved</b> — these are the real trade-offs:</div>`;
    h += `<div class="assess-routes">`;
    res.alternatives.forEach((alt, i) => {
      if (alt.maxed) {
        h += `<div class="assess-route maxed" title="No further gain available on these powers">`
          + `<span class="rt-label">${alt.label}</span> <span class="rt-maxed">already maxed</span></div>`;
      } else {
        const deltas = alt.deltas.map(d =>
          `<span class="rt-delta ${d.d >= 0 ? "up" : "down"}">${d.stat} ${fmtD(d)}</span>`).join(" ");
        h += `<button class="assess-route" onclick="applyRoute(${i})" title="Re-solve toward: ${alt.label}">`
          + `<span class="rt-label">${alt.label} →</span> ${deltas}</button>`;
      }
    });
    h += `</div>`;
  }
  h += `<div class="assess-line muted small">…or keep it as-is — nothing changes until you pick a route.</div>`;
  return h;
}

window.applyRoute = function (i) {
  const alt = LAST_ASSESS_ROUTES[i];
  if (!alt || !alt.targets) return;
  solveSlotting(null, { targets: alt.targets, routeLabel: alt.label });
};

let INCARNATE_RECS = [];
let INCARNATE_LOADOUTS = [];

function renderIncarnateRecs(recs, loadouts) {
  INCARNATE_RECS = recs || [];
  INCARNATE_LOADOUTS = loadouts || [];
  if (!INCARNATE_RECS.length) return;
  // Apply the optimal set so it lands in the Mids export. Refresh on every solve UNLESS
  // the user HAND-PICKED incarnates (build._incarnatesManual) — that way a re-solve for a
  // controller updates stale Spiritual/Assault defaults to the role's Nerve/Control, but
  // a player's deliberate choices are never clobbered.
  const hadNone = Object.keys(build.incarnates).length === 0;
  const applied = hadNone || !build._incarnatesManual;
  if (applied) applyIncarnateRecs(true);
  const card = document.createElement("div");
  card.className = "assess-card";
  card.innerHTML =
    `<div class="assess-head">🜂 <strong>Recommended incarnates</strong> <span class="muted small">(endgame · all slots unlocked)</span></div>`
    + INCARNATE_RECS.map(r =>
        `<div class="assess-line small"><b>${r.slot}:</b> ${r.display}`
        + (r.magnitude ? ` <span class="rt-delta up">${r.magnitude}</span>` : "")
        + (r.always_on ? ' <span class="aoe-tag">ALWAYS-ON</span>' : "")
        + `<br><span class="muted">${r.why}</span></div>`).join("")
    + `<div class="assess-line small">`
    + (applied ? "✓ Applied to your build — they'll be written into the Mids export."
               : `<button class="assess-route" style="width:auto" onclick="applyIncarnateRecs()">Apply these to my build</button>`)
    + `</div>`
    + incarnateLoadoutsHtml();
  $("ai-response").appendChild(card);
}

// Per-content loadouts — incarnates are swappable per encounter, so show the
// fire-farm vs iTrial vs AV Alpha/Destiny picks (the ones that actually differ) and
// let the user swap the whole set with one click.
function incarnateLoadoutsHtml() {
  if (!INCARNATE_LOADOUTS.length) return "";
  const pick = (recs, slot) => (recs.find(r => r.slot === slot) || {}).display || "—";
  const rows = INCARNATE_LOADOUTS.map((lo, i) =>
    `<div class="assess-line small"><b>${lo.label}:</b> `
    + `Alpha ${pick(lo.recs, "Alpha")} · Destiny ${pick(lo.recs, "Destiny")} `
    + `<button class="assess-route" style="width:auto;padding:1px 8px" onclick="applyIncarnateLoadout(${i})">Use</button></div>`
  ).join("");
  return `<div class="assess-head small" style="margin-top:8px">↔ <strong>Swap by content</strong> `
    + `<span class="muted">(incarnates are re-slottable per encounter)</span></div>` + rows;
}

window.applyIncarnateLoadout = function (i) {
  const lo = INCARNATE_LOADOUTS[i];
  if (!lo) return;
  INCARNATE_RECS = lo.recs;
  applyIncarnateRecs();
};

window.applyIncarnateRecs = function (silent) {
  INCARNATE_RECS.forEach(r => {
    build.incarnates[r.slot] = { full_name: r.full_name, display_name: r.display };
  });
  build._incarnatesManual = false;   // these came from the recommendation, not the user
  renderIncarnates();
  refreshBuildViews();               // the incarnates brick above the trays updates too
  if (!silent) recompute();
};

let SOLVE_INTENT = null;   // signature of the last user-CONFIRMED solve intent (role|goal|content)

// State the solver's UNDERSTANDING — the firm role STANDARD for this archetype, or the explicit
// OVERRIDE (Role picker / goal text) that bends it — and wait for the user to confirm BEFORE any
// solve commits. Resolves true (go) / false (user wants to adjust). Fails OPEN (never blocks).
function confirmIntent(req) {
  return new Promise(async (resolve) => {
    let interp;
    try {
      const r = await api("/build/interpret", postJson(req));
      interp = r && r.ok && r.interpretation;
    } catch (e) { resolve(true); return; }
    if (!interp) { resolve(true); return; }
    const out = $("ai-response");
    out.classList.remove("muted");
    const conflict = interp.conflict
      ? `<p class="intent-conflict">⚠️ Your Role picker and goal text point at different roles — I'm going with the <strong>Role picker</strong>. Clear one to resolve the ambiguity.</p>` : "";
    out.innerHTML = `<div class="intent-confirm">
        ${renderMarkdown(interp.banner)}
        ${conflict}
        <p class="muted small">🎯 Targets: ${interp.targets_summary || "—"}</p>
        <p class="muted small">${interp.switch_hint || ""}</p>
        <div class="intent-actions">
          <button id="intent-go" class="solve-btn" style="width:auto">✓ Yes, build it this way</button>
          <button id="intent-adjust" class="ghost-btn" style="width:auto">✗ Let me adjust</button>
        </div></div>`;
    // WALK FAILURE #3 (2026-07-20): this question was rendered into a panel that
    // an AI-free client HID — Solve hung forever on an invisible confirm. The
    // structural fix moved ai-response out of #ai-qa; belt-and-suspenders here:
    // make the question SEEN (scroll to it) and ANNOUNCED (status pointer with
    // the flash), so a pending confirm can never read as dead air.
    out.scrollIntoView({ behavior: "smooth", block: "center" });
    const _st = $("gen-status");
    if (_st) {
      _st.textContent = "⚠ One question before I build — answer above: "
        + "“Yes, build it this way” or “Let me adjust”.";
      _st.classList.remove("wiz-status-flash");
      void _st.offsetWidth;
      _st.classList.add("wiz-status-flash");
    }
    const _clearAsk = () => { if (_st && _st.textContent.startsWith("⚠ One question")) _st.textContent = ""; };
    $("intent-go").addEventListener("click", () => { _clearAsk(); resolve(true); });
    $("intent-adjust").addEventListener("click", () => {
      $("gen-status").textContent = "Adjust the Role or goal text, then Solve again.";
      out.innerHTML = ""; out.classList.add("muted");
      resolve(false);
    });
  });
}

// ── CUSTOM BUILD-TARGETS (Maelwys item 4; Joel's four rulings 2026-07-09) ──
// The editor seeds from the chosen preset (edit an informed default, never a
// blank guess), covers BOTH typed and positional defense (armor sets
// specialize — SR positional, Invuln typed), persists in the save AND as
// named reusable presets (the user's own explicit act). Anything solved
// under custom targets is DERIVED — labeled, never champion-certified.
const _CT_SCALARS = [["recharge", "Recharge", 400], ["recovery", "Recovery", 300],
                     ["regen", "Regeneration", 1000], ["max_hp", "Max HP", 100],
                     ["tohit", "ToHit", 60]];
let _CT_META = null;    // {res_cap, defense_types, resistance_types} from the server

// A custom-targets object with no actual numbers is NOT custom targets (walk
// failure #2: a stale empty object made the chip claim "yours" while the editor
// opened blank — chip and editor must read the SAME truth).
function hasTargetValues(t) {
  if (!t || typeof t !== "object") return false;
  return Object.values(t).some(v =>
    (typeof v === "number" && isFinite(v)) ||
    (v && typeof v === "object" && Object.values(v).some(x => typeof x === "number" && isFinite(x))));
}

// 2b (Joel's close-up screenshot ruling): ONE comprehensible control, not two
// look-alikes. No custom targets → only the "Customize build targets…" button.
// Custom targets present → only the CHIP, which SHOWS the asks it holds
// ("🎯 Your targets: Fire def 45 · Fire res 90 — edit"), opens the editor
// prefilled when clicked, and whose ✕ confirms with its named consequence.
function _targetsSummary(t) {
  const bits = [];
  for (const [ty, v] of Object.entries(t.defense || {}))
    if (typeof v === "number" && v > 0) bits.push(`${ty} def ${v}`);
  for (const [ty, v] of Object.entries(t.resistance || {}))
    if (typeof v === "number" && v > 0) bits.push(`${ty} res ${v}`);
  const scalarLabel = { recharge: "recharge", recovery: "recovery",
                        regen: "regen", max_hp: "max HP", tohit: "to-hit" };
  for (const [k, lbl] of Object.entries(scalarLabel))
    if (typeof t[k] === "number" && t[k] > 0) bits.push(`${lbl} ${t[k]}`);
  if (!bits.length) return "";
  return bits.length <= 4 ? bits.join(" · ")
    : bits.slice(0, 4).join(" · ") + ` · +${bits.length - 4} more`;
}

function updateCustomTargetsChip() {
  if (build._custom_targets && !hasTargetValues(build._custom_targets))
    build._custom_targets = null;          // normalize: empty "custom" is no custom
  const chip = $("custom-targets-chip");
  const btn = $("custom-targets-btn");
  const has = !!build._custom_targets;
  if (chip) {
    chip.classList.toggle("hidden", !has);
    if (has) {
      chip.innerHTML = `🎯 Your targets: ${escHtml(_targetsSummary(build._custom_targets))}`
        + ` <u>— edit</u>`
        + `<button class="ct-clear" type="button" title="Remove your custom targets`
        + ` — the solver returns to the content preset" onclick="event.stopPropagation();`
        + `clearCustomTargets()">✕</button>`;
      chip.onclick = () => openTargetsEditor();
      chip.title = "These are YOUR numbers — the solver targets them instead of the "
        + "preset, and the result is yours, never a certified champion build. "
        + "Click to edit them.";
    }
  }
  // one control at a time: the button offers customization only while no
  // custom targets exist; once they do, the chip IS the control.
  if (btn) btn.classList.toggle("hidden", has);
}

window.clearCustomTargets = function () {
  if (!confirm("Remove your custom targets? The solver returns to the content preset's targets.")) {
    return;
  }
  build._custom_targets = null;
  updateCustomTargetsChip();
  const st = $("gen-status");
  if (st) st.textContent = "Custom targets removed — back to the preset targets.";
};

window.openTargetsEditor = async function () {
  // Callable from BOTH entry points (ruling 2), and EVERY parameter follows
  // one rule (state-lifecycle family, Joel's field reports 07-13 + 07-14):
  // when the WIZARD is open, ITS answers are the current flow's truth; only
  // otherwise does the loaded build speak. Mixing surfaces is how a Stalker's
  // front-line exposure seeded Melee 45 into a fresh Blaster's editor.
  const wizOpen = $("respec-wizard") && !$("respec-wizard").classList.contains("hidden");
  const pick = (wizId, fallback) =>
    (wizOpen && $(wizId) && $(wizId).value) || fallback || "";
  const content = pick("wiz-content", $("preset-content") && $("preset-content").value);
  const role = pick("wiz-role", $("preset-role") && $("preset-role").value);
  const at = pick("wiz-at", build.archetype
    || ($("sel-archetype") && $("sel-archetype").value));
  const exposure = pick("wiz-exposure", build._exposure);
  const primary = pick("wiz-primary", build.primary);
  const secondary = pick("wiz-secondary", build.secondary);
  const [seed, lib] = await Promise.all([
    api(`/targets/preset?content=${encodeURIComponent(content)}&role=${encodeURIComponent(role)}`
        + `&archetype=${encodeURIComponent(at)}`
        + `&exposure=${encodeURIComponent(exposure)}`
        + `&primary=${encodeURIComponent(primary)}`
        + `&secondary=${encodeURIComponent(secondary)}`),
    api("/target_presets"),
  ]);
  if (!seed || !seed.ok) return;
  _CT_META = seed;
  // Active custom targets win over the preset seed — you edit what's applied.
  let t = (hasTargetValues(build._custom_targets) && build._custom_targets)
    || (hasTargetValues(seed.targets) && seed.targets) || {};
  // WALK FAILURE #2 (import path): with Content/Role unset the preset seed is a
  // blank slate, and the editor opened all-EMPTY on a loaded build. Prefill from
  // the build's CURRENT numbers instead (the last recompute's totals) — you
  // customize from where you are, and the editor never opens blank on a real
  // build. Display seeding only; nothing is applied until the user saves.
  if (!hasTargetValues(t) && build.powers.length && LAST_TOTALS && typeof LAST_TOTALS === "object") {
    const cur = { defense: {}, resistance: {} };
    for (const [ty, d] of Object.entries(LAST_TOTALS.defense || {}))
      if (d && typeof d.value === "number") cur.defense[ty] = Math.round(d.value * 2) / 2;
    for (const [ty, d] of Object.entries(LAST_TOTALS.resistance || {}))
      if (d && typeof d.value === "number") cur.resistance[ty] = Math.round(d.value * 2) / 2;
    if (typeof (LAST_TOTALS.recharge || {}).value === "number")
      cur.recharge = Math.round(LAST_TOTALS.recharge.value);
    if (typeof (LAST_TOTALS.recovery || {}).value === "number")
      cur.recovery = Math.round(LAST_TOTALS.recovery.value);
    if (hasTargetValues(cur)) t = cur;
  }
  const typed = (_CT_META.defense_types || []).filter(x => !["Melee", "Ranged", "AoE"].includes(x));
  const row = (grp, ty, val) =>
    `<label class="ct-field">${ty}<input type="number" min="0" step="0.5"
       data-ct="${grp}" data-ty="${ty}" value="${val != null ? val : ""}"></label>`;
  const dv = (t.defense || {});
  const rv = (t.resistance || {});
  let host = $("targets-modal");
  if (!host) {
    host = document.createElement("div");
    host.id = "targets-modal";
    document.body.appendChild(host);
  }
  const presetNames = Object.keys((lib && lib.presets) || {});
  host.innerHTML = `<div class="ct-card">
    <h3>Customize build targets
      <button class="iconbtn" onclick="closeTargetsEditor()" title="close">✕</button></h3>
    <p class="muted small">Seeded from ${content || role ? "your preset" : "a blank slate"} —
      set a number to chase it, clear it (or 0) to drop that target. The solver
      gets as close as 67 slots allow and reports honestly when the ask exceeds
      the budget. Solves under custom targets are YOUR builds — never labeled
      as certified champion builds.</p>
    <p class="muted small">ℹ️ <strong>What clearing a field means:</strong> a cleared
      field is <em>no ask</em> — the solver stops chasing that number, nothing more.
      Your build's own innate stats on that axis still count and still show in
      totals; you're dropping the demand, not the stat. Your targets also shape
      the <strong>power picks</strong> on a fresh auto-pick, and anything not fully
      reachable is reported with numbers and a suggested fix, never traded silently.</p>
    <div class="ct-grid">
      <div><h4>Defense — typed <span class="muted small">(0–60)</span></h4>
        ${typed.map(ty => row("defense", ty, dv[ty])).join("")}</div>
      <div><h4>Defense — positional <span class="muted small">(0–60)</span></h4>
        ${["Melee", "Ranged", "AoE"].map(ty => row("defense", ty, dv[ty])).join("")}
        <h4>Globals</h4>
        ${_CT_SCALARS.map(([k, lab, cap]) =>
          `<label class="ct-field">${lab} <span class="muted small">(0–${cap})</span>
             <input type="number" min="0" step="5" data-ct="scalar" data-ty="${k}"
               value="${t[k] != null ? t[k] : ""}"></label>`).join("")}</div>
      <div><h4>Resistance <span class="muted small">(0–${_CT_META.res_cap} on this archetype)</span></h4>
        ${(_CT_META.resistance_types || []).map(ty => row("resistance", ty, rv[ty])).join("")}</div>
    </div>
    <div class="ct-actions">
      <button class="mini" onclick="applyCustomTargets()">✓ Use these targets</button>
      <button class="mini" onclick="resetTargetsEditor()">Reset to preset</button>
      <button class="mini" onclick="saveTargetPreset()">Save as my preset…</button>
      ${presetNames.length ? `<select id="ct-preset-pick">
          <option value="">— my presets —</option>
          ${presetNames.map(n => `<option>${escHtml(n)}</option>`).join("")}
        </select>
        <button class="mini" onclick="loadTargetPreset()">Load</button>
        <button class="mini" onclick="deleteTargetPreset()">Delete</button>` : ""}
      <button class="mini" onclick="closeTargetsEditor()">Cancel</button>
    </div></div>`;
  host.classList.remove("hidden");
};

function _collectTargetsEditor() {
  const out = { defense: {}, resistance: {} };
  document.querySelectorAll("#targets-modal input[data-ct]").forEach(inp => {
    const v = parseFloat(inp.value);
    if (!v || v <= 0) return;
    const grp = inp.dataset.ct, ty = inp.dataset.ty;
    if (grp === "scalar") out[ty] = v;
    else out[grp][ty] = v;
  });
  if (!Object.keys(out.defense).length) delete out.defense;
  if (!Object.keys(out.resistance).length) delete out.resistance;
  return out;
}

window.applyCustomTargets = function () {
  const t = _collectTargetsEditor();
  const any = t.defense || t.resistance
    || _CT_SCALARS.some(([k]) => t[k] != null);
  build._custom_targets = any ? t : null;
  updateCustomTargetsChip();
  closeTargetsEditor();
  const st = $("gen-status");
  if (st) st.textContent = any
    ? "Custom targets set — hit Solve to slot toward YOUR numbers."
    : "No targets set — back to the preset.";
  autoSaveTick();    // ruling 4: custom targets persist in the save
};
window.resetTargetsEditor = function () {
  build._custom_targets = null;
  updateCustomTargetsChip();
  openTargetsEditor();     // re-seed from the preset
};
window.closeTargetsEditor = function () {
  const m = $("targets-modal");
  if (m) m.classList.add("hidden");
};
window.saveTargetPreset = async function () {
  const name = prompt("Name this target preset (yours, reusable on any build):");
  if (!name) return;
  await api("/target_presets", postJson({ name, targets: _collectTargetsEditor() }));
  openTargetsEditor();     // re-render with the library refreshed
};
window.loadTargetPreset = async function () {
  const sel = $("ct-preset-pick");
  if (!sel || !sel.value) return;
  const lib = await api("/target_presets");
  const t = lib && lib.presets && lib.presets[sel.value];
  if (!t) return;
  build._custom_targets = t;
  updateCustomTargetsChip();
  openTargetsEditor();     // re-render seeded from the loaded preset
};
window.deleteTargetPreset = async function () {
  const sel = $("ct-preset-pick");
  if (!sel || !sel.value) return;
  if (!confirm(`Delete your target preset "${sel.value}"?`)) return;
  await fetch(`/target_presets/${encodeURIComponent(sel.value)}`, { method: "DELETE" });
  openTargetsEditor();
};

async function solveSlotting(perkFocus, opts) {
  // Called from a perk chip (perkFocus = string), the Solve button's click listener
  // (perkFocus = a MouseEvent), or applyRoute (opts.targets = an alternative route).
  // Only a string is a real perk focus.
  if (typeof perkFocus !== "string") perkFocus = null;
  opts = opts || {};
  const status = $("gen-status");
  if (!build.archetype || !build.powers.length) {
    status.textContent = "Add some powers first, then solve the slotting.";
    return;
  }
  // Snapshot the CURRENT totals so a manual-edit Solve shows the same before/after diff that
  // imports get (imports keep using IMPORT_BEFORE, which also carries slot-level changes).
  const solveBefore = (LAST_TOTALS && typeof LAST_TOTALS === "object")
    ? { totals: LAST_TOTALS, name: "your previous slotting" } : null;
  const goal = $("gen-goal").value.trim();
  const content = $("preset-content") ? $("preset-content").value : "";
  const role = $("preset-role") ? $("preset-role").value : "";
  if (!goal && !content && !opts.targets && !build._custom_targets) {
    // WALK FAILURE #2 (2026-07-20): this gate wrote its answer into a status line
    // that sat BELOW THE FOLD — Solve and every perk-focus chip read as dead
    // controls after an import (Content/Role start unset). Same class as the
    // wizard gate: name the missing field, ring it, and make the answer visible.
    flagMissing([$("preset-content")],
      "Pick a Content preset first (highlighted in red) — Role refines it. "
      + "Or type a goal, or set custom targets.", status);
    return;
  }
  // Confirm-understanding gate (initial solve only — perk re-solves & applied routes skip it):
  // state the firm role STANDARD vs any override and get the user's OK before committing. Only
  // re-prompts when the intent (role/goal/content/exposure) changes, so tweaks don't nag.
  const isRefine = !!perkFocus || !!opts.targets;
  const intentSig = JSON.stringify([role, goal, content, build._exposure || ""]);
  if (opts.skipConfirm) {
    SOLVE_INTENT = intentSig;          // caller (wizard) already gathered + confirmed the intent
  } else if (!isRefine && SOLVE_INTENT !== intentSig) {
    const ok = await confirmIntent({ archetype: build.archetype, role: role || null, goal,
      content: content || null, primary: build.primary, secondary: build.secondary });
    if (!ok) return;
    SOLVE_INTENT = intentSig;
  }
  const btn = $("solve-btn");
  const restore = setWorking(btn, perkFocus
    ? `⏳ Re-solving (${perkFocus})…` : "⏳ Solving slotting…");
  // Elapsed-seconds pulse instead of the old static "(deterministic, ~1s)"
  // line — which was DISHONEST copy for the hard combos (measured 13s).
  const stopPulse = startSolvePulse(status, perkFocus
    ? `Re-solving with spare slots focused on ${perkFocus}`
    : "Solving optimal slotting");
  try {
    // v35 UX batch: per-power LOCKS carry preservation now — the checkbox is a
    // master switch over them (synced before this point), so the server gets
    // the truth per power instead of one coarse flag. preserve:false always;
    // a locked power comes back byte-identical (pinned), an unlocked one is
    // fully fair game — that IS "unlock to let a re-solve touch it".
    const retool = isRetool();
    const preserve = false;
    // keep_layout (tightest): stay within placed slots + keep un-upgraded cheap
    // IOs — its own choice now, no longer chained to the preserve checkbox.
    const keep_layout = retool
      && ($("keeplayout-toggle") ? $("keeplayout-toggle").checked : false);
    // snapshot the PRE-solve powers — reused for the request AND the post-solve
    // assessment (which re-solves alternatives from this same starting point).
    const presolvePowers = build.powers.map(p => ({ full_name: p.full_name,
      slots: p.slots, earned_slot_count: p.earned_slot_count,
      locked: !!p._locked }));
    const res = await api("/build/solve", postJson({
      archetype: build.archetype, goal, tier: build.tier || "premium",
      content: content || null, role: role || null, exposure: build._exposure || null,
      targets: opts.targets || null,    // an applied alternative route overrides
      custom_targets: build._custom_targets || null,   // YOUR numbers (derived, never certified)
      perk_focus: perkFocus || null, roles: selectedRoles(), pvp: build.pvp,
      preserve, keep_layout,
      // powerset display names -> context-aware goal interpretation (e.g. a
      // Kinetics support set + "fire farm" = supporting a farmer, not solo)
      primary_display: build.primary_display, secondary_display: build.secondary_display,
      powers: presolvePowers,
    }));
    if (!res.ok) {
      status.textContent = res.response || "Solve failed.";
      // surface the failure (and any goal interpretation) in the panel, not just
      // the small status line, so it's never silent.
      const out = $("ai-response");
      out.classList.remove("muted");
      let em = `⚠️ **Couldn't solve.** ${res.response || "Solve failed."}`;
      if (res.understood && res.understood.length) {
        em += `\n\n📋 I read your goal as: ${res.understood.join(", ")}.`;
      }
      out.innerHTML = renderMarkdown(em);
      return;
    }
    const byName = {};
    res.powers.forEach(p => { byName[p.full_name] = p; });
    build.powers.forEach(p => {
      const np = byName[p.full_name];
      if (np) {
        p.slots = np.slots; p.slotCount = np.slotCount;
        // Solve re-seats pick levels around the new slotting (a level-49 pick can
        // only ever hold 4 slots) — adopt them so the wall and respec order agree.
        if (np.pick_level) p.pick_level = np.pick_level;
      }
    });
    renderPowers();
    recompute();
    const out = $("ai-response");
    out.classList.remove("muted");
    const addedTxt = (res.added_slots != null)
      ? `${res.added_slots}/${res.added_budget || 67} added slots (+1 free base per power)`
      : `${res.slots_used} slots`;
    let md = "";
    if (res.understood && res.understood.length) {
      md += `📋 **I read your goal as:** ${res.understood.join(", ")}.`;
      if (res.target_summary) md += `\n\n**Targeting:** ${res.target_summary}.`;
      md += "\n\n";
    } else if (res.target_summary) {
      md += `📋 **Targeting:** ${res.target_summary}.\n\n`;
    }
    md += `**Optimal slotting solved** — ${addedTxt}, no AI guesswork`;
    md += perkFocus ? ` (spare slots → ${perkFocus}).` : ".";
    // v35 (#15) refuse-with-remedy: any DECLARED ask the solve couldn't fully
    // reach is named with numbers and a concrete next move — never silent.
    if (res.ask_remedies && res.ask_remedies.length) {
      md += "\n\n⚖️ **Asks I couldn't fully reach:**\n\n" + res.ask_remedies.map(r =>
        `- **${r.stat}**: you asked ${r.asked}, best reached ${r.reached} — ${r.remedy}.`
      ).join("\n");
    }
    // Be explicit about what happened to existing investment — but only for a
    // RETOOL build (a from-scratch/AI build has no prior investment to report on).
    const removed = res.removed_expensive || [];
    const lockedN = build.powers.filter(p => p._locked).length;
    if (retool) {
      if (lockedN) {
        md += `\n\n🔒 **${lockedN} locked power${lockedN === 1 ? "" : "s"} left exactly as you slotted ${lockedN === 1 ? "it" : "them"}** — a lock means byte-for-byte untouched, empty slots included. Everything unlocked was re-slotted toward the goal. Unlock a power (padlock on its card) to let a future re-solve improve it.`;
        const lockedEmpty = build.powers.filter(p => p._locked
          && (p.slots || []).some(s => !s)).length;
        if (lockedEmpty) {
          md += ` ℹ️ ${lockedEmpty} locked power${lockedEmpty === 1 ? " has" : "s have"} empty slots the solve was not allowed to fill.`;
        }
        if (keep_layout) {
          md += " 📐 **Kept your slot layout** on the unlocked powers — stayed within the slots you placed (no added slots); any cheap IO not upgraded by a goal-advancing set was left in place.";
        }
        if (removed.length) {
          md += "\n\n⚠️ **Had to drop some set pieces to fit** (an unlocked power ran out of room):\n\n"
            + removed.map(r => `- ${r.power}: ${r.set} (${r.before}→${r.after})`).join("\n");
        }
      } else if (res.preserved) {
        const kept = (res.kept_sets || []).length;
        md += `\n\n🔒 **Preserved your sets** — kept ${kept} existing IO set${kept === 1 ? "" : "s"} + unique globals; only re-slotted generic IOs and empty slots toward the goal.`;
        if (keep_layout) {
          md += " 📐 **Kept your slot layout** — stayed within the slots you placed (no added slots); any cheap IO not upgraded by a goal-advancing set was left in place.";
        }
        if (removed.length) {
          md += "\n\n⚠️ **Had to drop some set pieces to fit** (a power ran out of room):\n\n"
            + removed.map(r => `- ${r.power}: ${r.set} (${r.before}→${r.after})`).join("\n");
        }
      } else if (removed.length) {
        md += "\n\n⚠️ **Full re-slot — removed these expensive IOs you had:**\n\n"
          + removed.map(r => `- ${r.power}: ${r.set} (${r.before}→${r.after})`).join("\n")
          + "\n\n_Turn on \"Preserve my IO sets\" to keep these and only re-slot generic IOs instead._";
      }
    }
    md += "\n\nAchieved vs target:\n\n";
    md += res.report.map(r =>
      `- ${r.stat}: **${r.have}%** / ${r.want}% ${r.met ? "✅" : "— short"}`).join("\n");
    if (res.report.some(r => !r.met)) {
      md += res.preserved
        ? "\n\n_Some targets are short. With your sets preserved there may not be enough "
          + "free slots — untick \"Preserve my IO sets\" to let the solver respec for a "
          + "better fit (it will flag what it removes)._"
        : "\n\n_\"Short\" targets aren't reachable with these powers — change "
          + "powers or accept the trade._";
    }
    // Optimization headroom: what a full respec would GAIN vs what it would COST.
    const h = res.headroom;
    if (h && (h.gains.length || h.n_lost)) {
      md += "\n\n---\n\n### 📊 Go further? (full respec)\n";
      if (h.gains.length) {
        md += "\nA full re-slot could reach:\n\n"
          + h.gains.map(g => `- ${g.stat}: ${g.from}% → **${g.to}%**  (+${g.delta})`).join("\n");
      } else {
        md += "\n_No meaningful stat gain available beyond your preserved build._";
      }
      if (h.n_lost) {
        const items = h.lost.slice(0, 8).map(l => `${l.set} (${l.power})`).join(", ");
        md += `\n\n**Cost:** it would change **${h.n_lost}** of your set${h.n_lost === 1 ? "" : "s"} — ${items}${h.lost.length > 8 ? " …" : ""}`;
      }
      md += `\n\n_${h.verdict}_`;
    }
    out.innerHTML = renderMarkdown(md);
    // If this build was imported, show the before/after improvement diff + a
    // clear "what changed" pop-up (main solve only, not the perk-chip re-solves).
    const diffBefore = IMPORT_BEFORE || solveBefore;
    if (diffBefore) renderImproveDiff(diffBefore, res);
    // Don't interrupt — make the "what changed" window available on demand instead.
    if (IMPORTED_POWERS) { CHANGES_AVAILABLE = true; recompute(); }
    // Plain-language perk choice: targets are solved; what should spare slots push?
    const chips = PERK_FOCUSES.map(([f, label]) =>
      `<button class="perk-chip${perkFocus === f ? " on" : ""}" onclick="solveSlotting('${f}')">${label}</button>`).join("");
    out.insertAdjacentHTML("beforeend",
      `<div class="perk-pick"><span class="muted small">Targets solved — point the `
      + `leftover slots at what you want most:</span>`
      + `<div class="perk-chips">${chips}</div></div>`);
    // Assessment card: what this optimized + pre-computed alternative routes with
    // real deltas. Only on a MAIN/route solve (not the lightweight perk-chip re-solves).
    if (!perkFocus) renderAssessment(presolvePowers,
      { content, role, goal, preserve, keep_layout });
    if (!perkFocus && res.incarnate_recs) renderIncarnateRecs(res.incarnate_recs, res.incarnate_loadouts);
    // WALK FAILURE #2: a solve that changes nothing must SAY so — "solved" with
    // an unchanged build reads as a dead control. Compare the slot signature.
    const _sig = ps => JSON.stringify((ps || []).map(p =>
      [p.full_name, (p.slots || []).map(s => s && s.piece_uid)]));
    const unchanged = _sig(presolvePowers) === _sig(res.powers);
    status.textContent = (unchanged
      ? "✓ No changes — your current slotting already meets this goal."
      : (res.added_slots != null
        ? `✓ Slotting solved (${res.added_slots}/${res.added_budget || 67} added slots).`
        : `✓ Slotting solved (${res.slots_used} slots).`))
      // Derived-build labeling (Joel's constraint): a custom-target solve is
      // YOURS — it never reads as a certified champion result.
      + (res.custom_targets ? " Built to YOUR custom targets — not a certified champion build." : "");
    status.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (e) {
    status.textContent = "Solve error: " + e;
  } finally {
    stopPulse();   // cleared before restore so no tick overwrites final text
    restore();
  }
}
window.solveSlotting = solveSlotting;

// Before/after diff for an imported build that was just re-solved.
// Pop-up summary of exactly what the solve changed from the imported build:
// which empty/generic slots were filled, with what, per power.
function showChangeModal() {
  if (!IMPORTED_POWERS) return;
  const beforeBy = {};
  IMPORTED_POWERS.forEach(p => { beforeBy[p.full_name] = p; });
  const summarize = (slots) => {
    const sets = {}; let cheap = 0, empty = 0;
    (slots || []).forEach(s => {
      if (!s) { empty++; return; }
      if (s.set_uid && s.set_name) sets[s.set_name] = (sets[s.set_name] || 0) + 1;
      else if (s.piece_uid) cheap++;
      else empty++;
    });
    return { sets, cheap, empty };
  };
  const key = (i) => Object.keys(i.sets).sort().join("|") + `|c${i.cheap}|e${i.empty}`;
  // Plain-language delta for one power: what sets were ADDED, what was KEPT,
  // how many empty slots got filled, and how many cheap IOs were replaced.
  const describe = (bi, ai) => {
    const added = [];
    for (const [n, c] of Object.entries(ai.sets)) {
      const bc = bi.sets[n] || 0;
      if (c > bc) added.push(c > 1 ? `${n} ×${c}` : n);
    }
    const kept = Object.keys(bi.sets).filter(n => ai.sets[n]);
    const filled = Math.max(0, bi.empty - ai.empty);
    const cheapGone = Math.max(0, bi.cheap - ai.cheap);
    const parts = [];
    if (added.length) parts.push(`<span class="act-add">added ${added.join(", ")}</span>`);
    if (filled) parts.push(`<span class="act-fill">filled ${filled} empty slot${filled > 1 ? "s" : ""}</span>`);
    if (cheapGone) parts.push(`<span class="act-fill">replaced ${cheapGone} common IO${cheapGone > 1 ? "s" : ""}</span>`);
    if (kept.length) parts.push(`<span class="act-keep">kept ${kept.join(", ")}</span>`);
    if (ai.cheap) parts.push(`<span class="act-keep">kept ${ai.cheap} common IO${ai.cheap > 1 ? "s" : ""}</span>`);
    return parts.join(" · ") || "rearranged";
  };
  const changed = []; let unchanged = 0;
  build.powers.forEach(p => {
    const b = beforeBy[p.full_name];
    if (!b) return;
    const bi = summarize(b.slots), ai = summarize(p.slots);
    if (key(bi) !== key(ai)) {
      changed.push(`<div class="change-line"><span class="pname">${p.display_name}</span> — ${describe(bi, ai)}</div>`);
    } else unchanged++;
  });
  let html = `<p class="muted small">Your IO sets stayed in place — the solver filled empty &amp; generic slots toward your goal. <strong>${changed.length}</strong> power(s) changed, ${unchanged} unchanged.</p>`;
  html += changed.length ? changed.join("")
    : `<p class="muted small">Nothing to change — your build was already on-target.</p>`;
  $("change-body").innerHTML = html;
  $("change-title").textContent = `What changed — ${(IMPORT_BEFORE && IMPORT_BEFORE.name) || "imported build"}`;
  $("change-modal").classList.remove("hidden");
}
window.showChangeModal = showChangeModal;

function renderImproveDiff(before, res) {
  const report = $("import-report");
  if (!report) return;
  const after = res.totals || {};
  const bt = before.totals || {};
  const rows = [];
  const pct = (o, path) => {
    const v = path.reduce((a, k) => (a ? a[k] : undefined), o);
    return typeof v === "number" ? v : (v && v.value);
  };
  const stat = (label, b, a) => {
    if (b == null && a == null) return;
    const d = (a || 0) - (b || 0);
    if (Math.abs(d) < 0.1) return;
    const arrow = d > 0 ? "▲" : "▼";
    const cls = d > 0 ? "up" : "down";
    rows.push(`<tr><td>${label}</td><td>${(b || 0).toFixed(1)}</td><td>${(a || 0).toFixed(1)}</td>`
      + `<td class="diff-${cls}">${arrow} ${Math.abs(d).toFixed(1)}</td></tr>`);
  };
  ["Smashing", "Fire", "Energy", "Melee", "Ranged", "AoE"].forEach(t => {
    stat(`Def ${t}`, pct(bt, ["defense", t, "value"]), pct(after, ["defense", t, "value"]));
  });
  ["Smashing", "Fire", "Energy"].forEach(t => {
    stat(`Res ${t}`, pct(bt, ["resistance", t, "value"]), pct(after, ["resistance", t, "value"]));
  });
  stat("Recharge", pct(bt, ["recharge", "value"]), pct(after, ["recharge", "value"]));
  stat("Max HP", pct(bt, ["max_hp", "value"]), pct(after, ["max_hp", "value"]));
  if (bt.offense || after.offense) {
    if ((bt.offense && bt.offense.aoe_count) || (after.offense && after.offense.aoe_count)) {
      stat("AoE DPS", bt.offense && bt.offense.aoe_dps, after.offense && after.offense.aoe_dps);
    }
    stat("ST DPS", bt.offense && bt.offense.st_dps, after.offense && after.offense.st_dps);
  }
  stat("Set bonuses", bt.applied_bonus_count, after.applied_bonus_count);

  // slot changes: which powers got different sets
  const afterSlots = {};
  (res.powers || []).forEach(p => {
    const sets = {};
    (p.slots || []).forEach(s => { const n = s && (s.set_name || s.piece_name) || "—"; sets[n] = (sets[n] || 0) + 1; });
    afterSlots[p.full_name] = sets;
  });
  const changes = [];
  for (const [fn, info] of Object.entries(before.slots || {})) {
    const a = afterSlots[fn] || {};
    const bKey = Object.keys(info.sets).sort().join(",");
    const aKey = Object.keys(a).sort().join(",");
    if (bKey !== aKey) {
      const fmt = o => Object.keys(o).length ? Object.entries(o).map(([n, c]) => `${n}×${c}`).join(", ") : "(empty)";
      changes.push(`<li><strong>${info.display}</strong>: ${fmt(info.sets)} → ${fmt(a)}</li>`);
    }
  }
  const tbl = rows.length
    ? `<table class="diff-tbl"><tr><th>Stat</th><th>Before</th><th>After</th><th>Δ</th></tr>${rows.join("")}</table>`
    : `<p class="muted small">No net stat change (the import was already on-target for this goal).</p>`;
  report.classList.remove("hidden");
  report.innerHTML = `
    <div class="import-head"><strong>Improvement — ${before.name}</strong>
      <span class="muted small">solved for your goal · review before exporting</span></div>
    ${tbl}
    ${changes.length ? `<details open><summary>${changes.length} power(s) re-slotted</summary><ul class="crit-list">${changes.join("")}</ul></details>` : ""}
    <p class="muted small">Happy with it? Use <strong>⬇ Export to Mids Reborn</strong> above to save the improved build.</p>`;
}

async function applyGeneratedBuild(res) {
  build.imported = false;   // AI/optimize build from scratch — no investment to preserve
  // Load every powerset this build uses so its powers are available
  const used = [build.primary, build.secondary,
    ...(res.pools_used || []), res.epic_used].filter(Boolean);
  for (const ps of used) await loadPowers(ps);

  // Reflect pool selections
  const poolSels = [...document.querySelectorAll(".pool-sel")];
  build.pools = (res.pools_used || []).slice(0, 4);
  build.pools_display = build.pools.map((ps) => {
    const e = (POWERSETS_CACHE.pools || []).find((x) => x.full_name === ps);
    return e ? e.display_name : ps;
  });
  poolSels.forEach((s, i) => { s.value = build.pools[i] || ""; });

  // Reflect epic selection
  if (res.epic_used) {
    $("sel-epic").value = res.epic_used;
    build.epic = res.epic_used;
    const e = (POWERSETS_CACHE.epic || []).find((x) => x.full_name === res.epic_used);
    build.epic_display = e ? e.display_name : res.epic_used;
  }

  // Powers (already resolved + validated server-side)
  build.powers = (res.powers || []).map((p) => ({
    full_name: p.full_name,
    display_name: p.display_name,
    powerset_full_name: p.powerset_full_name,
    accepted_set_category_ids: p.accepted_set_category_ids || [],
    accepted_set_categories: p.accepted_set_categories || [],
    power_type: p.power_type,
    include_in_totals: p.include_in_totals !== undefined
      ? p.include_in_totals : (p.power_type === 1 || p.power_type === 2),
    slotCount: p.slotCount,
    slots: p.slots,
    // The server seats pick levels around the slotting + the creation rules —
    // dropping this field made the wall badge the first two cards "~L1" (field
    // report: Alkaloid AND Envenom both shown as level-1 choices).
    pick_level: p.pick_level,
    level_available: p.level_available,
  }));

  // Incarnates
  build.incarnates = {};
  for (const [slot, v] of Object.entries(res.incarnates || {})) build.incarnates[slot] = v;
  document.querySelectorAll("#incarnate-selectors select").forEach((s) => {
    const v = build.incarnates[s.dataset.slot];
    s.value = v ? v.full_name : "";
  });

  renderPowers();
  recompute();
}

// Minimal, self-contained Markdown -> HTML (offline; no external libs).
// Handles headings, tables, bold/italic/code, lists, hr, paragraphs.
function renderMarkdown(md) {
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const inline = (s) => esc(s)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*]+)\*(?!\*)/g, "$1<em>$2</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
  const lines = md.replace(/\r/g, "").split("\n");
  const isHr = (l) => /^\s*([-*_])\1\1+\s*$/.test(l);
  const isUl = (l) => /^\s*[-*]\s+/.test(l);
  const isOl = (l) => /^\s*\d+\.\s+/.test(l);
  const isH = (l) => /^#{1,6}\s/.test(l);
  const isTblRow = (l) => /^\s*\|/.test(l);
  let html = "", i = 0;
  while (i < lines.length) {
    const line = lines[i];
    // Table: a |row| followed by a |---|---| separator
    if (isTblRow(line) && i + 1 < lines.length &&
        /^\s*\|?[\s:|-]*-[\s:|-]*$/.test(lines[i + 1])) {
      const cells = (l) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const header = cells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && isTblRow(lines[i])) { rows.push(cells(lines[i])); i++; }
      html += "<table><thead><tr>" +
        header.map((h) => `<th>${inline(h)}</th>`).join("") +
        "</tr></thead><tbody>" +
        rows.map((r) => "<tr>" + r.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>").join("") +
        "</tbody></table>";
      continue;
    }
    const h = /^(#{1,6})\s+(.*)$/.exec(line);
    if (h) { html += `<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`; i++; continue; }
    if (isHr(line)) { html += "<hr>"; i++; continue; }
    if (isUl(line)) {
      html += "<ul>";
      while (i < lines.length && isUl(lines[i])) {
        html += `<li>${inline(lines[i].replace(/^\s*[-*]\s+/, ""))}</li>`; i++;
      }
      html += "</ul>"; continue;
    }
    if (isOl(line)) {
      html += "<ol>";
      while (i < lines.length && isOl(lines[i])) {
        html += `<li>${inline(lines[i].replace(/^\s*\d+\.\s+/, ""))}</li>`; i++;
      }
      html += "</ol>"; continue;
    }
    if (/^\s*$/.test(line)) { i++; continue; }
    const para = [];
    while (i < lines.length && !/^\s*$/.test(lines[i]) && !isTblRow(lines[i]) &&
           !isH(lines[i]) && !isUl(lines[i]) && !isOl(lines[i]) && !isHr(lines[i])) {
      para.push(lines[i]); i++;
    }
    html += `<p>${para.map(inline).join("<br>")}</p>`;
  }
  return html;
}

init();
