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
  <circle cx="196" cy="72" r="7" class="d-ctl d-hot"/><text x="196" y="76" class="d-glyph">i</text>
  <rect x="106" y="88" width="26" height="14" rx="7" class="d-chip d-hot"/><text x="119" y="99" class="d-lvl">L6</text>
  <rect x="246" y="86" width="18" height="18" rx="4" class="d-ctl d-hot"/><text x="255" y="99" class="d-glyph">•</text>
  <rect x="268" y="86" width="18" height="18" rx="4" class="d-ctl d-hot"/><text x="277" y="100" class="d-glyph">–</text>
  <rect x="290" y="86" width="18" height="18" rx="4" class="d-ctl d-hot"/><text x="299" y="100" class="d-glyph">+</text>
  <rect x="312" y="86" width="18" height="18" rx="4" class="d-ctl d-hot"/><text x="321" y="100" class="d-glyph">x</text>
  <circle cx="118" cy="122" r="8" class="d-slot d-hot"/><circle cx="140" cy="122" r="8" class="d-slot d-hot"/>
  <circle cx="162" cy="122" r="8" class="d-slot d-hot"/><circle cx="184" cy="122" r="8" class="d-slot d-hot"/>
  <path d="M196 40 L196 62" class="d-arrow"/><text x="196" y="32" class="d-lbl d-mid">its full details</text>
  <path d="M60 96 L102 96" class="d-arrow"/><text x="56" y="99" class="d-lbl d-end">level</text>
  <path d="M255 168 L255 108" class="d-arrow"/><text x="255" y="182" class="d-lbl d-mid">lock</text>
  <path d="M300 168 L288 108" class="d-arrow"/><text x="312" y="182" class="d-lbl d-mid">slots -/+</text>
  <path d="M370 96 L334 96" class="d-arrow"/><text x="374" y="99" class="d-lbl">drop it</text>
  <path d="M150 168 L150 132" class="d-arrow"/><text x="150" y="182" class="d-lbl d-mid">enhancement slots</text>
</svg>`,
  statBar: `
<svg viewBox="0 0 440 170" class="tour-svg" role="img"
     aria-label="An annotated stat bar showing the filled portion, the cap line, the printed figure, and the in-combat figure"><defs><marker id="tourArrowHead" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L8 4 L0 8 z" class="d-head"/></marker></defs>
  <text x="62" y="85" class="d-name d-end">Melee</text>
  <rect x="70" y="72" width="240" height="16" rx="4" class="d-chip"/>
  <rect x="70" y="72" width="204" height="16" rx="4" class="d-ico d-hot"/>
  <path d="M310 62 L310 98" class="d-slot d-hot"/>
  <text x="322" y="85" class="d-name">38.2%</text>
  <rect x="368" y="70" width="66" height="20" rx="4" class="d-hotbox"/>
  <text x="376" y="85" class="d-name">⚔ 31.9%</text>
  <path d="M130 138 L130 92" class="d-arrow"/><text x="130" y="152" class="d-lbl d-mid">what you have</text>
  <path d="M310 30 L310 58" class="d-arrow"/><text x="300" y="22" class="d-lbl d-mid">the bar ends at 45%</text>
  <path d="M392 138 L392 94" class="d-arrow"/><text x="392" y="152" class="d-lbl d-mid">in combat</text>
</svg>`,
  headerRow: `
<svg viewBox="0 0 440 200" class="tour-svg" role="img"
     aria-label="The header's row of small buttons: Journey, tour, save, help, bug report, champion, update check, alignment, and start over"><defs><marker id="tourArrowHead" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0 L8 4 L0 8 z" class="d-head"/></marker></defs>
  <rect x="20" y="78" width="400" height="40" rx="8" class="d-card"/>
  <text x="34" y="102" class="d-name">Hero Companion</text>
  <rect x="170" y="87" width="22" height="22" rx="4" class="d-ctl"/><text x="181" y="102" class="d-glyph">🗺️</text>
  <rect x="196" y="87" width="22" height="22" rx="4" class="d-ctl d-hot"/><text x="207" y="102" class="d-glyph">🧭</text>
  <rect x="222" y="87" width="22" height="22" rx="4" class="d-ctl"/><text x="233" y="102" class="d-glyph">💾</text>
  <rect x="248" y="87" width="22" height="22" rx="4" class="d-ctl"/><text x="259" y="102" class="d-glyph">❓</text>
  <rect x="274" y="87" width="22" height="22" rx="4" class="d-ctl"/><text x="285" y="102" class="d-glyph">🐞</text>
  <rect x="300" y="87" width="22" height="22" rx="4" class="d-ctl"/><text x="311" y="102" class="d-glyph">🏆</text>
  <rect x="326" y="87" width="22" height="22" rx="4" class="d-ctl d-hot"/><text x="337" y="102" class="d-glyph">⟳</text>
  <rect x="352" y="87" width="22" height="22" rx="4" class="d-ctl d-hot"/><text x="363" y="102" class="d-glyph">🦸</text>
  <rect x="378" y="87" width="22" height="22" rx="4" class="d-ctl d-hot"/><text x="389" y="102" class="d-glyph">↺</text>
  <path d="M207 50 L207 83" class="d-arrow"/><text x="207" y="42" class="d-lbl d-mid">this tour</text>
  <path d="M363 50 L363 83" class="d-arrow"/><text x="363" y="42" class="d-lbl d-mid">hero / villain</text>
  <path d="M337 146 L337 113" class="d-arrow"/><text x="337" y="160" class="d-lbl d-mid">check for updates</text>
  <path d="M389 174 L389 113" class="d-arrow"/><text x="389" y="188" class="d-lbl d-mid">start over</text>
</svg>`,
};

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

<div class="tour-mock-screen tm-center" data-tm-screen="entry">
  <div class="entry-box" data-tm="entry-box" data-for="entry-overlay">
    <h2>How do you want to start?</h2>
    <p class="muted">Pick a starting point — you can switch any time from the header.</p>
    <div class="entry-cards">
      <div class="entry-card" data-for="entry-continue">
        <div class="entry-ico">⏯️</div>
        <h3>Continue where you left off</h3>
        <p>Pick up a character you're partway through — leveling one from scratch is weeks of play, so your plan and progress are saved.</p>
        <span class="entry-go">3 saved — open →</span>
      </div>
      <div class="entry-card" data-for="entry-scratch">
        <div class="entry-ico">✨</div>
        <h3>Start a new character</h3>
        <p>Not sure what to roll? Tell me what you want to do and where you'll play — I'll recommend an archetype and powers and walk each level's pick and slotting.</p>
        <span class="entry-go">Pick my character →</span>
      </div>
      <div class="entry-card" data-for="entry-respec">
        <div class="entry-ico">♻️</div>
        <h3>Build a new level-50 character</h3>
        <p>Planning an end-game build from scratch? Tell me your archetype and main powersets — I'll build the optimized level-50 kit: picks, slotting, caps, epic, incarnates.</p>
        <span class="entry-go">Build a new 50 →</span>
      </div>
      <div class="entry-card" data-for="entry-mids">
        <div class="entry-ico">📋</div>
        <h3>Import a Mids Reborn build</h3>
        <p>Already have a <code>.mbd</code>? Load it for a critique, then optimize the slotting toward a goal — keeping the sets you've already invested in.</p>
        <span class="entry-go">Choose a .mbd file →</span>
      </div>
      <div class="entry-card entry-card-static" data-for="entry-ingame">
        <div class="entry-ico">🎮</div>
        <h3>Import a character you play</h3>
        <p>In game, type <code>/build_save_file</code> in chat — then come back here:</p>
        <span class="entry-go">🔍 Find my characters for me →</span>
      </div>
    </div>
  </div>
</div>

<div class="tour-mock-screen" data-tm-screen="build">
  <header class="tm-head" data-for="masthead">
    <h1>🦸 Hero Companion <span class="muted small">— Bruiser Brawlwell · Brute · level 50</span></h1>
    <div class="legend">
      <button class="iconbtn journey-pill" data-for="journey-btn" type="button">🗺️ <span class="journey-pill-label">Journey</span></button>
      <button class="iconbtn" data-tm="compass" type="button">🧭</button>
      <button class="iconbtn" data-for="save-btn" type="button">💾</button>
      <button class="iconbtn" data-for="help-btn" type="button">❓</button>
      <button class="iconbtn" data-for="bug-btn" type="button">🐞</button>
      <button class="iconbtn" data-for="champ-btn" type="button">🏆</button>
      <button class="iconbtn" data-for="update-btn" type="button">⟳</button>
      <button class="iconbtn" data-for="alignment-btn" type="button">🦸</button>
      <button class="iconbtn" data-for="start-over-btn" type="button">↺</button>
    </div>
  </header>

  <div class="tm-main">
    <section class="panel tm-setup" data-for="setup">
      <h2 data-tm="setup-head">Build</h2>
      <label>Archetype <select data-for="sel-archetype" disabled><option>Brute</option></select></label>
      <label>Primary <select data-for="sel-primary" disabled><option>Super Strength</option></select></label>
      <label>Secondary <select disabled><option>Willpower</option></select></label>
      <details open onclick="event.preventDefault()"><summary>Power Pools (up to 4)</summary>
        <div data-for="pool-selectors">
          <label>Pool 1 <select disabled><option>Fighting</option></select></label>
          <label>Pool 2 <select disabled><option>Leaping</option></select></label>
          <label>Pool 3 <select disabled><option>Speed</option></select></label>
        </div>
      </details>
      <label>Epic / Ancillary <select data-for="sel-epic" disabled><option>Energy Mastery</option></select></label>
      <label>Content <select data-for="preset-content" disabled><option>Task forces &amp; trials</option></select></label>
      <label>Role <select data-for="preset-role" disabled><option>Damage dealer</option></select></label>
      <div class="custom-targets-row">
        <button class="mini" data-for="custom-targets-btn" type="button">Customize build targets…</button>
      </div>
    </section>

    <div class="tm-buildcol">
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

      <div class="info-course">
        <div class="overview-card" data-for="overview-card">
          <div class="ovc-head">BUILD VITALS</div>
          <table class="ov-table">
            <tr><th></th><th>S/L</th><th>F/C</th><th>E/N</th><th>Mel</th><th>Rng</th><th>AoE</th></tr>
            <tr><th>DEF %</th><td>32</td><td>28</td><td>26</td><td class="ov-good">41</td><td>36</td><td>30</td></tr>
            <tr><th>RES %</th><td class="ov-good">90</td><td>52</td><td>46</td><td class="ov-dim">—</td><td class="ov-dim">—</td><td class="ov-dim">—</td></tr>
          </table>
          <div class="ov-buildline">
            <span>Recharge <b class="ov-good">+72.5%</b></span>
            <span>Recovery <b>+25%</b></span>
            <span>HP <b>+21.4%</b></span>
            <span>DPS <b>187</b> ST / <b>41</b> AoE</span>
          </div>
        </div>
        <div class="overview-card" data-for="bonuses-card">
          <div class="ovc-head">SET BONUSES <span class="muted">(23 active)</span></div>
          <div class="muted small">×3 Large Improved Recharge Bonus</div>
          <div class="muted small">×2 Moderate Increased Health Bonus</div>
          <div class="muted small">×2 Small Smashing/Lethal Defense Bonus</div>
          <div class="muted small">… +18 more</div>
        </div>
        <div class="overview-card" data-for="uniques-card">
          <div class="ovc-head">UNIQUES CARRIED</div>
          <div class="muted small">✓ Steadfast Protection +Def</div>
          <div class="muted small">✓ Gladiator's Armor +Def</div>
          <div class="muted small">✓ Numina +Regen/+Recovery</div>
          <div class="muted small">✓ Performance Shifter +End</div>
        </div>
        <div class="accolades-card" data-for="accolades-card">
          <div class="ovc-head">ACCOLADES <span class="acc-count">2/28</span></div>
          <div class="muted small">☑ Freedom Phalanx Reserve <b>+10% HP</b></div>
          <div class="muted small">☑ Task Force Commander <b>+5% HP</b></div>
          <div class="muted small">☐ Portal Jockey <b>+5% HP · +5 End</b> ⓘ</div>
          <div class="muted small" style="opacity:.45">☐ Born In Battle — villain-side only</div>
          <div class="muted small">👁 Preview all — your numbers with every accolade in hand</div>
        </div>
      </div>

      <div class="add-powers-row" data-tm="addrow" data-for="powers-list">
        <label>Add from Super Strength <select disabled><option>+ add power…</option></select></label>
        <label>Add from Willpower <select disabled><option>+ add power…</option></select></label>
        <label>Add from Fighting <select disabled><option>+ add power…</option></select></label>
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

    <section class="panel" data-for="gamelog">
      <h2 data-tm="gamelog-head">📜 Play Log <span class="muted small">— insights from your game sessions</span></h2>
      <div class="gl-cards" data-tm="gl-body">
        <div class="tm-set-row"><b>Last session · 2h 10m · Bruiser Brawlwell</b>
          <span class="muted small">Levelled 22 → 24 · haul: 2 rare recipes, 41 salvage —
            appraised: keep 2, craft 1, sell the rest</span></div>
        <div class="tm-set-row"><b>This week</b>
          <span class="muted small">3 characters played · busiest evening: Thursday</span></div>
      </div>
    </section>
    </div>

    <div class="tm-rail">
    <section class="panel" data-for="stats">
      <h2 data-tm="stats-head">Stats <span class="muted small">(toggles/autos + enhancements + set bonuses)</span></h2>
      <div class="cap-chips">
        <span class="chip cap-def">Defense soft cap 45%</span>
        <span class="chip cap-res">Resistance hard cap 90%</span>
      </div>
      <label class="incarnate-toggle" data-tm="inc-label"><input type="checkbox" data-for="incarnate-peak-toggle" disabled> Include incarnates (peak)</label>
      <label class="incarnate-toggle"><input type="checkbox" disabled> Include accolades + amplifiers</label>
      <label class="incarnate-toggle" data-tm="sup-label"><input type="checkbox" data-for="suppression-toggle" disabled> In-combat view (suppression)</label>
      <h3>Defense <span class="muted small">soft cap 45%</span></h3>
      <div class="bars" data-for="defense-bars">
        <div class="bar-row"><span class="bar-label">Melee</span><div class="bar-track"><div class="bar-fill def" style="width:92%"></div></div><span class="bar-val">41.3%</span></div>
        <div class="bar-row"><span class="bar-label">Ranged</span><div class="bar-track"><div class="bar-fill def" style="width:80%"></div></div><span class="bar-val">36.2% <span class="over">⚔ 31.9%</span></span></div>
        <div class="bar-row"><span class="bar-label">AoE</span><div class="bar-track"><div class="bar-fill def" style="width:67%"></div></div><span class="bar-val">30.1%</span></div>
      </div>
      <h3 data-tm="res-head">Resistance <span class="muted small" data-for="res-cap-label">hard cap 90%</span></h3>
      <div class="bars">
        <div class="bar-row"><span class="bar-label">S/L</span><div class="bar-track"><div class="bar-fill res capped" style="width:100%"></div></div><span class="bar-val capped">90%</span></div>
        <div class="bar-row"><span class="bar-label">Energy</span><div class="bar-track"><div class="bar-fill res" style="width:51%"></div></div><span class="bar-val">46.2%</span></div>
        <div class="bar-row"><span class="bar-label">Psionic</span><div class="bar-track"><div class="bar-fill res" style="width:35%"></div></div><span class="bar-val">31.8%</span></div>
      </div>
      <h3>Other</h3>
      <div class="other">
        <div class="o-row"><span>Recharge (global)</span><span>+72.5%</span></div>
        <div class="o-row"><span>Recovery</span><span>+25% <span class="muted small">= 3.12 end/s</span></span></div>
        <div class="o-row"><span>Max HP <span class="aoe-tag">CAP</span></span><span>+21.4% <span class="muted small">= 3212 HP</span></span></div>
      </div>
      <div data-for="offense-section">
        <h3 data-tm="offense-head">Offense <span class="muted small">damage / debuffs / buffs</span></h3>
        <div class="offense">
          <div class="o-row"><span>Single-target DPS</span><span>187</span></div>
          <div class="o-row"><span>AoE throughput</span><span>412 dmg / 10s</span></div>
          <div class="o-row"><span>AoE alpha</span><span>498</span></div>
        </div>
        <div class="offense" data-tm="atk-table" data-for="offense-stats">
          <div class="o-row"><span><b>Top attack</b> (damage / animation)</span><span>121.4</span></div>
          <div class="o-row"><span>Knockout Blow</span><span class="muted small">243 dmg · 2.0s · 25s rech · 121.4 DPA</span></div>
          <div class="o-row"><span>Haymaker</span><span class="muted small">98 dmg · 1.2s · 8s rech · 81.7 DPA</span></div>
          <div class="o-row"><span>Foot Stomp <span class="aoe-tag">AoE</span></span><span class="muted small">86 dmg · 2.1s · 20s rech · 41.0 DPA</span></div>
        </div>
        <p class="muted small" data-tm="support-note">A support set, controller or Mastermind grows
          this panel: per-pet damage, enemy debuffs (base, per application), and what your buffs
          hand allies.</p>
      </div>
      <div class="validation" data-for="validation">✓ Legal build — nothing here breaks the game's rules.</div>
    </section>

    <section class="panel">
      <h2>AI Assistant</h2>
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
    </section>
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
  </div>

  <div class="modal tm-modal" data-for="modal" data-tm-overlay="picker" style="display:none">
    <div class="modal-box" data-tm="modal-box">
      <div class="modal-head"><strong>Knockout Blow — choose an enhancement</strong><button type="button">✕</button></div>
      <p class="muted small">Only sets this power can actually take are offered — it accepts Melee Damage sets.</p>
      <input placeholder="Filter sets…" disabled>
      <div class="modal-sets">
        <div class="tm-set-row"><b>Superior Unrelenting Fury</b> <span class="muted small">Brute ATO · 6 pieces · +regeneration proc, strong build-wide bonuses</span></div>
        <div class="tm-set-row"><b>Hecatomb</b> <span class="muted small">Very rare · 6 pieces · big recharge and damage bonuses</span></div>
        <div class="tm-set-row"><b>Kinetic Combat</b> <span class="muted small">4 pieces · prized for smashing/lethal defense</span></div>
        <div class="tm-set-row"><b>Crushing Impact</b> <span class="muted small">5 pieces · accuracy and recharge bonuses</span></div>
      </div>
    </div>
  </div>

  <div class="modal tm-modal" data-tm-overlay="targets" style="display:none">
    <div class="modal-box" data-tm="targets-box">
      <div class="modal-head"><strong>Customize build targets</strong><button type="button">✕</button></div>
      <p class="muted small">Anything you set here outranks the preset — it is what the optimizer chases first.</p>
      <div class="tm-set-row"><b>Melee defense — 45%</b> <span class="muted small">your ask · reached 41.3% so far</span></div>
      <div class="tm-set-row"><b>Smashing/Lethal resistance — 90%</b> <span class="muted small">your ask · reached, at your cap ✓</span></div>
      <div class="tm-set-row"><b>Recharge — +70%</b> <span class="muted small">your ask · reached +72.5% ✓</span></div>
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
      <div class="tm-set-row"><b>Health</b> <span class="muted small">one slot moved out, to Knockout Blow</span></div>
      <div class="tm-set-row"><b>What it bought</b> <span class="muted small">+4.2% melee defense · +10% recharge · same endurance</span></div>
      <p class="muted small">⬇ Export as .mbd &nbsp;·&nbsp; Keep it &nbsp;·&nbsp; ↺ Reset to imported</p>
    </div>
  </div>

  <div class="modal tm-modal tm-journey" data-tm-overlay="journey" style="display:none">
    <div class="modal-box" data-tm="journey-box">
      <div class="modal-head"><strong>🗺️ The Leveling Journey — Bruiser Brawlwell</strong><button type="button">✕</button></div>
      <div class="tm-road">
        <span class="tm-stop">1</span><span class="tm-stop">8</span><span class="tm-stop">15</span>
        <span class="tm-stop here">★22</span><span class="tm-stop">30</span><span class="tm-stop">38</span>
        <span class="tm-stop">44</span><span class="tm-stop">50</span>
      </div>
      <div class="tm-set-row"><b>Level 22 — your next stop</b>
        <span class="muted small">Pick: Knockout Blow · a new enhancement slot arrives at 23 ·
          zones that fit: Talos Island (20–27), Independence Port (20–30) — enemies there run even
          with you · Citadel's Task Force opens at 25.</span></div>
      <p class="muted small">Hero · Vigilante · Rogue · Villain · 🌀 Flashback — a preview of other routes; changes nothing.</p>
    </div>
  </div>

  <div class="modal tm-modal" data-tm-overlay="bugreport" style="display:none">
    <div class="modal-box" data-tm="bug-box">
      <div class="modal-head"><strong>🐞 Report a bug</strong><button type="button">✕</button></div>
      <p class="muted small">App 0.12.28 · model v36 · Homecoming 2026.1.1242 — filled in for you.</p>
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
function _mockShowScene(scene) {
  if (!_mockEl) return;
  const entry = scene === "entry";
  _mockEl.querySelectorAll(".tour-mock-screen").forEach(sc => {
    sc.style.display = (sc.dataset.tmScreen === (entry ? "entry" : "build")) ? "" : "none";
  });
  const grid = _mockEl.querySelector(".tm-main");
  if (grid) grid.classList.toggle("tm-has-info", scene === "info");
  // Exactly one overlay (the ⓘ column, a chooser, the Journey, the report
  // form...) is up at a time: the one whose data-tm-overlay names this scene.
  _mockEl.querySelectorAll("[data-tm-overlay]").forEach(ov => {
    ov.style.display = (ov.dataset.tmOverlay === scene) ? "" : "none";
  });
}

const TOUR_CHAPTERS = {
  start:     "Getting started",
  build:     "Choosing your character",
  powers:    "Powers and slots",
  stats:     "Reading your numbers",
  solve:     "Letting it build for you",
  extras:    "The other tools",
  header:    "Saving, updates and help",
};

// One line per section for the chooser. Deliberately a separate map from
// TOUR_CHAPTERS: the audit parses that block to know which chapters exist, and
// turning it into objects would break the thing that keeps this honest.
const TOUR_CHAPTER_BLURB = {
  start:  "The opening screen and what each of the five ways in actually does.",
  build:  "Archetype, powersets, and the two choices that steer everything: Content and Role.",
  powers: "Taking powers, spending your 67 slots, and locking what you have already decided.",
  stats:  "Reading the bars, the cap lines, and the second number that appears in combat.",
  solve:  "Letting it work out the slotting, and how to read what it gives you back.",
  extras: "The Leveling Journey, the enhancement converter, and the Play Log.",
  header: "Saving, alignment, updates, and reporting something that looks wrong.",
};

// `target`  - the element this step explains (id selector).
// `absent`  - what to say when that element is not on screen right now.
// `spine`   - true = part of the short first-run tour.
const TOUR_STEPS = [
  // ── Getting started ────────────────────────────────────────────────────────
  { chapter: "start", target: "#entry-overlay", spine: true, anchor: "[data-tm=entry-box]",
    title: "Five ways in",
    body: "Everything starts here, and which card you pick decides how much you "
        + "have to type: two build a character from nothing, two read one you "
        + "already have, and one resumes earlier work.\n\n"
        + "A rule of thumb: new to the game, take Start a new character. Know "
        + "exactly what you want at 50, take Build a new level 50. Already playing "
        + "the character, import it instead -- a plan is worth more when it is "
        + "built around what you really own. You can come back to this screen any "
        + "time.",
    absent: "This is the first screen you see when the app opens. Reach it again "
          + "with the ↺ button in the header." },
  { chapter: "start", target: "#entry-continue",
    title: "Continue where you left off",
    body: "Levelling a character is weeks of real play, so the app keeps the whole "
        + "plan on your machine: powers, slotting, levelling progress, locks and "
        + "targets. This card lists every character you have saved and reopens one "
        + "exactly where you stopped.\n\n"
        + "You rarely need to save by hand -- the app saves quietly in the "
        + "background as you work, and a small note in the header tells you when "
        + "it has.",
    absent: "Appears on the opening screen once you have saved at least one character." },
  { chapter: "start", target: "#entry-scratch",
    title: "Start a new character",
    body: "For a character that does not exist yet. If you are not sure what to "
        + "roll, this is the one: you answer a few questions about how you like to "
        + "play and it suggests archetypes that fit, with reasons.\n\n"
        + "From there it walks the whole road on the game's real schedule -- a "
        + "power on even levels, slots on odd ones, pools from level 4, epics at "
        + "35 -- so at every level you know what to pick and where to put it.",
    absent: "One of the cards on the opening screen." },
  { chapter: "start", target: "#entry-respec",
    title: "Build a new level 50",
    body: "You already know what you want to play and you want the finished "
        + "article: every power, every slot, epic pool and incarnates, ready to "
        + "respec into.\n\n"
        + "Tell it the archetype and your two powersets and it does the rest, "
        + "aimed at your Content and Role -- both explained later in this tour. "
        + "Anything it produces, you can still adjust by hand.",
    absent: "One of the cards on the opening screen." },
  { chapter: "start", target: "#entry-mids",
    title: "Import from Mids Reborn",
    body: "Already have a build in Mids? Load the .mbd file and the app reads it "
        + "and tells you what it thinks of it first -- what is strong, what is "
        + "loose -- before changing anything.\n\n"
        + "From there it can improve the slotting while keeping the sets you have "
        + "already paid for, and export the result back out as a .mbd that Mids "
        + "can open. Your file is never touched.",
    absent: "One of the cards on the opening screen." },
  { chapter: "start", target: "#entry-ingame",
    title: "Import a character you actually play",
    body: "The character straight from the game. Type /build_save_file in the "
        + "game's chat box; Homecoming writes a small text file, and the app finds "
        + "those saves by itself -- you just pick the character from a list.\n\n"
        + "This is the most honest starting point there is: the plan is built "
        + "around exactly the powers and enhancements you really have, and the "
        + "Preserve setting (covered in the Powers section) keeps the sets you "
        + "have already paid for.",
    absent: "One of the cards on the opening screen." },

  // ── Choosing your character ────────────────────────────────────────────────
  { chapter: "build", target: "#setup", spine: true, anchor: "[data-tm=setup-head]", side: "right",
    title: "The Build panel",
    body: "Your character's identity lives here: archetype, primary and secondary "
        + "powersets, pools and epic. Change anything and everything below it -- "
        + "the power list, the slots, the numbers -- updates to match.\n\n"
        + "As in the Powers section, the examples in this chapter follow a Brute "
        + "built as a damage dealer, so the details stay consistent as you read.",
    absent: "The 'Build' panel, once you are past the opening screen." },
  { chapter: "build", target: "#sel-archetype", side: "right",
    title: "Archetype first",
    body: "Everything else follows from this one choice. The archetype decides "
        + "which powersets exist for you, the resistance cap your bars are "
        + "measured against, which roles make sense, and how strongly your powers "
        + "land at all.\n\n"
        + "Our example Brute is melee damage with a 90% resistance cap -- pick a "
        + "Defender instead and the whole panel reshapes around buffs and debuffs.",
    absent: "The first dropdown in the Build panel." },
  { chapter: "build", target: "#sel-primary", side: "right",
    title: "Primary and secondary",
    body: "The primary set is your archetype's main job and the secondary is its "
        + "supporting half. On the Brute that means attacks first and armour "
        + "second; a Defender is the reverse -- buffs and debuffs first, blasts "
        + "second.\n\n"
        + "Both lists are already filtered to your archetype, so everything "
        + "offered is a choice the game will allow -- including the special cases, "
        + "like Kheldian form powers living inside their own sets.",
    absent: "The primary and secondary dropdowns in the Build panel." },
  { chapter: "build", target: "#pool-selectors", side: "right",
    title: "Power pools",
    body: "Pools add what your sets lack: travel, extra toughness like Tough and "
        + "Weave, utility. The game allows four at most, opening from level 4, and "
        + "only one of the five origin pools -- Sorcery, Experimentation, Force of "
        + "Will, Gadgetry, Utility Belt.\n\n"
        + "You do not have to fill these by hand: the Build action later in this "
        + "tour picks pools too, following exactly the rules the game enforces.",
    absent: "The pool dropdowns in the Build panel." },
  { chapter: "build", target: "#sel-epic", side: "right",
    title: "Epic pools",
    body: "Epic and patron pools open at level 35 and reach outside your "
        + "archetype's normal toolkit -- armour for a damage dealer, or a ranged "
        + "attack for our melee Brute.\n\n"
        + "The list is per archetype and tiered like the game's own, and the "
        + "special cases are honoured: Kheldians have no epic at all, so none is "
        + "ever offered.",
    absent: "The epic dropdown in the Build panel." },
  { chapter: "build", target: "#preset-content", side: "right",
    title: "Content: where you play",
    body: "General play, task forces, incarnate trials, farming, PvP. This sets "
        + "what the build has to survive and what it needs to deliver -- an "
        + "incarnate trial hits far harder than street sweeping, and a fire farmer "
        + "cares mostly about a single damage type.\n\n"
        + "It is not cosmetic: Content changes the targets the optimizer chases, "
        + "so the same character solved for different content comes out slotted "
        + "differently.",
    absent: "A dropdown in the Build panel, next to Role." },
  { chapter: "build", target: "#preset-role", side: "right",
    title: "Role: what you are there to do",
    body: "Damage, tanking, support, control, healing. The optimizer maximises "
        + "your role's output rather than a generic score.\n\n"
        + "That matters most for support and control: a Defender is judged on how "
        + "much its buffs and debuffs actually change a fight -- their size times "
        + "how often they are up -- not on how well it survives alone. The aim is "
        + "characters that get noticed as contributors.",
    absent: "A dropdown in the Build panel, next to Content." },
  { chapter: "build", target: "#custom-targets-btn", scene: "targets", anchor: "[data-tm=targets-box]", side: "right", slim: true,
    title: "Your own targets",
    body: "This is what Customize build targets opens. Each row is an ask -- "
        + "defence by type or position, resistance, recharge, recovery and more "
        + "-- and anything you set outranks the preset: it is what the optimizer "
        + "chases first. The save line at the bottom keeps the whole set as a "
        + "named preset for your other characters.\n\n"
        + "The Ranged row shows the honest answer to an ask that cannot be "
        + "reached: how close it can get, and which unpicked power would close "
        + "the gap. Your ask is honored either way -- the tool states what a "
        + "goal costs rather than quietly overriding it.",
    absent: "A button on the build summary card, labelled 'Customize build targets'." },

  // -- Powers and slots ------------------------------------------------------
  { chapter: "powers", target: "#builder", spine: true, anchor: "[data-tm=builder-head]", side: "left",
    title: "Powers and slots",
    body: "This is where a build is actually built. Every power you have taken "
        + "gets a card, and the card shows the enhancement slots in it.\n\n"
        + "The examples in this tour describe a Brute built as a damage dealer, "
        + "so the set names and numbers stay consistent as you read. Your own "
        + "character will show its own powers; everything works the same way." },
  { chapter: "powers", target: "#powers-list", anchor: "[data-tm=addrow]", side: "left",
    title: "Adding a power",
    body: "Below the cards, every powerset you own has its own Add from… menu. "
        + "Pick a power and its card appears above, ready to slot.\n\n"
        + "Only legal picks are ever offered -- right tier, right level, real "
        + "prerequisites -- so you cannot assemble a character the game would "
        + "reject. Dropped something by accident? Undo, at the top of the panel." },
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
        + "That budget is what makes build planning interesting. Six slots in one "
        + "attack are six not spread across three others, and at 67 of 67 the "
        + "only way to improve anything is to take a slot from somewhere else." },
  { chapter: "powers", target: "#power-info", scene: "info", side: "left",
    title: "What the ⓘ opens",
    body: "Click a power's name or its ⓘ and this panel opens beside the build "
        + "-- exactly here, on the right. It shows what the power does, its "
        + "endurance cost and recharge, the enhancement categories it accepts, "
        + "and what is slotted in it right now.\n\n"
        + "It is also where enhancement details live: click a slotted piece and "
        + "you get the piece, its set, and the set's bonuses -- the same numbers "
        + "the game uses." },
  { chapter: "powers", target: "#power-info", scene: "info", side: "left", key: "proc-why",
    anchor: "[data-tm=trade-note]", slim: true,
    title: "Why these enhancements",
    body: "When the optimizer chooses damage procs over a full set -- or seats a "
        + "-resistance or Force Feedback proc -- this panel says why, in one "
        + "sentence with both numbers: what the procs add every use, and what "
        + "the replaced pieces would have added instead. The numbers come from "
        + "the same engine that prices your build; nothing is re-estimated for "
        + "the explanation.\n\n"
        + "Prefer the set after reading the trade? Slot it back and lock the "
        + "power -- a re-solve honors the lock exactly and rebalances the rest "
        + "of the build around your choice." },
  { chapter: "powers", target: "#modal", scene: "picker", anchor: "[data-tm=modal-box]", side: "right", slim: true,
    title: "Filling a slot, and why the list is short",
    body: "Click a slot and this chooser opens, offering the sets that power can "
        + "actually take, not every set in the game. An armour toggle offers "
        + "defence and resistance sets, an attack offers damage sets, because "
        + "each power declares which categories it accepts.\n\n"
        + "Right-click a slot to empty it. Minus and plus on the card move slots "
        + "between powers, so a slot sitting in something over-invested can go "
        + "where it earns more." },
  { chapter: "powers", target: "#builder", anchor: "[data-tm=card1-sets]", side: "bottom",
    title: "Set bonuses: why six of one set beats six good pieces",
    body: "Slotting several pieces of the SAME set earns set bonuses -- recharge, "
        + "defence, health -- on top of what each piece does. That is why a card "
        + "reads something like \"Superior Unrelenting Fury x6\" with a Full set tag.\n\n"
        + "You will also see Partial set, Frankenslot (pieces from different sets "
        + "picked purely for raw numbers), and Global mules: a power taken mainly "
        + "to carry one always-on unique, such as Luck of the Gambler's recharge." },
  { chapter: "powers", target: "#builder", anchor: "[data-tm=card2-lock]", side: "left",
    title: "The padlock: open or closed",
    body: "Open means the optimizer may re-slot that power. Closed means hands "
        + "off, and it means it absolutely: a locked power returns from a "
        + "re-solve exactly as you left it, down to individual enhancements, and "
        + "an empty slot inside it stays empty.\n\n"
        + "Lock what you have already decided. You own those sets in game and do "
        + "not want a plan that assumes you re-buy them; you want a particular "
        + "proc in a particular power; or you are asking what would change if "
        + "this part stayed fixed." },
  { chapter: "powers", target: "#builder", anchor: "[data-tm=card2]", side: "left",
    title: "When a lock is costing you",
    body: "Locks constrain the answer. A locked power that is slotted poorly caps "
        + "how good everything around it can be, and a lower result afterwards is "
        + "the solver being honest rather than failing.\n\n"
        + "So when a target you used to reach suddenly falls short, check your "
        + "locks first. Unlock, re-solve, compare." },
  { chapter: "powers", target: "#preserve-toggle", anchor: "[data-tm=preserve-label]", side: "right",
    title: "Preserve my IO sets",
    body: "The broad-stroke alternative to locking, and usually the right choice "
        + "for a character you actually play: keep every set you have already "
        + "paid for, and let the optimizer improve only the generic enhancements "
        + "and the empty slots around them." },
  { chapter: "powers", target: "#builder", anchor: "[data-tm=response]", side: "right",
    title: "Chasing a number, in practice",
    body: "Say you want 45% ranged defence on that Brute. Set it under Customize "
        + "build targets, then Solve. The optimizer works out which sets in which "
        + "powers get you there, because defence at that level comes mostly from "
        + "set BONUSES rather than from the defence powers themselves.\n\n"
        + "If it cannot reach the number it says so, tells you how close it got, "
        + "and names unpicked powers that would close the gap and roughly what "
        + "each would add. That is your decision point: take the extra power, "
        + "accept the lower number, or unlock whatever is in the way." },

  // ── Reading your numbers ───────────────────────────────────────────────────
  { chapter: "stats", target: "#stats", spine: true, anchor: "[data-tm=stats-head]", side: "right",
    title: "Your numbers, live",
    body: "Defence, resistance, recharge, recovery, damage. These update as you "
        + "change anything, and they include your enhancements, your set bonuses, "
        + "and the toggles and auto powers you would actually be running.\n\n"
        + "Every figure is computed from the game's own data. If the app and the "
        + "game ever disagree, the game is right -- and that is a bug worth "
        + "reporting with the 🐞 button.",
    absent: "The 'Stats' panel, once a character is loaded." },
  { chapter: "stats", target: "#defense-bars", diagram: "statBar", side: "right",
    title: "How to read a bar",
    body: "Every bar tells you three things at once, marked on the drawing above: "
        + "the filled part is what you have, and the END of the bar is the number "
        + "that matters -- each bar is drawn against its own target, so a full "
        + "bar means done. The exact figure is printed too, so you never have to "
        + "estimate from a picture.\n\n"
        + "For defence the bar runs to 45% -- the soft cap, where most incoming "
        + "attacks start missing you. If a row also shows a ⚔ figure, part of that "
        + "defence switches off in combat, and the ⚔ number is the one to plan "
        + "around, because it is what you have when it counts.",
    absent: "The Defence rows in the Stats panel." },
  { chapter: "stats", target: "#res-cap-label", anchor: "[data-tm=res-head]", side: "right",
    title: "Caps are per archetype",
    body: "Resistance stops counting at your archetype's cap: 90% for Tankers and "
        + "Brutes, 85% for Kheldians and the Arachnos archetypes, 75% for everyone "
        + "else.\n\n"
        + "Points past the line are wasted, which is why the app will not chase "
        + "them: a slot buying resistance past the cap is a slot better spent "
        + "anywhere else on the build.",
    absent: "Shown beside the Resistance heading in the Stats panel." },
  { chapter: "stats", target: "#suppression-toggle", anchor: "[data-tm=sup-label]", side: "right",
    title: "The in-combat view",
    body: "Powers like Stealth lose part of their defence the moment you attack, "
        + "get hit, or take damage -- the game calls this suppression. This switch "
        + "shows all your totals as they are mid-fight instead of at rest.\n\n"
        + "It is a display choice only: Solve optimizes the same numbers either "
        + "way. Turn it on when you want the honest in-combat picture, which is "
        + "usually the one worth planning around.",
    absent: "A checkbox under the stat bars, once a character is loaded." },
  { chapter: "stats", target: "#incarnate-peak-toggle", anchor: "[data-tm=inc-label]", side: "right",
    title: "What-if switches",
    body: "Two more switches live beside the in-combat view. Include incarnates "
        + "folds your Destiny and Hybrid buffs into the totals, matching the "
        + "fully-buffed display Mids users know. The amplifiers switch adds the "
        + "three buyable amplifier buffs and permanent accolades.\n\n"
        + "Useful for answering 'what am I really at during a fight' -- just "
        + "remember which switches are on before comparing numbers with someone "
        + "else's build.",
    absent: "Checkboxes under the stat bars, once a character is loaded." },
  { chapter: "stats", target: "#offense-section", anchor: "[data-tm=offense-head]", side: "right",
    title: "The output half",
    body: "Below the defensive bars, the panel speaks your role's language: a "
        + "damage dealer sees single-target and area damage throughput, a "
        + "Mastermind sees pet damage, a support character sees what its debuffs "
        + "and buffs are actually worth in a fight.\n\n"
        + "This is the side the optimizer is maximising for your role -- so when "
        + "you want to know whether a change helped, look here, not only at the "
        + "defensive bars.",
    absent: "The Offense section of the Stats panel, once a character is loaded." },
  { chapter: "stats", target: "#offense-stats", anchor: "[data-tm=atk-table]", side: "right",
    title: "Every attack, priced",
    body: "Under the headline numbers, each attack you own is priced: its damage, "
        + "how long its animation locks you in place, its recharge, and DPA -- "
        + "damage per second of animation, the honest measure of an attack's "
        + "worth. A huge hit with a slow animation can price out worse than a "
        + "quick one, and this table is where that shows.\n\n"
        + "The Top attack line names the best of them; a good attack chain is "
        + "built from the top of this table down." },
  { chapter: "stats", target: "#offense-stats", anchor: "[data-tm=support-note]", side: "right",
    title: "When you play support",
    body: "This example is a damage Brute, so the panel stays lean. Play a "
        + "support set, a controller or a Mastermind and it grows: per-pet "
        + "damage, your enemy debuffs at their base value per application, and "
        + "what your buffs hand allies.\n\n"
        + "Pet damage is honest about hit chance: pets are scored with their "
        + "real chance to hit at their own level. Lower-tier henchmen fight "
        + "higher-level enemies and miss more -- which is exactly why ToHit "
        + "buffs like Tactics and accuracy slotted in the summon power "
        + "visibly raise pet damage.\n\n"
        + "Those numbers are the invisible half of the game made visible -- and "
        + "for a support role they are exactly what the optimizer maximises: "
        + "size times how often they are up." },
  { chapter: "stats", target: "#overview-card", side: "left",
    title: "Build Vitals: the report card",
    body: "The summary band under your powers starts with the report card: "
        + "defence and resistance by type AND position in one grid -- marked "
        + "where a number is done -- with the build's pulse underneath: "
        + "recharge, recovery, hit points, and damage per second single-target "
        + "and area.\n\n"
        + "It is the same truth as the Stats panel, folded small enough to read "
        + "at a glance while you work the slots above it." },
  { chapter: "stats", target: "#bonuses-card", side: "left",
    title: "Set bonuses, totted up",
    body: "Every set bonus currently active, aggregated -- ×3 of one, ×2 of "
        + "another -- so you can see where your recharge and defence actually "
        + "come from.\n\n"
        + "When a number on the report card needs to move, look here first: "
        + "this list says which bonuses you are stacking, and what disappears "
        + "if you swap a set out." },
  { chapter: "stats", target: "#uniques-card", side: "left",
    title: "Uniques carried",
    body: "The one-slot wonders: globals that give a build-wide effect from a "
        + "single slot -- a +defense IO here, a +recovery proc there. This card "
        + "lists every one you carry, so you always know what you already have.\n\n"
        + "A solve parks them in low-priority powers where they cost nothing -- "
        + "the Global mules pattern from the Powers section." },
  { chapter: "stats", target: "#accolades-card", side: "left",
    title: "Accolades",
    body: "Accolades are permanent bonus powers the game awards for collections "
        + "of badges -- real hit points and endurance. Tick the ones your "
        + "character has earned and your totals recalculate; the greyed rows "
        + "belong to the other side, which is exactly why flipping Hero/Villain "
        + "moves your numbers.\n\n"
        + "The ⓘ on each row tells you how to earn it in game, and Preview all "
        + "shows your numbers with every accolade in hand -- a ceiling worth "
        + "knowing about." },

  // ── Letting it build for you ───────────────────────────────────────────────
  { chapter: "solve", target: "#solve-btn", spine: true, side: "right",
    title: "Solve the slotting",
    body: "This works out the best enhancement layout it can find for the powers "
        + "you have taken, aimed at your Content, Role and any targets you set. It "
        + "is real arithmetic over the game's actual numbers, not a template, and "
        + "it can take up to a minute on a complicated build. It will say so while "
        + "it works.\n\n"
        + "Two promises it always keeps: it never changes which powers you chose, "
        + "and it obeys your padlocks and the Preserve setting from the Powers "
        + "section.",
    absent: "The solve button, once a character is loaded." },
  { chapter: "solve", target: "#gen-btn", side: "right",
    title: "Or have it pick the powers too",
    body: "Build goes further than Solve: it chooses which powers to take as well "
        + "as how to slot them -- pools, epic and incarnates included -- following "
        + "the same rules the game enforces: four pools at most, one origin pool, "
        + "real prerequisites and level availability.\n\n"
        + "Where a certified champion build exists for your combination it starts "
        + "from there rather than from nothing. And whatever it produces, you can "
        + "still change anything by hand afterwards.",
    absent: "The build button, near the solve controls." },
  { chapter: "solve", target: "#ai-response", side: "right",
    title: "Achieved versus target",
    body: "After a solve you get the result in plain terms: what you asked for, "
        + "what it reached, and what it changed. If something fell short it does "
        + "not go quiet about it -- it names the unpicked powers on your character "
        + "that would close the gap and roughly what each would add.\n\n"
        + "If nothing on your character supplies a stat at all, it says that "
        + "plainly too. A goal you cannot reach is worth knowing about rather than "
        + "chasing.",
    absent: "Appears below the build once you have run a solve." },
  { chapter: "solve", target: "#changes-btn", scene: "changes", anchor: "[data-tm=changes-box]", side: "right", slim: true,
    title: "What changed?",
    body: "For imported characters, the What changed? button opens this window: "
        + "one line per power -- what was slotted, what it is now -- and a "
        + "closing line saying what the changes bought you, so you can judge the "
        + "trade before committing to anything in game.\n\n"
        + "It is a report, not a confirmation: open and close it as often as you "
        + "like. From here you can also export the result as a .mbd, keep it, or "
        + "put everything back with Reset.",
    absent: "Appears after you solve an imported build." },
  { chapter: "solve", target: "#reset-btn", side: "right",
    title: "Reset to imported",
    body: "Puts an imported build back exactly as it came in, so you can try a "
        + "different goal, role or options without re-importing.\n\n"
        + "Reset means reset: custom targets and similar settings attached to the "
        + "build are cleared with it. When there is something like that to lose, "
        + "the app tells you first and cancelling keeps it -- nothing is dropped "
        + "silently.",
    absent: "Appears once you have imported a build." },
  { chapter: "solve", target: "#tray-out", side: "left",
    title: "Your in-game trays",
    body: "After a solve, the plan lands the way you will actually play it: a "
        + "suggested layout for the game's power trays -- the attack chain "
        + "together where your fingers live, toggles and autos parked out of "
        + "the click path.\n\n"
        + "Copy it into the game once and muscle memory does the rest.",
    absent: "Appears under the powers once a solve has produced a layout." },
  { chapter: "solve", target: "#order-out", side: "left",
    title: "The respec order",
    body: "The respec screen in game asks you to re-place every pick, in order, "
        + "from level 1 up. This is that order, one line per pick, so at the "
        + "trainer you just read down the list instead of reconstructing it "
        + "from memory.\n\n"
        + "It appears once there is a plan worth respeccing into.",
    absent: "Appears under the powers when a plan differs from what you imported." },
  { chapter: "solve", target: "#validation", side: "right",
    title: "The rules check",
    body: "Anything the game would not allow shows up here: too many pools, an "
        + "enhancement in a power that cannot take it, a power taken before its "
        + "level, a second copy of a unique. If this is clear, the build is legal "
        + "-- you can respec into it in game exactly as shown.\n\n"
        + "The checks are the game's own rules, which is also why the app "
        + "sometimes refuses a request: it will not plan something the game would "
        + "reject.",
    absent: "Appears when something about the build needs attention." },

  // ── The other tools ────────────────────────────────────────────────────────
  { chapter: "extras", target: "#journey-btn", spine: true, scene: "journey", anchor: "[data-tm=journey-box]", side: "bottom",
    title: "The Leveling Journey",
    body: "Click the 🗺️ button in the header and this opens: your whole 1-to-50 "
        + "as a road. Every marker is a level, and the ★ is where your character "
        + "stands. The open stop reads like the one shown -- that level's pick, "
        + "when the next slot arrives, the zones that fit you and how their "
        + "enemies will feel, and which task forces have just opened.\n\n"
        + "It follows the game's real schedule, special careers included -- an "
        + "Arachnos character gets the mandatory level-24 respec walked properly, "
        + "branch and all. The alignment switch inside is a preview of where "
        + "somebody on another side would level; it changes nothing about your "
        + "character.",
    absent: "The 🗺️ button in the header, once a character is loaded." },
  { chapter: "extras", target: "#conv-tool", anchor: "[data-tm=conv-body]", side: "left",
    title: "Enhancement Converter",
    body: "This is the converter planner, and the highlighted example is what an "
        + "answer looks like: the piece to start from, the conversions to run, "
        + "and the price -- so 'expensive' becomes a shopping list.\n\n"
        + "Ask it the two money questions. 'How do I get this enhancement "
        + "cheaply?' returns a path like the one shown. 'Is this drop worth "
        + "anything?' reads drops pasted straight from the game and answers "
        + "keep, craft, or sell for each. Its paths only use conversions the "
        + "game actually allows -- there is no cheap-pool-to-purple shortcut, "
        + "because the game won't allow one.",
    absent: "The Converter panel." },
  { chapter: "extras", target: "#gamelog", anchor: "[data-tm=gl-body]", side: "left",
    title: "Play Log",
    body: "Turn it on and this is what it builds from your own chat logs, on "
        + "your machine -- the highlighted cards are the shape of it: each "
        + "session with who you played and what you levelled, and your haul "
        + "appraised for you, so 'worth keeping?' is already answered.\n\n"
        + "It is entirely optional and off until you turn it on. And turning it "
        + "on shares nothing: reading your logs locally and sharing anything "
        + "anywhere are separate choices, each asked separately.",
    absent: "The 📜 Play Log panel, shown when you enable it." },

  // ── Saving, updates and help ───────────────────────────────────────────────
  { chapter: "header", target: "#masthead", diagram: "headerRow", anchor: "[data-tm=compass]", side: "bottom",
    title: "The header's small buttons",
    body: "Nine small buttons share the header, and the drawing above names the "
        + "pair people mix up: the two circular arrows. ⟳ checks for updates; ↺ "
        + "leaves this character and returns to the opening screen.\n\n"
        + "Left to right: the 🗺️ Journey, this tour's 🧭 compass, 💾 save, the ❓ "
        + "user guide, 🐞 report a bug, 🏆 submit a champion, ⟳ updates, 🦸/🦹 "
        + "alignment, and ↺ to load another character. The rest of this section "
        + "takes the important ones in turn.",
    absent: "The bar across the top of the app." },

  { chapter: "header", target: "#save-btn", spine: true,
    title: "Saving",
    body: "Keeps the character's plan and levelling progress on your machine so "
        + "you can resume any time -- powers, slots, locks, targets, everything.\n\n"
        + "You will rarely need it: the app also saves quietly in the background "
        + "as you work, and a small note appears in the header when it does. The "
        + "button is for peace of mind before you close.",
    absent: "The 💾 button in the header." },
  { chapter: "header", target: "#start-over-btn",
    title: "Load another character",
    body: "Returns to the opening screen -- the five cards from the start of this "
        + "tour -- to continue another saved character, start a new one, or "
        + "import.\n\n"
        + "Nothing is lost on the way out: the character you are leaving has been "
        + "saved in the background as you worked.",
    absent: "The ↺ button at the right end of the header." },
  { chapter: "header", target: "#alignment-btn",
    title: "Hero or Villain",
    body: "Switches the whole app between blue and red. It is not only a colour "
        + "scheme: accolades are side-specific in game, so switching also swaps "
        + "which accolades your character is assumed to have and recalculates your "
        + "totals. If your numbers move slightly when you flip it, that is "
        + "correct; flip it back and they return.\n\n"
        + "Do not confuse it with the Leveling Journey's own alignment switch -- "
        + "that one is a preview of somebody else's route through the game and "
        + "changes nothing at all.",
    absent: "The 🦸 / 🦹 button in the header." },
  { chapter: "header", target: "#help-btn",
    title: "The user guide",
    body: "The full guide as a PDF: everything this tour covers and more, plus "
        + "the release notes for every version. It is stored with the app, so it "
        + "always matches the version you are actually running.",
    absent: "The ❓ button in the header." },
  { chapter: "header", target: "#champ-btn",
    title: "Submit a champion",
    body: "Think your build beats the shipped champion for its archetype, "
        + "powersets and role? This saves it as a champion candidate. Every "
        + "candidate is re-scored with the same math, and if yours genuinely wins "
        + "it becomes the shipped champion in a future update -- with credit to "
        + "you.\n\n"
        + "Champions are how the optimizer starts smart: the best certified build "
        + "for each combination ships with the app.",
    absent: "The 🏆 button in the header." },
  { chapter: "header", target: "#update-btn",
    title: "Updates",
    body: "Checks whether a newer version exists -- it compares version numbers "
        + "with the project's release page and sends nothing else. Nothing is "
        + "ever downloaded or installed without you saying so.\n\n"
        + "On first run the app asks once whether to check automatically at "
        + "startup; say no and this button is the only check that ever runs.",
    absent: "The ⟳ button in the header." },
  { chapter: "header", target: "#bug-btn", spine: true, scene: "bugreport", anchor: "[data-tm=bug-box]", side: "right", slim: true,
    title: "Something wrong? Say so",
    body: "This is the form behind the 🐞 button, and it goes straight to the "
        + "developer with no account needed. The hard part of a good report -- "
        + "your version, model and game-data numbers -- is filled in for you; "
        + "you describe what happened, and the checkbox attaches the build "
        + "itself so the problem can be reproduced. Nothing leaves your machine "
        + "until you press Send.\n\n"
        + "That is the tour. Every panel has a ? that brings you back to just "
        + "that part, and the 🧭 compass holds the rest, whenever you want it.",
    absent: "The 🐞 button in the header." },
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
    __tmScene: s.scene || (s.chapter === "start" ? "entry" : "build"),
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
  _mockShowScene(live[0].scene || (live[0].chapter === "start" ? "entry" : "build"));
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
      if (step && step.__tmScene) _mockShowScene(step.__tmScene);
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
