// ── THE GUIDED TOUR ──────────────────────────────────────────────────────────
// A self-paced walkthrough of every area of the app.
//
// THE TOUR RUNS OVER A FAKE SCREEN, NEVER THE LIVE APP (Joel, 2026-07-27,
// second ruling — the first design toured the live page and dead-ended
// whenever the thing a step described was not on screen, which on a fresh
// install was almost everything). When any tour starts, this file paints a
// full-screen MOCK: a made-up Brute damage build with every panel populated,
// plus a copy of the opening menu for the Getting-started chapter. Every step
// highlights its subject on that mock, so part, some, or all of the tour works
// from anywhere, in any app state, with nothing loaded at all.
//
// THREE RULES THIS FILE IS BUILT AROUND (Joel, 2026-07-27):
//
//  1. IT NEVER TOUCHES YOUR WORK. The mock is a picture. Nothing in here
//     writes to `build`, opens a character, runs a solve, or changes a
//     setting -- when the tour closes, the app is exactly as you left it.
//
//  2. YOU SET THE PACE. Nothing advances on a timer. Next, Back, Esc, and a
//     visible position count, because people read at different speeds and a
//     walkthrough that moves on its own is a walkthrough nobody finishes.
//
//  3. IT MUST STAY TRUE AS THE APP CHANGES. Every step's `target` still names
//     the REAL control's id, and the mock marks its stand-in for that control
//     with data-for="<that id>". tools/audit_tour.py fails if a step's real id
//     stops existing in the app (the content went stale) OR if the mock has no
//     stand-in for it (the tour would point at nothing). Rename a control and
//     the audit says which step went stale, in the same run that renamed it.
//     (`absent` fields on steps are legacy from the live-page design and are
//     no longer rendered.)
//
// ADDING OR CHANGING A STEP: edit TOUR_STEPS below, give the mock a
// data-for element for the target, then run
//   python tools/audit_tour.py


// ── Annotated diagrams ───────────────────────────────────────────────────────
// Some things cannot be explained in prose. "The + and - move slots between
// powers" means nothing until you can SEE which button is which (Joel,
// 2026-07-27: point at the buttons, "like a + or -, can be identified").
//
// Inline SVG rather than screenshots, deliberately: it stays sharp at any size,
// it takes its colours from the app's theme so it is never a light-mode picture
// on a dark panel, it adds no files to the install, and -- the reason that
// matters most -- a screenshot of this app would be out of date within a release
// or two, while a drawing of "a card with these controls on it" stays true.
const TOUR_DIAGRAMS = {
  powerCard: `
<svg viewBox="0 0 440 210" class="tour-svg" role="img"
     aria-label="An annotated power card showing its information button, level, padlock, minus, plus, drop button and enhancement slots"><defs><marker id="tourArrowHead" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L8 4 L0 8 z" class="d-head"/></marker></defs>
  <rect x="96" y="52" width="248" height="86" rx="8" class="d-card"/>
  <circle cx="118" cy="72" r="9" class="d-ico"/>
  <text x="134" y="77" class="d-name">Fire Blast</text>
  <!-- ⚠ The info button sits at 214, not 196. MEASURED: the name runs to
       x=192.5 and a circle at cx=196 (r=7) starts at x=189, so the power name
       was drawn UNDERNEATH it (Joel, 2026-08-02: "the power name buried under
       some characters"). 214 leaves a clear 14px gap and room for a longer
       name. Its arrow and label move with it - an annotation pointing at where
       the control USED to be is worse than the overlap. -->
  <circle cx="214" cy="72" r="7" class="d-ctl d-hot"/><text x="214" y="76" class="d-glyph">i</text>
  <rect x="106" y="88" width="26" height="14" rx="7" class="d-chip d-hot"/><text x="119" y="99" class="d-lvl">L6</text>
  <rect x="246" y="86" width="18" height="18" rx="4" class="d-ctl d-hot"/><text x="255" y="99" class="d-glyph">•</text>
  <rect x="268" y="86" width="18" height="18" rx="4" class="d-ctl d-hot"/><text x="277" y="100" class="d-glyph">–</text>
  <rect x="290" y="86" width="18" height="18" rx="4" class="d-ctl d-hot"/><text x="299" y="100" class="d-glyph">+</text>
  <rect x="312" y="86" width="18" height="18" rx="4" class="d-ctl d-hot"/><text x="321" y="100" class="d-glyph">x</text>
  <circle cx="118" cy="122" r="8" class="d-slot d-hot"/><circle cx="140" cy="122" r="8" class="d-slot d-hot"/>
  <circle cx="162" cy="122" r="8" class="d-slot d-hot"/><circle cx="184" cy="122" r="8" class="d-slot d-hot"/>
  <path d="M214 40 L214 62" class="d-arrow"/><text x="214" y="32" class="d-lbl d-mid">its full details</text>
  <path d="M60 96 L102 96" class="d-arrow"/><text x="56" y="99" class="d-lbl d-end">level</text>
  <path d="M255 168 L255 108" class="d-arrow"/><text x="255" y="182" class="d-lbl d-mid">lock</text>
  <path d="M300 168 L288 108" class="d-arrow"/><text x="312" y="182" class="d-lbl d-mid">slots -/+</text>
  <path d="M370 96 L334 96" class="d-arrow"/><text x="374" y="99" class="d-lbl">drop it</text>
  <path d="M150 168 L150 132" class="d-arrow"/><text x="150" y="182" class="d-lbl d-mid">enhancement slots</text>
</svg>`,
};
// (statBar and headerRow diagrams retired with the tabbed rebuild, 2026-08-04:
// the bars became percent rows with a live breakdown — better shown on the
// mock itself — and the icon toolbar became four labelled menus.)

// ── The fake screen the tour walks ───────────────────────────────────────────
// A made-up Super Strength / Willpower Brute, built as a damage dealer -- the
// same example character the step text describes. Hand-written from the app's
// REAL markup shapes (powerCardHtml, barRow, the static panels in index.html)
// and painted by the app's real stylesheet, so it looks like the app without
// being the app. Every element a step points at carries data-for="<real id>".
// Numbers are plausible for the pairing but illustrative -- the corner badge
// says so on screen.
//
// Two screens, switched per step: the opening menu (Getting-started chapter)
// and the build screen (everything else).
const TOUR_MOCK_HTML = `
<div class="tour-mock-badge">EXAMPLE — a Brute damage build, drawn for this tour. Nothing here is your character.</div>

<div class="tour-mock-screen tm-center" data-tm-screen="menus">
  <div class="entry-box tm-menu-open" data-tm="entry-menu" data-for="m-character">
    <h2>The Character menu</h2>
    <p class="muted">Everything begins here — the menu bar's first entry.</p>
    <div class="menu-drop tm-menu-list">
      <button type="button" data-for="entry-continue"><b>⏯️ Continue where you left off</b><i>Resume one of your saved characters</i></button>
      <button type="button" data-for="entry-scratch"><b>✨ Start a new character</b><i>Tell me how you want to play and I will pick the build</i></button>
      <button type="button" data-for="entry-respec"><b>♻️ Build a new level 50</b><i>An end-game kit from scratch, no file needed</i></button>
      <button type="button" data-for="import-btn"><b>📋 Import a build</b><i>From Mids Reborn, or a character you play — I will show you how</i></button>
      <button type="button" data-for="save-btn"><b>💾 Save this character</b><i>Plan and progress, so you can resume later</i></button>
      <button type="button" data-for="start-over-btn"><b>↺ Switch character</b><i>Load another one, or start over</i></button>
    </div>
  </div>
</div>

<div class="tour-mock-screen" data-tm-screen="build">
  <header class="tm-head" data-for="masthead">
    <h1>🦸 Hero Companion <span class="muted small">— Bruiser Brawlwell · Brute · level 50</span></h1>
    <nav class="menubar" data-tm="menubar">
      <button class="menu-top" type="button">Character</button>
      <button class="menu-top" type="button" data-tm="menu-build" data-for="m-build">Build</button>
      <button class="menu-top" type="button" data-tm="menu-view" data-for="m-view">View</button>
      <button class="menu-top" type="button" data-tm="menu-help" data-for="m-help">Help</button>
    </nav>
    <!-- (the alignment button moved into the View menu, 2026-08-04) -->
  </header>

  <nav class="tabbar tm-tabbar" data-for="tabbar">
    <button class="tab" data-tm-tabbtn="powers" data-for="tab-btn-powers" type="button">Powers &amp; Slots</button>
    <button class="tab" data-tm-tabbtn="stats" data-for="tab-btn-stats" type="button">Stats</button>
    <button class="tab" data-tm-tabbtn="leveling" data-for="tab-btn-leveling" type="button">Leveling Guide</button>
    <button class="tab" data-tm-tabbtn="logging" data-for="tab-btn-logging" type="button">Logging</button>
  </nav>

  <section class="build-tile tm-tile" data-for="build-tile" data-tm="tile">
    <label>Name <input data-for="char-name" value="Bruiser Brawlwell" disabled></label>
    <label>Archetype <select data-for="sel-archetype" disabled><option>Brute</option></select></label>
    <label>Primary <select data-for="sel-primary" disabled><option>Super Strength</option></select></label>
    <label>Secondary <select disabled><option>Willpower</option></select></label>
    <label data-tm="exemp-dial">Exemplar <select data-for="exemplar-sel" disabled><option>Off — full level</option></select></label>
    <details open onclick="event.preventDefault()"><summary>Power Pools (up to 4)</summary>
      <div data-for="pool-selectors">
        <label>Pool 1 <select disabled><option>Fighting — already chosen</option></select></label>
        <label>Pool 2 <select disabled><option>Leaping — already chosen</option></select></label>
        <label>Pool 3 <select disabled><option>Speed</option></select></label>
      </div>
    </details>
  </section>

  <div class="tm-main">

  <div class="tm-tab" data-tm-tab="powers">
    <!-- the order-to-work-in band, stood in for so the tour can teach the loop
         at its action location (Joel, 2026-08-07: the tour should reinforce the
         workflow "so people know what they are likely to do with results") -->
    <div class="change-spine" data-for="change-spine">
      <b class="cs-lead">Changing this build? Work in this order.</b>
      <span class="cs-step"><span class="cs-n">1</span><span class="cs-t"><b>Say what you want more of</b>
        <span class="cs-why">set the goal in the Build Assistant</span></span></span>
      <span class="cs-step"><span class="cs-n">2</span><span class="cs-t"><b>Press Solve</b>
        <span class="cs-why">one press re-slots every slot toward that goal, and says what moved</span></span></span>
      <span class="cs-step"><span class="cs-n">3</span><span class="cs-t"><b>Tune one piece at a time</b>
        <span class="cs-why">on Stats, click any number to see what each enhancement is worth</span></span></span>
      <span class="cs-step"><span class="cs-n">4</span><span class="cs-t"><b>Change powers last</b>
        <span class="cs-why">only if the goal can't be reached by slotting alone</span></span></span>
    </div>
    <div class="tm-cols">
    <section class="panel" data-for="builder">
      <h2 data-tm="builder-head">Powers &amp; Slots</h2>
      <div class="edit-bar">
        <button class="ghost-btn" type="button">↶ Undo (Ctrl+Z)</button>
        <span class="slot-tally" data-for="slot-tally">67 / 67 slots</span>
      </div>
      <div class="power-card" data-tm="card1">
        <div class="pc-head"><span class="pc-title"><span class="pname">Knockout Blow</span><span class="pc-info-glyph">ⓘ</span></span></div>
        <div class="pc-sub" data-tm="card1-tools">
          <span class="pick-lvl">L6</span>
          <span class="pc-tools">
            <button class="mini lock-btn" type="button">🔓</button>
            <button class="mini" type="button">−</button>
            <button class="mini" type="button">+</button>
            <button class="remove-power" type="button">✕</button>
          </span>
        </div>
        <div class="slot-row">
          <div class="slot filled"><img src="/static/icons/enh/SAO_Brute2.png" alt="Superior Unrelenting Fury"><span class="slot-lvl">50</span></div>
          <div class="slot filled"><img src="/static/icons/enh/SAO_Brute2.png" alt=""><span class="slot-lvl">50</span></div>
          <div class="slot filled"><img src="/static/icons/enh/SAO_Brute2.png" alt=""><span class="slot-lvl">50</span></div>
          <div class="slot filled"><img src="/static/icons/enh/SAO_Brute2.png" alt=""><span class="slot-lvl">50</span></div>
          <div class="slot filled"><img src="/static/icons/enh/SAO_Brute2.png" alt=""><span class="slot-lvl">50</span></div>
          <div class="slot filled unique"><img src="/static/icons/enh/SAO_Brute2.png" alt=""><span class="slot-lvl">50</span></div>
        </div>
        <div class="set-summary" data-tm="card1-sets"><span class="muted small">sets:</span> Superior Unrelenting Fury ×6</div>
      </div>
      <div class="power-card pc-locked" data-tm="card2">
        <div class="pc-head"><span class="pc-title"><span class="pname">High Pain Tolerance</span><span class="pc-info-glyph">ⓘ</span></span></div>
        <div class="pc-sub">
          <span class="pick-lvl">L4</span>
          <span class="pc-tools">
            <button class="mini lock-btn locked" data-tm="card2-lock" type="button">🔒</button>
            <button class="mini" type="button">−</button>
            <button class="mini" type="button">+</button>
            <button class="remove-power" type="button">✕</button>
          </span>
        </div>
        <div class="slot-row">
          <div class="slot filled"><img src="/static/icons/enh/UnbreakableGuard.png" alt="Unbreakable Guard"><span class="slot-lvl">50</span></div>
          <div class="slot filled"><img src="/static/icons/enh/UnbreakableGuard.png" alt=""><span class="slot-lvl">50</span></div>
          <div class="slot filled"><img src="/static/icons/enh/UnbreakableGuard.png" alt=""><span class="slot-lvl">50</span></div>
          <div class="slot filled unique"><img src="/static/icons/enh/sSteadfastProtection.png" alt="Steadfast Protection +Def"><span class="slot-lvl">50</span></div>
        </div>
        <div class="set-summary"><span class="muted small">sets:</span> Unbreakable Guard ×3 · Steadfast Protection</div>
      </div>
      <div class="add-powers-row" data-tm="addrow" data-for="powers-list">
        <label>Add from Super Strength <select disabled><option>+ add power…</option></select></label>
        <label>Add from Willpower <select disabled><option>+ add power…</option></select></label>
        <label>Add from Fighting <select disabled><option>+ add power…</option></select></label>
      </div>
      <!-- the card strip under the powerset rows (2026-08-04): ⌨ commands and the
           set-bonus rules, side by side and full width -->
      <div class="pw-cardband tm-strip">
        <div class="panel" data-for="cmd-card" data-tm="cmd-box">
          <h2>⌨ In-game commands</h2>
          <p class="muted small">Click a command to copy it — then Ctrl+V into the game's chat box.</p>
          <div class="cmd-list">
            <div class="cmd-row"><code>/build_save_file mybuild.txt</code><span>Save your live character to a file</span></div>
            <div class="cmd-row"><code>/respec</code><span>Start a respec in game — follow the plan's order</span></div>
          </div>
        </div>
        <div class="panel" data-for="setbonus-blurb">
          <h2>💠 How set bonuses stack</h2>
          <p class="muted small">Two or more pieces of one set unlock bonuses tier by tier; the
            game counts each identical bonus at most five times.</p>
        </div>
      </div>
      <div class="order-out subpanel" data-for="tray-out">
        <div class="ovc-head">IN-GAME TRAYS</div>
        <p class="muted small">Tray 1 — the chain: Punch · Haymaker · Knockout Blow · Foot Stomp ·
          Rage · Taunt&nbsp;&nbsp;|&nbsp;&nbsp;Tray 2 — toggles &amp; answers: Tough · Weave ·
          Combat Jumping · High Pain Tolerance (auto)</p>
      </div>
      <div class="order-out subpanel" data-for="order-out">
        <div class="ovc-head">RESPEC ORDER</div>
        <p class="muted small">1 · Punch &nbsp; 2 · High Pain Tolerance &nbsp; 3 · Haymaker &nbsp;
          4 · Mind Over Body &nbsp; 5 · Combat Jumping &nbsp; … every pick in the order the
          respec screen will ask for it.</p>
      </div>
      <details class="conv-guide" open onclick="event.preventDefault()"><summary data-tm="conv-summary">💰 Get expensive IOs cheap — enhancement converters</summary>
        <div data-for="conv-tool">
          <div data-tm="conv-body">
            <p class="muted small">You asked: <b>Luck of the Gambler: Defense/+Recharge</b></p>
            <div class="tm-set-row"><b>Cheapest path found</b>
              <span class="muted small">Craft a cheap rare defense recipe at level 50 · run
                enhancement converters within Defense sets until it lands (≈ 4 converters,
                ≈ 275k inf) · total ≈ 1.4M inf — versus ≈ 7M buying it outright.</span></div>
          </div>
        </div>
      </details>
    </section>

    <section class="panel" data-for="assistant">
      <h2>Build Assistant</h2>
      <label>Content <select data-for="preset-content" disabled><option>Task forces &amp; trials</option></select></label>
      <label>Role <select data-for="preset-role" disabled><option>Split role — more than one job</option></select></label>
      <div data-for="role-focus-split" data-tm="split-role">
        <b>Split role: which jobs, and how much of each?</b>
        <div class="muted small">Not a role of its own — you naming the jobs this character
          really does.</div>
        <div class="rf-jobs">
          <div class="rf-job"><select disabled><option>Damage dealer</option></select>
            <input type="number" value="60" disabled><span class="muted small">%</span></div>
          <div class="rf-job"><select disabled><option>Healer</option></select>
            <input type="number" value="25" disabled><span class="muted small">%</span></div>
          <div class="rf-job"><select disabled><option>Buffer / Support</option></select>
            <input type="number" value="15" disabled><span class="muted small">%</span></div>
        </div>
        <div class="muted small">→ 60% Damage dealer / 25% Healer / 15% Buffer / Support  (100% total)</div>
      </div>
      <div data-for="role-output" data-tm="role-output">
        <div class="ro-box">
          <div class="ro-head"><b>What this build delivers today</b>
            <span class="muted small">Your powers, your IOs and whatever you have ticked under
            accolades and incarnates.</span></div>
          <div class="ro-row"><span class="ro-job">Damage dealer <span class="muted small">60%</span></span>
            <span class="ro-val"><b>112.4</b> single-target DPS · <b>41</b> AoE DPS per target</span></div>
          <div class="ro-row"><span class="ro-job">Healer <span class="muted small">25%</span></span>
            <span class="ro-val"><b>933 HP</b> Heal</span></div>
          <div class="ro-foot muted small" data-tm="unslotter">To change one enhancement, the game
            sells <b>Enhancement Unslotter</b> salvage: one is consumed per enhancement, and you use
            it by dragging the slotted enhancement into an empty slot in your enhancement tray. To
            change everything at once, a <code>/respec</code> rebuilds every pick and slot.</div>
        </div>
      </div>
      <div class="custom-targets-row">
        <button class="mini" data-for="custom-targets-btn" type="button">Customize build targets…</button>
      </div>
      <label class="preserve-toggle" data-tm="preserve-label"><input type="checkbox" data-for="preserve-toggle" checked disabled>
        <span>Preserve my IO sets — 🔒 locks every power I hand-slotted; unlock exceptions on their cards</span></label>
      <button class="solve-btn" data-for="solve-btn" type="button">🧮 Solve optimal slotting for goal (instant)</button>
      <button data-for="gen-btn" type="button">Generate 3 builds</button>
      <button class="changes-btn" data-for="changes-btn" type="button">📋 What changed? (open / close anytime)</button>
      <button class="reset-btn" data-for="reset-btn" type="button">↺ Reset to imported build (try again)</button>
      <div class="tm-response" data-tm="response" data-for="ai-response">
        <b>Solved for: Task forces · Damage dealer.</b>
        Smashing/Lethal resistance reached 90% — your cap. Melee defense reached
        41.3% of the 45% asked; an unpicked power on this character would close
        the gap: Weave (about +5%).
      </div>
      <div class="validation" data-for="validation">✓ Legal build — nothing here breaks the game's rules.</div>
    </section>
    <!-- the inherent moved to Stats as the Archetype bonus group (2026-08-05) -->
    </div>
  </div>

  <div class="tm-tab" data-tm-tab="stats" style="display:none">
    <div class="tm-miniwall" data-for="stats-miniwall" data-tm="mini-wall">
      <div class="mw-frame-label">🗂 Powers &amp; Slots, in miniature <span class="muted small">— click a stat below and everything feeding it turns green here: a ring on an enhancement, a box on a power's name when the power grants it by itself</span></div>
      <div class="mw-grid">
        <div class="mw-card"><div class="mw-head"><span class="mw-name">Knockout Blow</span><span class="mw-lv">L6</span></div>
          <div class="mw-slots"><span class="mw-slot"><img class="mw-ico" src="/static/icons/enh/SAO_Brute2.png" alt=""></span><span class="mw-slot"><img class="mw-ico" src="/static/icons/enh/SAO_Brute2.png" alt=""></span></div></div>
        <div class="mw-card stat-hot-power"><div class="mw-head"><span class="mw-name">Weave</span><span class="mw-lv">L30</span></div>
          <div class="mw-slots"><span class="mw-slot stat-hot"><img class="mw-ico" src="/static/icons/enh/UnbreakableGuard.png" alt=""></span><span class="mw-slot stat-hot"><img class="mw-ico" src="/static/icons/enh/UnbreakableGuard.png" alt=""></span></div></div>
        <div class="mw-card"><div class="mw-head"><span class="mw-name">Tough</span><span class="mw-lv">L28</span></div>
          <div class="mw-slots"><span class="mw-slot"><img class="mw-ico" src="/static/icons/enh/sSteadfastProtection.png" alt=""></span></div></div>
      </div>
      <div class="mw-inh-strip muted small">Inherents, nothing slotted: Brawl · Sprint · Rest · Swift · Hurdle</div>
    </div>
    <section class="panel" data-for="stats">
      <h2 data-tm="stats-head">Stats <span class="muted small">(toggles/autos + enhancements + set bonuses)</span></h2>
      <div class="stats-ctlrow" data-tm="ctl-row">
        <span class="chip cap-def">Defense soft cap 45%</span>
        <span class="chip cap-res" data-for="res-cap-chip">Resistance hard cap 90%</span>
        <label class="incarnate-toggle"><input type="checkbox" data-for="incarnate-peak-toggle" disabled> Include incarnates (peak)</label>
        <label class="incarnate-toggle" data-tm="sup-label"><input type="checkbox" data-for="suppression-toggle" disabled> In-combat view (suppression)</label>
        <label class="incarnate-toggle" data-tm="exemp-dial-stats">View exemplared at <select data-for="exemplar-sel-stats" disabled><option>Off — full level</option></select></label>
      </div>
      <div class="tm-statcols">
        <div>
          <div data-for="at-bonus-group">
            <h3>Archetype bonus <span class="muted small">what you get for free</span></h3>
            <div class="bars">
              <div class="o-row at-bonus-row"><span class="o-name">Fury</span>
                <span class="o-desc">builds as you fight and get hit</span>
                <span class="statval im-dormant">shown only</span></div>
            </div>
          </div>
          <h3>Defense <span class="muted small">soft cap 45%</span></h3>
          <div class="bars">
            <div class="o-row stat-selected" data-tm="sel-row"><span>Melee</span><span>41.3%</span></div>
            <div class="o-row"><span>Ranged</span><span>36.2% <span class="over">⚔ 31.9%</span></span></div>
            <div class="o-row"><span>AoE</span><span>30.1%</span></div>
          </div>
          <h3 data-tm="res-head">Resistance <span class="muted small">hard cap 90%</span></h3>
          <div class="bars">
            <div class="o-row"><span>Smashing</span><span>90%</span></div>
            <div class="o-row"><span>Energy</span><span>46.2%</span></div>
          </div>
          <div class="offense" data-tm="atk-table" data-for="offense-stats">
            <div class="o-row"><span><b>Top attack</b> (damage / animation)</span><span>121.4</span></div>
            <div class="o-row"><span>Knockout Blow</span><span class="muted small">243 dmg · 2.0s · 25s rech · 121.4 DPA</span></div>
            <div class="o-row"><span>Foot Stomp <span class="aoe-tag">AoE</span></span><span class="muted small">86 dmg · 2.1s · 20s rech · 41.0 DPA</span></div>
          </div>
          <p class="muted small" data-tm="support-note">A support set, controller or Mastermind grows
            this panel: per-pet damage, enemy debuffs (base, per application), and what your buffs
            hand allies.</p>
        </div>
        <div class="tm-breakdown" data-for="stat-breakdown" data-tm="breakdown-box">
          <h2><span>Defense: Melee</span></h2>
          <p class="sb-sub">Where the <b class="sb-green">+41.3%</b> comes from. The contributing IOs
            ring <b class="sb-green">green</b> — here and in the wall above.</p>
          <p class="sb-editnote">✏️ <b>Editable:</b> click any IO chit below to change it —
            the change is REAL and updates your build and every number, everywhere.</p>
          <div class="sbp-card stat-hot-power"><div class="sbp-head"><span class="sbp-name">Weave</span>
            <span class="sbp-val">+7.19%</span></div>
            <div class="sbp-src muted small">+7.19% — the power grants this by itself
              <span class="sb-selfnote">(green name box = built in, not from an IO)</span></div></div>
          <div class="sbp-card"><div class="sbp-head"><span class="sbp-name">Knockout Blow</span>
            <span class="sbp-val">+3.75%</span></div>
            <div class="sbp-src muted small">+3.75% — 6 pieces of Superior Unrelenting Fury</div></div>
        </div>
      </div>
    </section>
  </div>

  <!-- The End Game TAB is retired (2026-08-04): these surfaces live on
       Powers & Slots, so this mock block carries the powers tag and stacks
       under the wall mock — exactly like the real layout. -->
  <div class="tm-tab" data-tm-tab="powers" style="display:none">
    <section class="panel">
      <!-- ⚠ heading is NOT "End Game": that tab no longer exists, and a mock that
           names a retired tab teaches a layout the user cannot find -->
      <h2>Accolades</h2>
      <div class="accolades-card" data-for="accolades-card" data-tm="acc-box">
        <div class="ovc-head">ACCOLADES <span class="acc-count">2/28</span></div>
        <div class="muted small">☑ Freedom Phalanx Reserve <b>+10% HP</b></div>
        <div class="muted small">☑ Task Force Commander <b>+5% HP</b></div>
        <div class="muted small">☐ Portal Jockey <b>+5% HP · +5 End</b> ⓘ</div>
        <div class="muted small" style="opacity:.45">☐ Born In Battle — villain-side only</div>
        <div class="muted small">👁 Preview all — your numbers with every accolade in hand</div>
      </div>
      <div class="endgame-block" data-tm="epic-row">
        <div class="endgame-label">Epic / Ancillary Pool <span class="muted small">— survival / utility; unlocks at level 35</span></div>
        <select data-for="sel-epic" disabled><option>Energy Mastery</option></select>
      </div>
      <div class="endgame-block" data-tm="inc-row">
        <div class="endgame-label">Incarnates <span class="muted small">— unlock at level 50</span></div>
        <div class="incarnates" data-for="incarnate-selectors">
          <label class="muted small">Alpha
            <select disabled><option>Musculature Core Paragon</option></select>
            <div class="inc-detail"><span>Increases Damage</span><b class="inc-fx">+45% damage</b></div>
          </label>
          <label class="muted small">Destiny
            <select disabled><option>Ageless Radial Epiphany</option></select>
            <div class="inc-detail"><span>Wide PBAoE Ally +End, +Recharge Rate</span><b class="inc-fx">+100% max end · +40% recharge</b></div>
          </label>
        </div>
      </div>
    </section>
  </div>

  <div class="tm-tab" data-tm-tab="leveling" style="display:none">
    <section class="panel" data-for="journey-body">
      <h2>🗺️ Leveling Guide</h2>
      <!-- the side preview sits DIRECTLY under the title in the real app
           (2026-08-05) — the mock explains things at their action location -->
      <p class="muted small" data-tm="align-preview">Preview another side:
        Hero · Vigilante · Rogue · Villain · 🌀 Flashback
        <i>(your character is unchanged)</i></p>
      <div class="tm-road" data-tm="road">
        <span class="tm-stop">1</span><span class="tm-stop">8</span><span class="tm-stop">15</span>
        <span class="tm-stop here">★22</span><span class="tm-stop">30</span><span class="tm-stop">38</span>
        <span class="tm-stop">44</span><span class="tm-stop">50</span>
      </div>
      <div class="tm-lvlpanel" data-tm="lvl-panel">
        <div class="tm-art" data-tm="art-box"><div class="tm-art-name">TALOS ISLAND</div>
          <div class="muted small">the zone this level sends you to — the picture follows your click</div></div>
        <div class="tm-lvlinfo">
          <b>Level 22 — your next stop</b>
          <p class="muted small">Pick: Knockout Blow · a new enhancement slot arrives at 23 ·
            zones that fit: Talos Island (20–27), Independence Port (20–30) — enemies there run even
            with you · Citadel's Task Force opens at 25.</p>
        </div>
      </div>
    </section>
  </div>

  <div class="tm-tab" data-tm-tab="logging" style="display:none">
    <div class="entry-share" data-for="share-line" data-tm="share-row">
      🛰 <b>Feed the live Pulse Boards from your game log?</b>
      <span class="muted small">Off until you say yes; nothing has been sent. Your rewards and public
        recruitment lines, never raw chat and never tells.</span>
      <span class="muted small"><u>Yes, share my play data</u> · <u>No thanks</u></span>
    </div>
    <section class="panel" data-for="gamelog">
      <h2 data-tm="gamelog-head">📜 Play Log <span class="muted small">— insights from your game sessions</span></h2>
      <div class="gl-cards" data-tm="gl-body">
        <div class="tm-set-row"><b>Last session · 2h 10m · Bruiser Brawlwell</b>
          <span class="muted small">Levelled 22 → 24 · haul: 2 rare recipes, 41 salvage —
            appraised: keep 2, craft 1, sell the rest</span></div>
        <div class="tm-set-row"><b>This week</b>
          <span class="muted small">3 characters played · busiest evening: Thursday</span></div>
      </div>
      <div class="gl-pulse" data-for="gl-pulse" data-tm="boards-row">
        <button class="ghost-btn" type="button">🗞 My private board</button>
        <button class="ghost-btn" type="button">👁 What sharing shows</button>
      </div>
    </section>
  </div>

  </div>

  <aside class="panel pinfo tm-info" data-for="power-info" data-tm-overlay="info" style="display:none">
    <h2>Knockout Blow</h2>
    <div class="pi-tags"><span class="pi-tag">Click</span><span class="pi-tag">Melee</span><span class="pi-tag">Single target</span></div>
    <table>
      <tr><td>Damage</td><td>Superior (smashing)</td></tr>
      <tr><td>Endurance cost</td><td>≈19</td></tr>
      <tr><td>Recharge</td><td>25 s</td></tr>
      <tr><td>Accepts</td><td>Melee Damage sets</td></tr>
    </table>
    <p class="pi-note">Slotted: Superior Unrelenting Fury ×6 — the full set, with its
      +regeneration proc and the set's build-wide bonuses.</p>
    <p class="pi-trade" data-tm="trade-note">From this build's Foot Stomp ⓘ: “Why procs here:
      4 procs add ≈118 damage every use. The Obliteration pieces they replaced would have
      added ≈36 damage from enhancement instead — this build wanted the procs, and collects
      set bonuses in other powers.”</p>
  </aside>

  <div class="modal tm-modal" data-for="modal" data-tm-overlay="picker" style="display:none">
    <div class="modal-box" data-tm="modal-box">
      <div class="modal-head"><strong>Knockout Blow — choose an enhancement</strong><button type="button">✕</button></div>
      <p class="muted small">Only sets this power can actually take are offered — it accepts Melee Damage sets.</p>
      <input placeholder="Filter sets…" disabled>
      <div class="modal-sets">
        <div class="tm-set-row"><b>Superior Unrelenting Fury</b> <span class="muted small">Brute ATO · 6 pieces · +regeneration proc, strong build-wide bonuses</span></div>
        <div class="tm-set-row"><b>Hecatomb</b> <span class="muted small">Very rare · 6 pieces · big recharge and damage bonuses</span></div>
        <div class="tm-set-row"><b>Kinetic Combat</b> <span class="muted small">4 pieces · prized for smashing/lethal defense</span></div>
        <div class="tm-set-row" data-tm="ho-row"><b>Hamidon Origin: Nucleolus</b> <span class="muted small">special · accuracy AND damage in one slot · from Hamidon raids or merits · no set bonuses</span></div>
      </div>
    </div>
  </div>

  <div class="modal tm-modal" data-tm-overlay="targets" style="display:none">
    <div class="modal-box" data-tm="targets-box">
      <div class="modal-head"><strong>Customize build targets</strong><button type="button">✕</button></div>
      <p class="muted small">Anything you set here outranks the preset — it is what the optimizer chases first.</p>
      <div class="tm-set-row"><b>Melee defense — 45%</b> <span class="muted small">your ask · reached 41.3% so far</span></div>
      <div class="tm-set-row"><b>Smashing/Lethal resistance — 90%</b> <span class="muted small">your ask · reached, at your cap ✓</span></div>
      <div class="tm-set-row"><b>Ranged defense — 45%</b> <span class="muted small">best reachable on this character ≈ 36.2 — the unpicked
        Weave would add about +5. Take it, lower the ask, or leave it: your call either way.</span></div>
      <p class="muted small">💾 Save these as a named preset to reuse on other characters.</p>
    </div>
  </div>

  <div class="modal tm-modal" data-tm-overlay="changes" style="display:none">
    <div class="modal-box" data-tm="changes-box">
      <div class="modal-head"><strong>📋 What the solve changed</strong><button type="button">✕</button></div>
      <div class="tm-set-row"><b>Knockout Blow</b> <span class="muted small">Crushing Impact ×5 → Superior Unrelenting Fury ×6 (one slot added)</span></div>
      <div class="tm-set-row"><b>Tough</b> <span class="muted small">generic resistance IO → Steadfast Protection: Resistance/+Def 3%</span></div>
      <div class="tm-set-row"><b>What it bought</b> <span class="muted small">+4.2% melee defense · +10% recharge · same endurance</span></div>
      <p class="muted small">⬇ Export as .mbd &nbsp;·&nbsp; Keep it &nbsp;·&nbsp; ↺ Reset to imported</p>
    </div>
  </div>

  <div class="modal tm-modal" data-for="bug-btn" data-tm-overlay="bugreport" style="display:none">
    <div class="modal-box" data-tm="bug-box">
      <div class="modal-head"><strong>🐞 Report a bug</strong><button type="button">✕</button></div>
      <p class="muted small">App version · model · game-data numbers — filled in for you.</p>
      <input placeholder="What happened?" disabled>
      <label class="incarnate-toggle"><input type="checkbox" checked disabled> Attach this build (.mbd) so it can be reproduced</label>
      <p class="muted small">Nothing leaves your machine until you press Send.</p>
    </div>
  </div>
</div>`;

let _mockEl = null;

function _openTourMock() {
  if (_mockEl) return _mockEl;
  _mockEl = document.createElement("div");
  _mockEl.id = "tour-mock";
  _mockEl.innerHTML = TOUR_MOCK_HTML;
  document.body.appendChild(_mockEl);
  return _mockEl;
}

function _closeTourMock() {
  if (_mockEl) _mockEl.remove();
  _mockEl = null;
}

// Show the mock SCENE a step belongs to. Scenes exist so the tour can show
// what a choice actually DOES, in the place it actually happens (Joel,
// 2026-07-27 third ruling: go to the action's location, and show the
// consequence -- not everything squeezed onto one pane):
//   entry  - the fake opening menu (Getting-started chapter)
//   build  - the fake builder, laid out exactly like the real app's grid
//   info   - build + the power-details column open, as after clicking ⓘ
//   picker - build + the enhancement-set chooser open, as after clicking a slot
// Which mock TAB a chapter's steps show — the tabbed rebuild's one addition
// (2026-08-04): the mock reproduces the five-tab shell, and each step lights
// the tab its subject lives on, tab strip state included.
const TM_TAB = { build: "powers", powers: "powers", solve: "powers", header: "powers",
                 stats: "stats", endgame: "powers", leveling: "leveling", logging: "logging" };

function _mockShowScene(scene, tab) {
  if (!_mockEl) return;
  const menus = scene === "menus";
  _mockEl.querySelectorAll(".tour-mock-screen").forEach(sc => {
    sc.style.display = (sc.dataset.tmScreen === (menus ? "menus" : "build")) ? "" : "none";
  });
  // exactly one mock tab panel shows, and the strip's button reads selected
  _mockEl.querySelectorAll(".tm-tab").forEach(p => {
    p.style.display = (p.dataset.tmTab === (tab || "powers")) ? "" : "none";
  });
  // the REAL tile shows only on Powers & Slots — the mock must not teach
  // a layout the app does not have (rule 3). Class, not inline style: the
  // mock tile carries a display:flex !important override (to beat the real
  // body:not(.tab-powers) hide), which an inline style cannot outrank.
  const tile = _mockEl.querySelector(".tm-tile");
  if (tile) tile.classList.toggle("tm-tile-off", (tab || "powers") !== "powers");
  _mockEl.querySelectorAll("[data-tm-tabbtn]").forEach(b => {
    b.setAttribute("aria-selected", b.dataset.tmTabbtn === (tab || "powers") ? "true" : "false");
  });
  const grid = _mockEl.querySelector(".tm-main");
  if (grid) grid.classList.toggle("tm-has-info", scene === "info");
  // Exactly one overlay (the ⓘ column, a chooser, the report form...) is up
  // at a time: the one whose data-tm-overlay names this scene.
  _mockEl.querySelectorAll("[data-tm-overlay]").forEach(ov => {
    ov.style.display = (ov.dataset.tmOverlay === scene) ? "" : "none";
  });
}

const TOUR_CHAPTERS = {
  start:     "Getting started",
  build:     "Your character's identity",
  powers:    "Powers and slots",
  solve:     "Letting it build for you",
  stats:     "Where your numbers come from",
  endgame:   "The end game",
  leveling:  "The Leveling Guide",
  logging:   "Your play log",
  header:    "Menus, saving and help",
};

// One line per section for the chooser. Deliberately a separate map from
// TOUR_CHAPTERS: the audit parses that block to know which chapters exist, and
// turning it into objects would break the thing that keeps this honest.
const TOUR_CHAPTER_BLURB = {
  start:    "The Character menu — every way to start — and the four tabs.",
  build:    "Name, archetype, powersets and pools on the build bar; goal and role in the Assistant.",
  powers:   "Taking powers, spending your 67 slots, and locking what you have already decided.",
  solve:    "Letting it work out the slotting, and how to read what it gives you back.",
  stats:    "Click any stat and see exactly which powers and IOs make it — and change them there.",
  endgame:  "Accolades, your epic pool at 35, and the incarnates at 50 — all on Powers & Slots.",
  leveling: "Your 1-to-50 as a road: every level's pick, zones and task forces.",
  logging:  "What your game sessions earned you, read from your own chat log.",
  header:   "The four menus, alignment, updates, and reporting something wrong.",
};

// `target`  - the element this step explains (id selector).
// `spine`   - true = part of the short first-run tour.
const TOUR_STEPS = [
  // ── Getting started ────────────────────────────────────────────────────────
  { chapter: "start", target: "#m-character", spine: true, anchor: "[data-tm=entry-menu]",
    title: "Everything starts in the Character menu",
    body: "The first entry on the menu bar holds every way in: two build a "
        + "character from nothing, two read one you already have, and one "
        + "resumes earlier work.\n\n"
        + "A rule of thumb: new to the game, take Start a new character. Know "
        + "exactly what you want at 50, take Build a new level 50. Already "
        + "playing the character, import it instead — a plan is worth more when "
        + "it is built around what you really own." },
  { chapter: "start", target: "#entry-continue",
    title: "Continue where you left off",
    body: "Levelling a character is weeks of real play, so the app keeps the "
        + "whole plan on your machine: powers, slotting, levelling progress, "
        + "locks and targets. This lists every character you have saved and "
        + "reopens one exactly where you stopped — and on launch, the app "
        + "reopens your last character by itself.\n\n"
        + "You rarely need to save by hand: it saves quietly in the background "
        + "as you work." },
  { chapter: "start", target: "#entry-scratch",
    title: "Start a new character",
    body: "For a character that does not exist yet. If you are not sure what to "
        + "roll, this is the one: you answer a few questions about how you like "
        + "to play and it suggests archetypes that fit, with reasons.\n\n"
        + "From there it walks the whole road on the game's real schedule — a "
        + "power on even levels, slots on odd ones, pools from level 4, epics "
        + "at 35 — so at every level you know what to pick and where to put it." },
  { chapter: "start", target: "#entry-respec",
    title: "Build a new level 50",
    body: "You already know what you want to play and you want the finished "
        + "article: every power, every slot, epic pool and incarnates, ready to "
        + "respec into.\n\n"
        + "Tell it the archetype and your two powersets and it does the rest, "
        + "aimed at your Content and Role — both explained later in this tour. "
        + "Anything it produces, you can still adjust by hand." },
  { chapter: "start", target: "#import-btn",
    title: "Import a build",
    body: "One door, two kinds of file, and it shows you how to get either.\n\n"
        + "From Mids Reborn: Mids saves builds as a .mbd, and you pick yours.\n\n"
        + "From a character you actually play: type /build_save_file in the "
        + "game's chat box and Homecoming writes a small text file. The app "
        + "finds those saves by itself, so you just pick the character from a "
        + "list; there is a Browse button too, if your game lives somewhere "
        + "unusual. That is the most honest starting point there is, because "
        + "the plan is built around exactly the powers and enhancements you "
        + "really have.\n\n"
        + "Either way it reads the build and tells you what it thinks of it "
        + "first — what is strong, what is loose — before changing anything. "
        + "From there it can improve the slotting while keeping the sets you "
        + "have already paid for, and write the result back out as a .mbd that "
        + "Mids can open. Your file is never touched." },
  { chapter: "start", target: "#save-btn",
    title: "Saving and switching",
    body: "The same menu holds Save this character and Switch character. Saving "
        + "keeps the plan and progress on your machine; switching loads another "
        + "one.\n\n"
        + "Nothing is lost on the way out: the character you are leaving has "
        + "been saved in the background as you worked, and closing the app "
        + "offers to save anything unsaved." },
  // ⚠ Same `scene: "build"` fix as the workflow step below, and the same cause:
  // the tab strip's mock stand-in lives on the BUILD screen, while the start
  // chapter defaults to the menus screen. Found 2026-08-07 by measuring the
  // highlighted element on every step — this one was 0x0 and invisible, so a
  // step titled "Four tabs, one character" was pointing at a tab strip that was
  // not on screen. ⚠ VISUAL CONFIRMATION STILL OWED (see RESUME-HERE).
  { chapter: "start", target: "#tabbar", spine: true, scene: "build",
    title: "Four tabs, one character",
    body: "The whole app is four tabs across the top. Powers & Slots is the "
        + "build itself — and everything that belongs to it, including your "
        + "accolades, your epic pool at 35 and the incarnates at 50. Stats "
        + "shows every number and where it comes from. The Leveling Guide is "
        + "your 1-to-50 as a road, and Logging reads what your real game "
        + "sessions earned.\n\n"
        + "Everything on every tab describes the same character — change "
        + "something on one and the others update." },

  // ⚠ THE WORKFLOW STEP (Joel, 2026-08-07: "the Tour might help reinforce the
  // workflow, so people know what they are likely to do with results, and what
  // sections of the tool accommodate those well"). The band on the tab says the
  // ORDER; this says what each step gives you back and which surface holds it,
  // which is the half a signpost has no room for.
  // ⚠ scene: "build" IS REQUIRED HERE, and leaving it off is a silent defect.
  // __tmScene defaults to "menus" for the WHOLE start chapter, and a step that
  // omits scene never flips it back — so this card highlighted a collapsed,
  // zero-size stub while the mock still showed the Character menu. Caught by
  // running the tour and looking; no audit sees it, because the target id is
  // real and the mock stand-in exists — they just were not on screen together.
  { chapter: "start", target: "#change-spine", spine: true, key: "workflow",
    scene: "build",
    title: "The order to work in",
    body: "Once a character exists, changing it has a shape, and the band at "
        + "the top of Powers & Slots states it: say what you want, press "
        + "Solve, then tune.\n\n"
        + "It matters because each step hands you something different. Solve "
        + "returns a before-and-after naming every number that moved — that is "
        + "the answer to \"did this help?\". Stats answers \"why?\": click any "
        + "number and it breaks down to the exact powers and enhancements "
        + "making it, and you can pull one out to see what it was worth.\n\n"
        + "So the assistant does the whole build in one move and Stats is where "
        + "you change one piece at a time. Changing which POWERS you took comes "
        + "last, because slotting usually gets there first." },

  // ── Your character's identity ──────────────────────────────────────────────
  { chapter: "build", target: "#build-tile", spine: true, anchor: "[data-tm=tile]", side: "bottom",
    title: "The build bar",
    body: "Your character's identity lives on this bar, on the Powers & Slots "
        + "tab: name, archetype, primary and secondary powersets, pools, and "
        + "the exemplar dial. Change anything and every number in the app "
        + "updates to match.\n\n"
        + "The examples in this tour follow a Brute built as a damage dealer, "
        + "so the details stay consistent as you read." },
  { chapter: "build", target: "#sel-archetype", side: "bottom",
    title: "Archetype first",
    body: "Everything else follows from this one choice. The archetype decides "
        + "which powersets exist for you, the resistance cap your numbers are "
        + "measured against, which roles make sense, and how strongly your "
        + "powers land at all.\n\n"
        + "Our example Brute is melee damage with a 90% resistance cap — pick a "
        + "Defender instead and the whole app reshapes around buffs and debuffs." },
  { chapter: "build", target: "#sel-primary", side: "bottom",
    title: "Primary and secondary",
    body: "The primary set is your archetype's main job and the secondary is "
        + "its supporting half. On the Brute that means attacks first and "
        + "armour second; a Defender is the reverse.\n\n"
        + "Both lists are already filtered to your archetype, so everything "
        + "offered is a choice the game will allow — including the special "
        + "cases, like Kheldian form powers living inside their own sets." },
  { chapter: "build", target: "#pool-selectors", side: "bottom",
    title: "Power pools",
    body: "Pools add what your sets lack: travel, extra toughness like Tough "
        + "and Weave, utility. The game allows four at most, opening from "
        + "level 4, and only one of the origin pools — which is why a pool you "
        + "cannot take is greyed out with the reason on it, never hidden.\n\n"
        + "You do not have to fill these by hand: the Assistant's Generate "
        + "picks pools too, following exactly the rules the game enforces." },
  { chapter: "build", target: "#exemplar-sel", anchor: "[data-tm=exemp-dial]", side: "bottom",
    title: "The exemplar dial",
    body: "Set a level here and the whole app shows your build as it plays "
        + "exemplared down to that level: powers the game switches off leave "
        + "every number, set bonuses above the piece's level go quiet, and a "
        + "bold banner says exactly what view you are in.\n\n"
        + "It is a view only — nothing about the build changes, and turning it "
        + "off puts every number back. The same dial lives on the Stats tab "
        + "and in the View menu." },
  { chapter: "build", target: "#preset-content", side: "left",
    title: "Content: where you play",
    body: "General play, task forces, incarnate trials, farming, PvP — set in "
        + "the Build Assistant beside the powers. This decides what the build "
        + "has to survive and what it needs to deliver: an incarnate trial hits "
        + "far harder than street sweeping.\n\n"
        + "It is not cosmetic: Content changes the targets the optimizer "
        + "chases, so the same character solved for different content comes "
        + "out slotted differently." },
  { chapter: "build", target: "#preset-role", side: "left",
    title: "Role: what you are there to do",
    body: "Damage, tanking, support, control, healing. The optimizer maximises "
        + "your role's output rather than a generic score.\n\n"
        + "That matters most for support and control: a Defender is judged on "
        + "how much its buffs and debuffs actually change a fight — their size "
        + "times how often they are up — not on how well it survives alone.\n\n"
        + "The list is grouped for your archetype: what is natural, what your "
        + "powersets also support, and what is off-role. Nothing is removed. "
        + "Off-role is allowed and always was, it just says so first." },
  { chapter: "build", target: "#role-focus-split", anchor: "[data-tm=split-role]", side: "left",
    key: "split-role",
    title: "Split role: when one job is not the truth",
    body: "Some characters genuinely do two or three things. A triform Kheldian "
        + "is the clearest case — human, Nova and Dwarf are three jobs and all "
        + "three can be worth playing — and it is just as true of a Defender who "
        + "farms fire while still healing.\n\n"
        + "Pick Split role and you name the jobs yourself, one row each, adding "
        + "as many as you actually play. Every job is offered, grouped the same "
        + "way, so an off-role one is a choice you can make rather than an "
        + "option that was hidden from you.\n\n"
        + "The shares always total 100. Type 80 into one and the others give way "
        + "to make room, so the number you type is the number the optimizer "
        + "uses. There is no quiet rescaling behind your back." },
  { chapter: "build", target: "#role-output", anchor: "[data-tm=role-output]", side: "left",
    key: "role-output",
    title: "What the build actually delivers",
    body: "Percentages are a wish. This is the answer: real numbers for each job "
        + "you named, from your powers, your IOs, and whatever you have ticked "
        + "under accolades and incarnates.\n\n"
        + "So a Defender who wants to farm can see the damage they really do "
        + "sitting next to the healing they really do, and judge for themselves "
        + "whether the character does the job.\n\n"
        + "One thing it will not pretend: moving the percentages does not change "
        + "these numbers. Your slots have not moved yet. The sliders change what "
        + "the next solve AIMS for, and the numbers here change when you run it. "
        + "Where a figure cannot be measured honestly, such as control output, it "
        + "says so instead of showing you something invented." },
  { chapter: "build", target: "#role-output", anchor: "[data-tm=unslotter]", side: "left",
    key: "unslotter", slim: true,
    title: "None of it has to be right first time",
    body: "Nothing you decide here is expensive to undo, and that is worth knowing "
        + "before you agonise over a slot.\n\n"
        + "To change ONE enhancement, the game sells Enhancement Unslotter "
        + "salvage. One is consumed per enhancement, and you use it by dragging "
        + "the slotted enhancement into an empty slot in your enhancement tray.\n\n"
        + "To change EVERYTHING, /respec rebuilds every pick and every slot from "
        + "scratch. Plan boldly: the game lets you take it back." },
  { chapter: "build", target: "#custom-targets-btn", scene: "targets", anchor: "[data-tm=targets-box]", side: "right", slim: true,
    title: "Your own targets",
    body: "This is what Customize build targets opens. Each row is an ask — "
        + "defence by type or position, resistance, recharge and more — and "
        + "anything you set outranks the preset: it is what the optimizer "
        + "chases first.\n\n"
        + "The Ranged row shows the honest answer to an ask that cannot be "
        + "reached: how close it can get, and which unpicked power would close "
        + "the gap. Your ask is honored either way — the tool states what a "
        + "goal costs rather than quietly overriding it." },

  // ── Powers and slots ───────────────────────────────────────────────────────
  { chapter: "powers", target: "#builder", spine: true, anchor: "[data-tm=builder-head]", side: "right",
    title: "Powers and slots",
    body: "This is where a build is actually built. Every power you have taken "
        + "gets a card, and the card shows the enhancement slots in it — laid "
        + "out the way the in-game respec screen offers them.\n\n"
        + "Your own character will show its own powers; everything works the "
        + "same way." },
  { chapter: "powers", target: "#powers-list", anchor: "[data-tm=addrow]", side: "right",
    title: "Adding a power",
    body: "Below the cards, every powerset you own has its own Add from… menu. "
        + "Pick a power and its card appears above, ready to slot.\n\n"
        + "Only legal picks are ever offered — right tier, right level, real "
        + "prerequisites — and anything the rules forbid is greyed out with "
        + "the reason on it, so the rule teaches itself. Dropped something by "
        + "accident? Undo, at the top of the panel." },
  { chapter: "powers", target: "#builder", diagram: "powerCard", key: "power-card", anchor: "[data-tm=card1]", side: "bottom", top: 0.08,
    title: "What is on a power card",
    body: "The drawing labels everything on a card: the power's name with the ⓘ "
        + "that opens its full details, the level you take it at, the padlock, "
        + "the − and + that move slots out and in, the ✕ that drops the power, "
        + "and the enhancement slots along the bottom." },
  { chapter: "powers", target: "#slot-tally",
    title: "The 67 slots, and why they are the whole game",
    body: "The game gives you 67 placeable slots across a career, plus one free "
        + "base slot in each power you take. This counter shows what you have "
        + "spent.\n\n"
        + "That budget is what makes build planning interesting. Six slots in "
        + "one attack are six not spread across three others, and at 67 of 67 "
        + "the only way to improve anything is to take a slot from somewhere "
        + "else." },
  { chapter: "powers", target: "#power-info", scene: "info", side: "left",
    title: "What the ⓘ opens",
    body: "Click a power's name or its ⓘ and this panel opens beside the build. "
        + "It shows what the power does, its endurance cost and recharge, the "
        + "enhancement categories it accepts, and what is slotted in it right "
        + "now.\n\n"
        + "It is also where enhancement details live: click a slotted piece and "
        + "you get the piece, its set, and the set's bonuses — the same numbers "
        + "the game uses." },
  { chapter: "powers", target: "#power-info", scene: "info", side: "left", key: "proc-why",
    anchor: "[data-tm=trade-note]", slim: true,
    title: "Why these enhancements",
    body: "When the optimizer chooses damage procs over a full set — or seats a "
        + "-resistance or Force Feedback proc — this panel says why, in one "
        + "sentence with both numbers: what the procs add every use, and what "
        + "the replaced pieces would have added instead.\n\n"
        + "Prefer the set after reading the trade? Slot it back and lock the "
        + "power — a re-solve honors the lock exactly." },
  { chapter: "powers", target: "#modal", scene: "picker", anchor: "[data-tm=modal-box]", side: "right", slim: true,
    title: "Filling a slot, and why the list is short",
    body: "Click a slot and this chooser opens, offering the sets that power "
        + "can actually take, not every set in the game. An armour toggle "
        + "offers defence and resistance sets, an attack offers damage sets, "
        + "because each power declares which categories it accepts.\n\n"
        + "Right-click a slot to empty it. Minus and plus on the card move "
        + "slots between powers, so a slot sitting in something over-invested "
        + "can go where it earns more." },
  { chapter: "powers", target: "#modal", scene: "picker", key: "ho-why",
    anchor: "[data-tm=ho-row]", side: "right", slim: true,
    title: "Hamidon Origins: two aspects in one slot",
    body: "A Hamidon Origin carries two or three aspects at once — accuracy AND "
        + "damage, resistance AND endurance — in a single slot. More raw "
        + "enhancement per slot than any set piece.\n\n"
        + "The price is that an HO earns no set bonuses, and they come from "
        + "endgame play: Hamidon raids, or merit conversion. That is why the "
        + "optimizer only proposes them for endgame content, and why every HO "
        + "it places carries a note saying where it comes from. Slot them by "
        + "hand anywhere you like." },
  { chapter: "powers", target: "#builder", anchor: "[data-tm=card1-sets]", side: "bottom",
    title: "Set bonuses: why six of one set beats six good pieces",
    body: "Slotting several pieces of the SAME set earns set bonuses — "
        + "recharge, defence, health — on top of what each piece does. That is "
        + "why a card reads something like \"Superior Unrelenting Fury x6\" "
        + "with a Full set tag.\n\n"
        + "You will also see Partial set, Frankenslot (pieces from different "
        + "sets picked purely for raw numbers), and Global mules: a power taken "
        + "mainly to carry one always-on unique." },
  { chapter: "powers", target: "#builder", anchor: "[data-tm=card2-lock]", side: "right",
    title: "The padlock: open or closed",
    body: "Open means the optimizer may re-slot that power. Closed means hands "
        + "off, and it means it absolutely: a locked power returns from a "
        + "re-solve exactly as you left it, down to individual enhancements, "
        + "and an empty slot inside it stays empty.\n\n"
        + "Lock what you have already decided — sets you own in game, a "
        + "particular proc in a particular power." },
  { chapter: "powers", target: "#builder", anchor: "[data-tm=card2]", side: "right",
    title: "When a lock is costing you",
    body: "Locks constrain the answer. A locked power that is slotted poorly "
        + "caps how good everything around it can be, and a lower result "
        + "afterwards is the solver being honest rather than failing.\n\n"
        + "So when a target you used to reach suddenly falls short, check your "
        + "locks first. Unlock, re-solve, compare." },
  { chapter: "powers", target: "#preserve-toggle", anchor: "[data-tm=preserve-label]", side: "left",
    title: "Preserve my IO sets",
    body: "The broad-stroke alternative to locking, and usually the right "
        + "choice for a character you actually play: keep every set you have "
        + "already paid for, and let the optimizer improve only the generic "
        + "enhancements and the empty slots around them." },

  // ── Letting it build for you ───────────────────────────────────────────────
  { chapter: "solve", target: "#solve-btn", spine: true, side: "left",
    title: "Solve the slotting",
    body: "This works out the best enhancement layout it can find for the "
        + "powers you have taken, aimed at your Content, Role and any targets "
        + "you set. It is real arithmetic over the game's actual numbers, not a "
        + "template.\n\n"
        + "Two promises it always keeps: it never changes which powers you "
        + "chose, and it obeys your padlocks and the Preserve setting." },
  { chapter: "solve", target: "#gen-btn", side: "left",
    title: "Or have it pick the powers too",
    body: "Generate goes further than Solve: it chooses which powers to take as "
        + "well as how to slot them — pools, epic and incarnates included — "
        + "following the same rules the game enforces.\n\n"
        + "Where a certified champion build exists for your combination it "
        + "starts from there rather than from nothing. Whatever it produces, "
        + "you can still change anything by hand afterwards." },
  { chapter: "solve", target: "#ai-response", anchor: "[data-tm=response]", side: "left",
    title: "Achieved versus target",
    body: "After a solve you get the result in plain terms: what you asked for, "
        + "what it reached, and what it changed. If something fell short it "
        + "does not go quiet about it — it names the unpicked powers on your "
        + "character that would close the gap and roughly what each would add.\n\n"
        + "A goal you cannot reach is worth knowing about rather than chasing." },
  { chapter: "solve", target: "#changes-btn", scene: "changes", anchor: "[data-tm=changes-box]", side: "right", slim: true,
    title: "What changed?",
    body: "For imported characters, the What changed? button opens this window: "
        + "one line per power — what was slotted, what it is now — and a "
        + "closing line saying what the changes bought you.\n\n"
        + "It is a report, not a confirmation: open and close it as often as "
        + "you like. From here you can also export the result as a .mbd, keep "
        + "it, or put everything back with Reset." },
  { chapter: "solve", target: "#reset-btn", side: "left",
    title: "Reset to imported",
    body: "Puts an imported build back exactly as it came in, so you can try a "
        + "different goal, role or options without re-importing.\n\n"
        + "Reset means reset: custom targets and similar settings attached to "
        + "the build are cleared with it. When there is something like that to "
        + "lose, the app tells you first — nothing is dropped silently." },
  { chapter: "solve", target: "#tray-out", side: "right",
    title: "Your in-game trays",
    body: "After a solve, the plan lands the way you will actually play it: a "
        + "suggested layout for the game's power trays — the attack chain "
        + "together where your fingers live, toggles and autos parked out of "
        + "the click path.\n\n"
        + "This is one of three reference sections at the foot of the tab, and "
        + "they start folded shut: click the heading to open one, and it stays "
        + "open next time. Copy the trays into the game once and muscle memory "
        + "does the rest." },
  { chapter: "solve", target: "#order-out", side: "right",
    title: "The respec order",
    body: "The respec screen in game asks you to re-place every pick, in "
        + "order, from level 1 up. This is that order, one line per pick, so "
        + "at the trainer you just read down the list instead of "
        + "reconstructing it from memory.\n\n"
        + "Folded shut like its neighbours — the third one, Get expensive IOs "
        + "cheap, prices the enhancements you still need." },
  // ── The three fixed cards on Powers & Slots (2026-08-04 layout) ────────────
  { chapter: "powers", target: "#cmd-card", anchor: "[data-tm=cmd-box]", side: "top",
    title: "Getting a build in and out of the game",
    body: "The game's own chat commands do the carrying, and this card holds the "
        + "ones worth knowing. Click any of them to copy it, then Ctrl+V into "
        + "the game's chat box.\n\n"
        + "/build_save_file writes your live character to a file this app can "
        + "import; /respec starts the respec you follow with the level plan; "
        + "/ah opens the auction house for the shopping list; /logchat turns on "
        + "the log the Logging tab reads." },
  { chapter: "stats", target: "#at-bonus-group", side: "right",
    title: "What your archetype gets for free",
    body: "Every archetype has a built-in mechanic no power pick grants — Fury "
        + "on a Brute, Vigilance on a Defender, Domination on a Dominator. It "
        + "sits at the top of your stats, above Defence, because that is what it "
        + "is: a stat you did not have to spend a pick on.\n\n"
        + "The right-hand word is the honest part. Counted means it is already "
        + "in the score the optimizer chases, on the basis shown beside it. "
        + "Shown only means it is real in game but deliberately left out, "
        + "because assuming it would flatter your build. Not modeled is an "
        + "admitted gap. It never pretends either way." },
  { chapter: "solve", target: "#validation", side: "left",
    title: "The rules check",
    body: "Anything the game would not allow shows up here: too many pools, an "
        + "enhancement in a power that cannot take it, a power taken before "
        + "its level, a second copy of a unique. If this is clear, the build "
        + "is legal — you can respec into it in game exactly as shown.\n\n"
        + "The checks are the game's own rules, which is also why the app "
        + "sometimes refuses a request: it will not plan something the game "
        + "would reject." },

  // ── Where your numbers come from ───────────────────────────────────────────
  { chapter: "stats", target: "#stats", spine: true, anchor: "[data-tm=stats-head]", side: "right",
    title: "Your numbers, live",
    body: "Defence, resistance, recharge, recovery, damage — every figure "
        + "computed from the game's own data, updating as you change anything. "
        + "They include your enhancements, your set bonuses, and the toggles "
        + "and auto powers you would actually be running.\n\n"
        + "If the app and the game ever disagree, the game is right — and that "
        + "is a bug worth reporting from the Help menu." },
  { chapter: "stats", target: "#stats-miniwall", anchor: "[data-tm=mini-wall]", side: "bottom",
    title: "Your build, in miniature",
    body: "The wall above the stats is your Powers & Slots in miniature — same "
        + "cards, same enhancement icons, just small. It exists for one "
        + "reason: when you click a stat below, everything feeding that stat "
        + "turns green up here, so the number and its sources are visible "
        + "together. Two marks, and the breakdown lists both in a legend: a "
        + "ring around an enhancement means that IO feeds the number, and a box "
        + "around a power's NAME means the power grants it by itself, with no "
        + "enhancement involved.\n\n"
        + "Inherents with nothing slotted fold into the one-line strip at the "
        + "bottom." },
  { chapter: "stats", target: "#stat-breakdown", anchor: "[data-tm=breakdown-box]", side: "left",
    title: "Click a stat, get its receipts",
    body: "Click any stat row and this breakdown opens beside it: every power "
        + "and IO that feeds the number, with the exact contribution of each — "
        + "set bonuses by tier, always-on globals, and powers that grant the "
        + "stat by themselves, marked with a green box on their name because "
        + "there is no IO to ring.\n\n"
        + "It is editable in place: click any IO chit in the breakdown to "
        + "change it, and the change is real — your build and every number "
        + "update, everywhere. The arrow keys walk you up and down the stat "
        + "list." },
  { chapter: "stats", target: "#res-cap-chip", anchor: "[data-tm=ctl-row]", side: "bottom",
    title: "Caps are per archetype",
    body: "Resistance stops counting at your archetype's cap: 90% for Tankers "
        + "and Brutes, 85% for Kheldians and the Arachnos archetypes, 75% for "
        + "everyone else. Defence has a soft cap at 45%, where most incoming "
        + "attacks already miss.\n\n"
        + "Points past the line are wasted, which is why the app will not "
        + "chase them: a slot buying resistance past the cap is a slot better "
        + "spent anywhere else." },
  { chapter: "stats", target: "#suppression-toggle", anchor: "[data-tm=sup-label]", side: "bottom",
    title: "The view switches",
    body: "The control line holds the what-if switches. In-combat view shows "
        + "your totals as they are mid-fight — powers like Stealth lose part "
        + "of their defence the moment you attack, and the mid-fight number is "
        + "usually the one worth planning around. Include incarnates folds "
        + "your Destiny and Hybrid buffs in, matching Mids' fully-buffed "
        + "display; the accolades switch adds those.\n\n"
        + "All display choices only: Solve optimizes the same numbers either "
        + "way." },
  { chapter: "stats", target: "#exemplar-sel-stats", anchor: "[data-tm=exemp-dial-stats]", side: "bottom",
    title: "Exemplared numbers",
    body: "The same exemplar dial from the build bar lives here too. Set a "
        + "level and every stat on this page becomes the exemplared truth: "
        + "powers received above that level plus five switch off, set bonuses "
        + "above the piece's level go quiet — per piece, exactly as the game "
        + "does it — and a banner states the view in bold.\n\n"
        + "The advice on the banner is numeric: what you lose at that level, "
        + "and what fully-attuned IOs would win back." },
  { chapter: "stats", target: "#offense-stats", anchor: "[data-tm=atk-table]", side: "right",
    title: "Every attack, priced",
    body: "The offense numbers are clickable like everything else. Under the "
        + "headline figures, each attack you own is priced: its damage, how "
        + "long its animation locks you in place, its recharge, and DPA — "
        + "damage per second of animation, the honest measure of an attack's "
        + "worth.\n\n"
        + "A good attack chain is built from the top of this table down." },
  { chapter: "stats", target: "#offense-stats", anchor: "[data-tm=support-note]", side: "right",
    title: "When you play support",
    body: "This example is a damage Brute, so the panel stays lean. Play a "
        + "support set, a controller or a Mastermind and it grows: per-pet "
        + "damage, your enemy debuffs at their base value per application, and "
        + "what your buffs hand allies.\n\n"
        + "Pet damage is honest about hit chance: pets are scored with their "
        + "real chance to hit at their own level — which is exactly why ToHit "
        + "buffs like Tactics visibly raise pet damage." },

  // ── The end game ───────────────────────────────────────────────────────────
  { chapter: "endgame", target: "#accolades-card", spine: true, anchor: "[data-tm=acc-box]", side: "right",
    title: "Accolades",
    body: "Accolades are permanent bonus powers the game awards for "
        + "collections of badges — real hit points and endurance. Tick the "
        + "ones your character has earned and your totals recalculate; the "
        + "greyed rows belong to the other alignment, which is exactly why "
        + "flipping Hero/Villain moves your numbers.\n\n"
        + "The ⓘ on each row tells you how to earn it in game, and Preview all "
        + "shows your numbers with every accolade in hand.\n\n"
        + "You'll find this checklist on Powers & Slots, right under the "
        + "powers wall." },
  { chapter: "endgame", target: "#sel-epic", anchor: "[data-tm=epic-row]", side: "right",
    title: "Epic pools",
    body: "Epic and patron pools open at level 35 and reach outside your "
        + "archetype's normal toolkit — armour for a damage dealer, or a "
        + "ranged attack for our melee Brute.\n\n"
        + "The list is per archetype and tiered like the game's own, and the "
        + "special cases are honoured: Kheldians have no epic at all, and a "
        + "patron pool says on it that a patron arc unlocks it in game.\n\n"
        + "The Epic & Ancillary fold lives in the right column of Powers & "
        + "Slots, under the Build Assistant — the incarnate pickers are "
        + "inside the same fold." },
  { chapter: "endgame", target: "#incarnate-selectors", spine: false, anchor: "[data-tm=inc-row]", side: "right",
    title: "Incarnates, explained per pick",
    body: "The incarnate system opens at level 50. Under every slot's dropdown, "
        + "the current pick shows its own description and the exact numbers "
        + "our math folds into your totals at peak — and a choice our math "
        + "does not price yet says so at the point of choice, rather than "
        + "silently doing nothing.\n\n"
        + "Incarnate buffs are situational, so they stay out of the passive "
        + "totals until you tick Include incarnates (peak) on the Stats tab." },

  // ── The leveling guide ─────────────────────────────────────────────────────
  { chapter: "leveling", target: "#journey-body", spine: true, anchor: "[data-tm=road]", side: "bottom",
    title: "Your 1-to-50 as a road",
    body: "Every marker is a level, and the ★ is where your character stands — "
        + "green rings mean levels already reached. Click any stop and the "
        + "panel below reads that level: its pick, when the next enhancement "
        + "slot arrives, the zones that fit you and how their enemies will "
        + "feel, badges worth grabbing, and which task forces have just "
        + "opened.\n\n"
        + "It follows the game's real schedule, special careers included." },
  { chapter: "leveling", target: "#journey-body", anchor: "[data-tm=art-box]", side: "right",
    title: "The place you are going",
    body: "The picture is the game's own art for the zone the selected level "
        + "sends you to, and it changes as you click along the road — Atlas "
        + "Park at 1, Peregrine Island at 50.\n\n"
        + "Where the game ships no art for a zone, the slot says so instead of "
        + "showing a picture of the wrong place." },
  { chapter: "leveling", target: "#journey-body", anchor: "[data-tm=align-preview]", side: "right",
    title: "Previewing other routes",
    body: "This row previews where somebody on another side would level — Hero, "
        + "Vigilante, Rogue, Villain, and 🌀 Flashback, which is not a side at "
        + "all but Ouroboros: replaying older arcs at their original level, "
        + "which has to be unlocked.\n\n"
        + "It is a preview and nothing more. Your character, your build and "
        + "your numbers are unchanged, and it lasts only while you are on this "
        + "tab — leave and come back and you are looking at your own side "
        + "again. Your real alignment is set from the View menu, and choosing "
        + "one there always wins over a preview showing here." },

  // ── Your play log ──────────────────────────────────────────────────────────
  { chapter: "logging", target: "#gamelog", spine: true, anchor: "[data-tm=gl-body]", side: "right",
    title: "Play Log",
    body: "Turn it on and this is what it builds from your own chat logs, on "
        + "your machine: each session with who you played and what you "
        + "levelled, and your haul appraised for you — keep, craft, or sell, "
        + "answered per drop.\n\n"
        + "It is entirely optional and off until you turn it on." },
  { chapter: "logging", target: "#gl-pulse", anchor: "[data-tm=boards-row]", side: "right",
    title: "Your boards",
    body: "My private board is your own data, built locally and never "
        + "uploaded. What sharing shows is a preview of the sanitized public "
        + "variant — exactly what feeding the community boards would share, so "
        + "the choice to share is an informed one." },
  { chapter: "logging", target: "#share-line", anchor: "[data-tm=share-row]", side: "bottom",
    title: "Sharing is a separate choice",
    body: "Reading your logs locally and sharing anything anywhere are "
        + "separate choices, each asked separately. The feed is off until you "
        + "say yes, and the prompt states exactly what would be shared: your "
        + "own rewards and public recruitment lines — never raw chat, never "
        + "private tells.\n\n"
        + "Closing the question stores nothing; it is not a decision." },

  // ── Menus, saving and help ─────────────────────────────────────────────────
  { chapter: "header", target: "#masthead", spine: true, anchor: "[data-tm=menubar]", side: "bottom",
    title: "Four menus run the app",
    body: "Character holds every way in and out: continue, new, import, "
        + "export, save, switch. Build holds the solver actions. View switches "
        + "tabs and display toggles. Help holds this tour, the guide, updates "
        + "and the bug report.\n\n"
        + "Every item carries its one-line description, so nothing needs "
        + "memorising." },
  { chapter: "header", target: "#m-build", anchor: "[data-tm=menu-build]", side: "bottom",
    title: "The Build menu",
    body: "Solve the slotting lives here, along with Customise build targets, "
        + "the What changed? report, Undo and Reset to imported — the same "
        + "actions the Assistant panel offers, reachable from any tab.\n\n"
        + "Some of them will be greyed out, and each says why in its own line: "
        + "What changed? only compares an imported build against a solve, and "
        + "Reset to imported needs a file to go back to. Greyed here means not "
        + "applicable yet, never broken." },
  { chapter: "header", target: "#m-view", anchor: "[data-tm=menu-view]", side: "bottom",
    title: "The View menu",
    body: "Every tab, one click away — plus your alignment, and Exemplared "
        + "view, which opens a dialog explaining what exemplaring does to a "
        + "build before it asks you for a level.\n\n"
        + "The display toggles (incarnates at peak, PvP mode, the in-combat "
        + "view…) live on the Stats control row, right where their numbers "
        + "move." },
  { chapter: "header", target: "#m-help", anchor: "[data-tm=menu-help]", side: "bottom",
    title: "The Help menu",
    body: "The guided tour you are in now, the full user guide as a PDF stored "
        + "with the app, the bug report, champion submission, and Check for "
        + "updates — which compares version numbers with the project's release "
        + "page and sends nothing else. Nothing is ever downloaded or "
        + "installed without you saying so.\n\n"
        + "Settings is here too: start with Windows, whether to check for a new "
        + "version at launch, and whether the Play Log may read your game logs. "
        + "Credits names everyone this is built on, and About says which build "
        + "you are running." },
  { chapter: "header", target: "#m-view", anchor: "[data-tm=menu-view]", side: "bottom",
    title: "Your alignment",
    body: "The View menu's Alignment entry opens the four choices: Hero, "
        + "Vigilante, Rogue and Villain. It "
        + "reskins the whole app and decides which side's information you see "
        + "— a Vigilante levels like a hero and can also visit villain "
        + "content; a Rogue is the mirror of that.\n\n"
        + "It will not change how your build scores: the game treats a "
        + "Vigilante as hero-side and a Rogue as villain-side. Accolades are "
        + "side-specific, so moving between the pairs can shift totals "
        + "slightly — nothing you ticked is thrown away; the other side's "
        + "accolades grey out and wait." },
  { chapter: "header", target: "#bug-btn", spine: false, scene: "bugreport", anchor: "[data-tm=bug-box]", side: "right", slim: true,
    title: "Something wrong? Say so",
    body: "This is the form behind Report a bug, and it goes straight to the "
        + "developer with no account needed. The hard part of a good report — "
        + "your version, model and game-data numbers — is filled in for you; "
        + "the checkbox attaches the build itself so the problem can be "
        + "reproduced. Nothing leaves your machine until you press Send.\n\n"
        + "That is the tour. Every ? in the app brings you back to the exact "
        + "part it sits on, and the Help menu holds the rest, whenever you "
        + "want it." },
];


// ── State the tour keeps, and what counts as "seen" ──────────────────────────
// Two different states, deliberately kept apart (closing is not a decision).
// FINISHED is permanent and only earned by reaching the last step. LATER is
// this-session-only, so "maybe later" genuinely means later. Merely STARTING the
// tour marks nothing: one someone opened and abandoned must still be offered.
const _tourFinished = () => {
  try { return localStorage.getItem("cohTourFinished") === "1"; } catch (e) { return false; }
};
const _tourMarkFinished = () => {
  try { localStorage.setItem("cohTourFinished", "1"); } catch (e) {}
};
const _tourLater = () => {
  try { return sessionStorage.getItem("cohTourLater") === "1"; } catch (e) { return false; }
};
window._tourMarkLater = () => {
  try { sessionStorage.setItem("cohTourLater", "1"); } catch (e) {}
};
// The saved SPOT (Joel, 2026-07-27: "there should always be a save favorite,
// or exit"). Every card carries an explicit save-and-leave; the compass
// chooser then offers to resume exactly there. Saving is the user's explicit
// act -- a plain Esc/✕ exit stores nothing (closing is not a decision).
const _tourSpot = () => {
  try { return JSON.parse(localStorage.getItem("cohTourSpot") || "null"); } catch (e) { return null; }
};
const _tourSaveSpot = (chapter, index) => {
  try { localStorage.setItem("cohTourSpot", JSON.stringify({ c: chapter || "", i: index | 0 })); } catch (e) {}
};
const _tourClearSpot = () => {
  try { localStorage.removeItem("cohTourSpot"); } catch (e) {}
};

function _tourVisible(el) {
  if (!el) return false;
  // Two traps, both found by driving this in a real browser:
  //   - width>0 && height>0 is wrong: a flex container can compute to zero WIDTH
  //     while fully visible (#entry-cards does), which hid the offer entirely.
  //   - offsetParent !== null is wrong: it is ALWAYS null for position:fixed, so
  //     every modal and overlay read as invisible.
  const cs = getComputedStyle(el);
  return cs.display !== "none" && cs.visibility !== "hidden"
      && el.getClientRects().length > 0;
}

// Where a step's highlight actually lands: the mock's stand-in for the real
// control. The step's `target` keeps naming the REAL id (that is what the
// audit verifies against the app); the mock marks its copy with data-for.
//
// `anchor` narrows the highlight WITHIN the mock (always "[data-tm=...]",
// which the audit verifies exists). It exists because of Joel's screenshots
// (2026-07-27): a step whose subject is a whole panel or a full-screen
// wrapper put the green box around everything -- or around nothing visible --
// and the card then sat on top of the very content it was explaining. The
// anchor points at the set-summary line, the actual padlock, the modal BOX
// rather than its full-screen backdrop.
function _tourMockEl(s) {
  if (!_mockEl) return null;
  if (s.anchor) return _mockEl.querySelector(s.anchor);
  return _mockEl.querySelector(`[data-for="${s.target.replace(/^#/, "")}"]`);
}


// ── Engine: driver.js ────────────────────────────────────────────────────────
// The spotlight, tooltip placement, viewport clamping, scroll-into-view and
// keyboard handling are driver.js's job now (static/vendor, MIT, pinned 1.8.0,
// zero dependencies, loaded locally so the app stays offline).
//
// WHY THE SWITCH (2026-07-27): this engine was hand-rolled first, and its
// POSITIONING failed in the field three times running -- a card pushed off the
// top of the screen, a 4px spotlight sliver over an obscured panel, an offer
// that rendered invisible. Those are exactly the edge cases a mature library has
// already solved. What stayed ours is everything the library has no opinion on:
// the step catalogue, the audit that keeps it true, the never-touch-your-work
// rule, the persistence rules, and deciding what is actually POINTABLE in this
// app's own layout.

let _driver = null;

function _tourHtml(text) {
  return String(text).split("\n\n").map(p => `<p>${escHtml(p)}</p>`).join("");
}

// Turn one catalogue entry into a driver.js step. The element is the MOCK's
// stand-in; __tmScreen tells onHighlightStarted which fake screen to show.
function _tourToDriverStep(s, i, all) {
  // Say WHICH section this is and how far through it you are. On a 46-step
  // complete tour, "12 of 46" alone tells you nothing about whether you are
  // nearly done with a topic or just starting one.
  const inChapter = all.filter(x => x.chapter === s.chapter);
  const nth = inChapter.indexOf(s) + 1;
  const label = TOUR_CHAPTERS[s.chapter] || "";
  const crumb = `<p class="tour-crumb">${escHtml(label)} · ${nth} of ${inChapter.length}</p>`;
  const art = s.diagram && TOUR_DIAGRAMS[s.diagram] ? TOUR_DIAGRAMS[s.diagram] : "";
  return {
    element: _tourMockEl(s),
    __tmScene: s.scene || (s.chapter === "start" ? "menus" : "build"),
    __tmTab: s.tab || TM_TAB[s.chapter] || "powers",
    __tmTop: s.top,
    // `side` steers the card into empty space instead of over the subject
    // (rail steps open rightward into the build column, build-column steps
    // open leftward over the rail) -- driver still flips it if it won't fit.
    popover: { title: s.title,
               description: crumb + art + _tourHtml(s.body),
               popoverClass: s.diagram ? "tour-wide" : (s.slim ? "tour-slim" : ""),
               side: s.side, align: s.align },
  };
}

// ONE rule for stray clicks, everywhere (Joel's ruling, 2026-07-27 second
// pass): a click outside the card does NOTHING. Advancing is Next, the
// arrow keys, or the space bar; leaving is Exit, the ✕, or Esc -- every
// move is a deliberate press, never a stray click. Capture-phase, so
// driver's own document handler (which would close on outside clicks with
// small targets and advance with big ones) never sees them at all.
function _tourDocClick(e) {
  if (!_driver) return;
  if (e.target.closest(".driver-popover")) return;   // the card's own controls
  e.preventDefault();
  e.stopImmediatePropagation();
}

// Space bar = Next (Joel's suggestion). Driver already handles the arrow
// keys and Esc; space would otherwise just scroll the mock.
function _tourKey(e) {
  if (!_driver || e.key !== " ") return;
  e.preventDefault();
  e.stopImmediatePropagation();
  if (_driver.isActive() && _driver.hasNextStep()) _driver.moveNext();
}

window.endTour = function () {
  document.removeEventListener("click", _tourDocClick, true);
  document.removeEventListener("keydown", _tourKey, true);
  if (_driver && _driver.isActive()) _driver.destroy();
  _driver = null;
  _closeTourMock();
};

// chapter: undefined = the short first-run tour (the spine); a chapter key =
// that section only; "all" = every step. Whatever the choice, the tour runs
// over the mock, so every subset works from anywhere in any app state.
window.startTour = function (chapter, atIndex) {
  if (!(window.driver && window.driver.js && window.driver.js.driver)) {
    console.warn("[tour] driver.js did not load; tour unavailable");
    return;
  }
  const live = chapter === "all" ? TOUR_STEPS.slice()
    : chapter ? TOUR_STEPS.filter(s => s.chapter === chapter)
      : TOUR_STEPS.filter(s => s.spine);
  if (!live.length) return;

  endTour();
  _openTourMock();
  _mockShowScene(live[0].scene || (live[0].chapter === "start" ? "menus" : "build"),
                 live[0].tab || TM_TAB[live[0].chapter] || "powers");
  _driver = window.driver.js.driver({
    steps: live.map((s, i) => _tourToDriverStep(s, i, live)),
    showProgress: true,
    progressText: "{{current}} of {{total}}",
    nextBtnText: "Next →",
    prevBtnText: "← Back",
    doneBtnText: "Done",
    smoothScroll: true,
    stagePadding: 6,
    stageRadius: 8,
    // NO dark overlay (Joel, 2026-07-27: with the green outline doing the
    // pointing, blacking out the rest of the screen was a "where am I?"
    // moment). The overlay element stays -- it is what makes a stray click
    // advance instead of interacting -- it is just fully transparent.
    overlayOpacity: 0,
    allowClose: true,               // Esc and the ✕ both leave, deliberately
    // No overlayClickBehavior: there is no overlay, and _tourDocClick swallows
    // every outside click before driver sees it (Joel's ruling: stray clicks
    // do nothing -- Next/space/arrows advance, Exit/✕/Esc leave).
    // The mock is a picture -- blocking interaction keeps it one.
    disableActiveInteraction: true,
    // Flip the mock to the step's scene -- opening menu, builder, the ⓘ
    // details column, or the set picker -- so each card is explained at the
    // place it happens. Fires before positioning, so the element is visible
    // when measured.
    onHighlightStarted: (el, step) => {
      if (step && step.__tmScene) _mockShowScene(step.__tmScene, step.__tmTab);
      // Pre-scroll the subject into the UPPER THIRD of the screen. driver
      // centres it, which leaves ~half a screen below -- less than a card,
      // so the card got clamped upward OVER the subject (Joel's screenshots:
      // the set-bonuses card buried the sets line it described). With the
      // subject high, every card fits cleanly beneath. The picker modal is
      // fixed-position, so scrolling would only shift the backdrop -- skip.
      if (el && _mockEl && !el.closest(".tm-modal")) {
        const r = el.getBoundingClientRect();
        // Steps with tall cards (diagrams) can ask for a higher perch (__tmTop).
        _mockEl.scrollTop += r.top - window.innerHeight * (step.__tmTop || 0.22);
      }
    },
    // Esc / ✕ / Done all pass through destroy; the mock must never outlive
    // the tour, or it would sit as a full-screen lid over the real app.
    onDestroyed: () => {
      document.removeEventListener("click", _tourDocClick, true);
      document.removeEventListener("keydown", _tourKey, true);
      _closeTourMock(); _driver = null;
    },
    // EVERY card carries an explicit way out (Joel: "there should always be a
    // save favorite, or exit"): save your spot and leave -- the 🧭 chooser
    // offers to resume there -- or just leave.
    onPopoverRender: (popover, opts) => {
      const idx = (opts && opts.state && opts.state.activeIndex) | 0;
      const row = document.createElement("div");
      row.className = "tour-exit-row";
      const save = document.createElement("button");
      save.type = "button";
      save.textContent = "★ Save my spot & exit";
      save.title = "Leave the tour and keep your place — the 🧭 compass will offer to resume exactly here.";
      save.onclick = () => { _tourSaveSpot(chapter, idx); endTour(); };
      const exit = document.createElement("button");
      exit.type = "button";
      exit.textContent = "Exit tour";
      exit.title = "Leave the tour (Esc works too)";
      exit.onclick = () => endTour();
      row.append(save, exit);
      popover.wrapper.appendChild(row);
    },
    onHighlighted: () => {
      if (!_driver || _driver.hasNextStep()) return;
      // Finished = reached the end of a tour that covered every chapter (the
      // complete tour or the first-run spine). A single section does not count.
      if (chapter === "all" || chapter === undefined) { _tourMarkFinished(); _tourClearSpot(); }
    },
  });
  document.addEventListener("click", _tourDocClick, true);
  document.addEventListener("keydown", _tourKey, true);
  _driver.drive(Math.max(0, Math.min(atIndex | 0, live.length - 1)));
};

// Explain ONE card on the opening menu, then carry on through the rest of that
// chapter. The entry cards are themselves <button>s, so their ? has to be a span
// that stops the click from reaching the card -- otherwise asking what a card
// does would trigger it, which is the opposite of helpful.
window.explainEntry = function (elementId, ev) {
  if (ev && ev.stopPropagation) ev.stopPropagation();
  const steps = TOUR_STEPS.filter(s => s.chapter === "start");
  const idx = steps.findIndex(s => s.target === "#" + elementId);
  startTour("start", idx < 0 ? 0 : idx);
};

// ── The chooser: where do you want to start? ─────────────────────────────────
// Requesting help does not drop you straight into a 30-step walk. It asks which
// part you care about, because someone confused about slots does not want six
// cards about the opening screen first. "Everything" is offered at the top for
// people who do want the lot, labelled with its real length rather than a
// comfortable fiction.
window.closeTourMenu = function () {
  const m = document.getElementById("tour-menu");
  if (m) m.remove();
};

// Resume at a saved spot. The spot is cleared on resume -- saving again is
// one click away on every card, so a stale bookmark never lingers.
window.resumeTour = function () {
  const s = _tourSpot();
  if (!s) { openTourMenu(); return; }
  _tourClearSpot();
  startTour(s.c === "" ? undefined : s.c, s.i | 0);
};

// The list a saved spot refers to, or null if that selection no longer exists
// (e.g. a chapter renamed between releases -- the row simply is not offered).
function _tourSpotList(c) {
  const list = c === "all" ? TOUR_STEPS
    : c ? TOUR_STEPS.filter(s => s.chapter === c)
      : TOUR_STEPS.filter(s => s.spine);
  return list.length ? list : null;
}

window.openTourMenu = function () {
  closeTourMenu();
  endTour();
  const spot = _tourSpot();
  const spotList = spot ? _tourSpotList(spot.c === "" ? undefined : spot.c) : null;
  const resumeRow = spotList
    ? `<button class="tour-menu-row tour-menu-resume" onclick="closeTourMenu(); resumeTour();">
         <b>★ Resume where you left off</b>
         <span class="muted small">${escHtml(spot.c === "all" ? "The complete tour"
           : spot.c ? (TOUR_CHAPTERS[spot.c] || spot.c) : "The short tour")}
           · step ${Math.min((spot.i | 0) + 1, spotList.length)} of ${spotList.length}</span>
         <span class="tour-menu-n">saved</span>
       </button>`
    : "";
  const total = TOUR_STEPS.length;
  const rows = Object.keys(TOUR_CHAPTERS).map(k => {
    const n = TOUR_STEPS.filter(s => s.chapter === k).length;
    return `<button class="tour-menu-row" onclick="closeTourMenu(); startTour('${k}');">
              <b>${escHtml(TOUR_CHAPTERS[k])}</b>
              <span class="muted small">${escHtml(TOUR_CHAPTER_BLURB[k] || "")}</span>
              <span class="tour-menu-n">${n} step${n === 1 ? "" : "s"}</span>
            </button>`;
  }).join("");
  const wrap = document.createElement("div");
  wrap.id = "tour-menu";
  wrap.className = "modal";
  wrap.innerHTML =
    `<div class="entry-box tour-menu-box">
       <div class="wizard-head">
         <h2>🧭 What would you like explained?</h2>
         <button class="linkchip" onclick="closeTourMenu()">✕ Close</button>
       </div>
       <p class="muted small">Pick a section, or take the lot. Nothing you see here changes
         your build, and every card has "Save my spot &amp; exit" — leave any time and
         resume right here.</p>
       ${resumeRow}
       <button class="tour-menu-row tour-menu-all" onclick="closeTourMenu(); startTour('all');">
         <b>The complete tour</b>
         <span class="muted small">Every section, start to finish, in order.</span>
         <span class="tour-menu-n">${total} steps</span>
       </button>
       <div class="tour-menu-list">${rows}</div>
     </div>`;
  document.body.appendChild(wrap);
  wrap.addEventListener("click", e => { if (e.target === wrap) closeTourMenu(); });
};

// ── The first-run offer ──────────────────────────────────────────────────────
// WHO GETS OFFERED (Joel's rule): a fresh install. If the machine already has
// saved characters, the person has clearly used this before and does not need to
// be asked -- the ? circles and the header compass are there when they want them.
// That is a better signal than a "have I shown this yet" flag, because it
// survives clearing browser storage and reinstalls.
window.maybeOfferTour = async function () {
  if (_tourFinished() || _tourLater()) return;
  if (document.querySelector(".tour-offer")) return;   // called from init AND showEntry
  const host = document.getElementById("entry-cards");
  if (!host || !_tourVisible(host)) return;
  try {
    const res = await api("/saves");
    if (((res && res.saves && res.saves.length) || 0) > 0) return;   // not a new user
  } catch (e) { return; }        // cannot tell: say nothing rather than nag
  if (document.querySelector(".tour-offer")) return;   // may have raced while awaiting
  const bar = document.createElement("div");
  bar.className = "tour-offer";
  bar.innerHTML =
    `<span class="tour-offer-ico">🧭</span>
     <span class="tour-offer-txt"><b>New here?</b> Take a guided tour — it points at each part
       of the app and explains what it does. Nothing is changed or built along the way, and
       you can leave at any point.</span>
     <button onclick="this.closest('.tour-offer').remove(); openTourMenu();">Show me around</button>
     <button class="secondary" onclick="_tourMarkLater(); this.closest('.tour-offer').remove();"
       title="Hides it for now. The compass in the header and the ? next to each section will still explain anything, any time.">Maybe later</button>`;
  host.parentNode.insertBefore(bar, host);
};

// The per-section entry point: a quiet ? circle that explains just that section.
// Small on purpose -- it sits beside a heading without competing with it.
window.tourHelpLink = function (chapter) {
  return `<button class="tour-help" onclick="startTour('${chapter}')" `
       + `aria-label="Explain this section" `
       + `title="Explain this section">?</button>`;
};

// DEEP LINK: a ? sitting ON a thing jumps to the exact step that explains
// that thing (Joel, 2026-07-27: standing on a power with slots, one click
// should land on that area defined -- not on page one of a chapter). Steps
// opt in with a stable `key`; audit_tour.py verifies every explainStep()
// reference in the app resolves to a real key. From the landing step, Next
// continues through the rest of that chapter as usual.
window.explainStep = function (key, ev) {
  if (ev && ev.stopPropagation) ev.stopPropagation();
  const s = TOUR_STEPS.find(x => x.key === key);
  if (!s) { openTourMenu(); return; }   // unknown key: degrade to the chooser
  startTour(s.chapter, TOUR_STEPS.filter(x => x.chapter === s.chapter).indexOf(s));
};
