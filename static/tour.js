// ── THE GUIDED TOUR ──────────────────────────────────────────────────────────
// A self-paced walkthrough of every area of the app.
//
// THREE RULES THIS FILE IS BUILT AROUND (Joel, 2026-07-27):
//
//  1. IT NEVER TOUCHES YOUR WORK. Nothing in here writes to `build`, opens a
//     character, runs a solve, or changes a setting. It only points at things
//     and explains them. A tour that disturbs work in progress is worse than no
//     tour, so the engine simply has no code path that mutates app state. If a
//     step's subject is not on screen right now, it says when you would see it
//     instead of forcing the app into that state.
//
//  2. YOU SET THE PACE. Nothing advances on a timer. Next, Back, Esc, and a
//     visible position count, because people read at different speeds and a
//     walkthrough that moves on its own is a walkthrough nobody finishes.
//
//  3. IT MUST STAY TRUE AS THE APP CHANGES. Every step names the element it
//     describes by id, and tools/audit_tour.py fails the build if any of those
//     ids stops existing. Rename a control and the audit tells you which step
//     went stale, in the same run that renamed it. That is the whole mechanism
//     keeping this honest: documentation that cannot silently rot.
//
// ADDING OR CHANGING A STEP: edit TOUR_STEPS below, then run
//   python tools/audit_tour.py
// It checks every target resolves and every chapter is reachable.

const TOUR_CHAPTERS = {
  start:     "Getting started",
  build:     "Choosing your character",
  powers:    "Powers and slots",
  stats:     "Reading your numbers",
  solve:     "Letting it build for you",
  extras:    "The other tools",
  header:    "Saving, updates and help",
};

// `target`  - the element this step explains (id selector).
// `absent`  - what to say when that element is not on screen right now.
// `spine`   - true = part of the short first-run tour.
const TOUR_STEPS = [
  // ── Getting started ────────────────────────────────────────────────────────
  { chapter: "start", target: "#entry-overlay", spine: true,
    title: "Five ways in",
    body: "Everything starts here. Which card you pick decides how much you have "
        + "to type: some build a character from nothing, others read one you "
        + "already play. You can come back to this screen any time.",
    absent: "This is the first screen you see when the app opens. Reach it again "
          + "with the ↺ button in the header." },
  { chapter: "start", target: "#entry-continue",
    title: "Continue where you left off",
    body: "Levelling a character is weeks of real play, so the app saves your plan "
        + "and your progress. This card lists everything you have saved and picks "
        + "up exactly where you stopped.",
    absent: "Appears on the opening screen once you have saved at least one character." },
  { chapter: "start", target: "#entry-scratch",
    title: "Start a new character",
    body: "For a character that does not exist yet. If you are not sure what to "
        + "roll, this is the one to pick: you answer a few questions about how you "
        + "like to play and it suggests archetypes that fit, then walks every "
        + "level from 1 to 50.",
    absent: "One of the cards on the opening screen." },
  { chapter: "start", target: "#entry-respec",
    title: "Build a new level 50",
    body: "You already know what you want to play and you want the finished "
        + "article: powers, slotting, caps, epic pool and incarnates. Tell it the "
        + "archetype and your two sets and it does the rest.",
    absent: "One of the cards on the opening screen." },
  { chapter: "start", target: "#entry-mids",
    title: "Import from Mids Reborn",
    body: "Already have a build in Mids? Load the .mbd file and the app reads it, "
        + "tells you what it thinks, and can improve the slotting while keeping "
        + "the sets you have already paid for.",
    absent: "One of the cards on the opening screen." },
  { chapter: "start", target: "#entry-ingame",
    title: "Import a character you actually play",
    body: "Type /build_save_file in the game's chat box, then use this card. The "
        + "app finds your Homecoming saves by itself and imports the character you "
        + "pick, so the plan is built around what you really have.",
    absent: "One of the cards on the opening screen." },

  // ── Choosing your character ────────────────────────────────────────────────
  { chapter: "build", target: "#setup", spine: true,
    title: "The Build panel",
    body: "Your character's identity lives here: archetype, primary and secondary "
        + "sets, pools and epic. Change anything and everything below updates.",
    absent: "The 'Build' panel, once you are past the opening screen." },
  { chapter: "build", target: "#sel-archetype",
    title: "Archetype first",
    body: "Everything else follows from this. The powerset choices, the resistance "
        + "cap your bars are measured against, and which roles make sense are all "
        + "decided by the archetype.",
    absent: "The first dropdown in the Build panel." },
  { chapter: "build", target: "#preset-content",
    title: "Content: where you play",
    body: "General play, task forces, incarnate trials, farming, PvP. This sets "
        + "what the build has to survive and what it needs to deliver. It is not "
        + "cosmetic: it changes what the optimizer aims for.",
    absent: "A dropdown in the Build panel, next to Role." },
  { chapter: "build", target: "#preset-role",
    title: "Role: what you are there to do",
    body: "Damage, tanking, support, control, healing. The optimizer maximises "
        + "your role's output rather than a generic score, so a support character "
        + "is judged on how much its buffs and debuffs change a fight, not on how "
        + "well it survives alone.",
    absent: "A dropdown in the Build panel, next to Content." },
  { chapter: "build", target: "#custom-targets-btn",
    title: "Your own targets",
    body: "If you have specific numbers in mind, set them here: defence by type or "
        + "position, resistance, recharge, recovery. What you set is what the "
        + "optimizer chases, and you can save your settings as a named preset to "
        + "reuse. If a target cannot be reached it tells you, and names the powers "
        + "that would help.",
    absent: "A button on the build summary card, labelled 'Customize build targets'." },

  // ── Powers and slots ───────────────────────────────────────────────────────
  { chapter: "powers", target: "#builder", spine: true,
    title: "Powers and slots",
    body: "Every power you have taken, with its enhancement slots. Click a power to "
        + "take or drop it. The game gives you 67 placeable slots across a whole "
        + "career and the app enforces that limit, so what you see here is "
        + "something you could really build.",
    absent: "The 'Powers & Slots' panel, once a character is loaded." },
  { chapter: "powers", target: "#slot-tally",
    title: "Your slot budget",
    body: "How many of your 67 slots are spent. This is the constraint that makes "
        + "build planning interesting: every slot here is one not somewhere else.",
    absent: "Shown in the Powers & Slots panel once a character is loaded." },
  { chapter: "powers", target: "#builder",
    title: "The padlock on each power",
    body: "🔓 open means the optimizer may re-slot that power. 🔒 closed means hands "
        + "off, and it means it absolutely: a locked power comes back from a "
        + "re-solve exactly as you left it, down to individual enhancements, and "
        + "an empty slot inside it stays empty.\n\n"
        + "Lock the things you have already decided, then let the optimizer work "
        + "around them. If a target suddenly cannot be reached, your locks are the "
        + "first thing to check, because a locked power that is slotted poorly "
        + "limits everything else.",
    absent: "Each power card carries a padlock button once a character is loaded." },
  { chapter: "powers", target: "#preserve-toggle",
    title: "Preserve my IO sets",
    body: "The broad-stroke version of locking. It keeps the sets you have already "
        + "invested in and only re-slots generic enhancements and empty slots. Use "
        + "this when you want to improve a real character without being told to "
        + "re-buy everything.",
    absent: "A checkbox near the solve controls." },

  // ── Reading your numbers ───────────────────────────────────────────────────
  { chapter: "stats", target: "#stats", spine: true,
    title: "Your numbers, live",
    body: "Defence, resistance, recharge, recovery, damage. These update as you "
        + "change anything, and they include your enhancements, set bonuses, and "
        + "the toggles and auto powers you actually run.",
    absent: "The 'Stats' panel, once a character is loaded." },
  { chapter: "stats", target: "#defense-bars",
    title: "How to read a bar",
    body: "The filled part is what you have. The marked line is the number that "
        + "matters: 45% for defence, where most attacks start missing you. The "
        + "figure is printed too, so you never have to guess from the picture.\n\n"
        + "If a defence row shows a second '⚔' number, that power switches off when "
        + "you attack. The ⚔ figure is the one to plan around, because it is what "
        + "you have when it counts.",
    absent: "The Defence rows in the Stats panel." },
  { chapter: "stats", target: "#res-cap-label",
    title: "Caps are per archetype",
    body: "Resistance stops counting at your archetype's cap: 90% for Tankers and "
        + "Brutes, 85% for Kheldians and the Arachnos archetypes, 75% for everyone "
        + "else. Points past the line are wasted, which is why the app will not "
        + "chase them.",
    absent: "Shown beside the Resistance heading in the Stats panel." },

  // ── Letting it build for you ───────────────────────────────────────────────
  { chapter: "solve", target: "#solve-btn", spine: true,
    title: "Solve the slotting",
    body: "This works out the best enhancement layout it can find for the powers "
        + "you have, aimed at your Content and Role. It is real arithmetic over the "
        + "game's actual numbers, not a template, and it can take up to a minute on "
        + "a complicated build. It will say so while it works.",
    absent: "The solve button, once a character is loaded." },
  { chapter: "solve", target: "#gen-btn",
    title: "Or have it pick the powers too",
    body: "Build goes further than Solve: it chooses which powers to take as well "
        + "as how to slot them, including pools, epic and incarnates.",
    absent: "The build button, near the solve controls." },
  { chapter: "solve", target: "#ai-response",
    title: "Achieved versus target",
    body: "After a solve you get the result in plain terms: what you asked for, "
        + "what it reached, and what it changed. If something fell short it does "
        + "not go quiet about it. It names the unpicked powers on your character "
        + "that would close the gap and roughly what each would add, and if nothing "
        + "would, it tells you the goal may not be reachable on this pairing.",
    absent: "Appears below the build once you have run a solve." },
  { chapter: "solve", target: "#validation",
    title: "The rules check",
    body: "Anything the game would not allow shows up here: too many pools, an "
        + "enhancement that cannot go where you put it, a power taken too early. "
        + "If this is clear, the build is legal.",
    absent: "Appears when something about the build needs attention." },

  // ── The other tools ────────────────────────────────────────────────────────
  { chapter: "extras", target: "#journey-btn", spine: true,
    title: "The Leveling Journey",
    body: "A map of the whole road from 1 to 50: what you pick at each level, when "
        + "slots arrive, which zones suit you, and the badges and task forces "
        + "within reach. It has its own Hero / Vigilante / Rogue / Villain switch, "
        + "which is only a preview of where somebody on that side would level. It "
        + "changes nothing about your character.",
    absent: "The 🗺️ button in the header, once a character is loaded." },
  { chapter: "extras", target: "#conv-tool",
    title: "Enhancement Converter",
    body: "Answers two questions. 'How do I get this enhancement cheaply' gives you "
        + "a concrete path with the converter and merit cost. 'Is this drop worth "
        + "anything' takes your drops pasted straight from the game and tells you "
        + "keep, craft, or sell.",
    absent: "The Converter panel." },
  { chapter: "extras", target: "#gamelog",
    title: "Play Log",
    body: "Reads your own game chat logs, on your machine, and turns them into a "
        + "picture of what you have actually been doing. Entirely optional and off "
        + "until you turn it on.",
    absent: "The 📜 Play Log panel, shown when you enable it." },

  // ── Saving, updates and help ───────────────────────────────────────────────
  { chapter: "header", target: "#save-btn", spine: true,
    title: "Saving",
    body: "Keeps the character's plan and levelling progress on your machine so you "
        + "can resume. It also saves quietly in the background as you work.",
    absent: "The save button in the header." },
  { chapter: "header", target: "#alignment-btn",
    title: "Hero or Villain",
    body: "Switches the whole app between blue and red. It is not only a colour "
        + "scheme: accolades are side-specific in game, so switching also swaps "
        + "which accolades your character is assumed to have and recalculates your "
        + "totals. If your numbers move slightly when you flip it, that is correct. "
        + "Flip it back and they return.",
    absent: "The 🦸 / 🦹 button in the header." },
  { chapter: "header", target: "#update-btn",
    title: "Updates",
    body: "Checks whether a newer version exists. Nothing is ever downloaded or "
        + "installed without you saying so.",
    absent: "The ⟳ button in the header." },
  { chapter: "header", target: "#bug-btn", spine: true,
    title: "Something wrong? Say so",
    body: "Sends a report straight to the developer with no account needed. Your "
        + "version and character are attached automatically, and you can include "
        + "the build itself. Nothing leaves your machine until you press Send.\n\n"
        + "That is the tour. Every panel has a 'Need help?' link that brings you "
        + "back to just that part, whenever you want it.",
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

// Being in the DOM and being POINTABLE are different things. The builder panels
// sit BEHIND the entry overlay: visible by every CSS test, yet completely
// covered. Highlighting those produced the meaningless slivers in Joel's walk.
// driver.js positions whatever we hand it -- deciding what is worth pointing at
// in THIS app's layout is still our job.
function _tourPointable(el) {
  if (!_tourVisible(el)) return false;
  const r = el.getBoundingClientRect();
  if (r.width < 40 || r.height < 20) return false;
  const vw = window.innerWidth || document.documentElement.clientWidth || 0;
  const vh = window.innerHeight || document.documentElement.clientHeight || 0;
  if (vw && vh && (r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw)) return false;
  const cx = Math.min(Math.max(r.left + r.width / 2, 1), (vw || r.right) - 1);
  const cy = Math.min(Math.max(r.top + r.height / 2, 1), (vh || r.bottom) - 1);
  const hit = document.elementFromPoint(cx, cy);
  if (!hit) return true;                       // cannot hit-test: do not block
  if (hit.closest && hit.closest(".driver-popover, .driver-overlay")) return true;
  return el.contains(hit) || hit.contains(el);
}

// "Are we on the opening screen?" is a VISIBILITY question, not a pointability
// one, and conflating them was a real bug: #entry-cards computes to zero WIDTH,
// so asking _tourPointable about it answered "no" while the overlay was plainly
// on screen, and the tour walked the builder spine instead of the entry cards.
// Ask about the overlay, and only whether it is showing.
const _onEntryScreen = () => {
  const ov = document.getElementById("entry-overlay");
  return !!ov && !ov.classList.contains("hidden") && _tourVisible(ov);
};

// The closing card of the entry-screen tour: says where the rest of it lives, so
// nobody is left wondering whether that was all of it.
const _TOUR_HANDOFF = {
  chapter: "start", target: "#entry-cards",
  title: "That is the starting screen",
  body: "Pick whichever card fits and the builder opens behind this. From there, "
      + "every panel has its own \"Need help?\" link that explains that panel the "
      + "same way. Nothing you have seen here changed anything.",
  absent: "Pick a card above to open the builder. Every panel there has its own "
        + "\"Need help?\" link.",
};

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

// Turn one catalogue entry into a driver.js step. A step with NO `element` is
// rendered by driver.js as a centred card, which is exactly what we want for
// something the user cannot see yet -- so "not on screen" needs no special case.
function _tourToDriverStep(s) {
  const el = s.target ? document.querySelector(s.target) : null;
  const pointable = _tourPointable(el);
  const desc = _tourHtml(pointable ? s.body : (s.absent || s.body))
    + (pointable ? "" :
      `<p class="tour-note">Not on screen yet. Pick a starting point first, and every
        panel then has its own <b>Need help?</b> link that reopens the tour right there.</p>`);
  const step = { popover: { title: s.title, description: desc } };
  if (pointable) step.element = el;
  return step;
}

window.endTour = function () {
  if (_driver && _driver.isActive()) _driver.destroy();
  _driver = null;
};

// chapter: undefined = the context-aware first tour; a chapter key = that
// section only; "all" = every step.
window.startTour = function (chapter) {
  if (!(window.driver && window.driver.js && window.driver.js.driver)) {
    console.warn("[tour] driver.js did not load; tour unavailable");
    return;
  }
  const onEntry = _onEntryScreen();
  const chosen = chapter === "all" ? TOUR_STEPS.slice()
    : chapter ? TOUR_STEPS.filter(s => s.chapter === chapter)
      : onEntry ? TOUR_STEPS.filter(s => s.chapter === "start").concat(_TOUR_HANDOFF)
        : TOUR_STEPS.filter(s => s.spine);
  if (!chosen.length) return;

  endTour();
  _driver = window.driver.js.driver({
    steps: chosen.map(_tourToDriverStep),
    showProgress: true,
    progressText: "{{current}} of {{total}}",
    nextBtnText: "Next →",
    prevBtnText: "← Back",
    doneBtnText: "Done",
    smoothScroll: true,
    stagePadding: 6,
    stageRadius: 8,
    allowClose: true,               // Esc and the ✕ both leave, deliberately
    // NOT "close": a stray click outside used to end the tour and leave the user
    // "in limbo" (Joel's walk). Advancing is recoverable; exiting silently is not.
    overlayClickBehavior: "nextStep",
    // The tour is READ-ONLY. Blocking interaction with the highlighted control
    // means a click during the tour cannot change the user's build by accident.
    disableActiveInteraction: true,
    onHighlighted: () => {
      // Reaching the last step counts as having seen it: stop offering.
      if (_driver && !_driver.hasNextStep()) _tourMarkFinished();
    },
  });
  _driver.drive();
};

// The first-run OFFER. One line, dismissible, and dismissing it only stops the
// OFFER - the tour stays reachable from every 'Need help?' link forever.
window.maybeOfferTour = function () {
  if (_tourFinished() || _tourLater()) return;
  if (document.querySelector(".tour-offer")) return;   // called from init AND showEntry
  const host = document.getElementById("entry-cards");
  if (!host || !_tourVisible(host)) return;
  const bar = document.createElement("div");
  bar.className = "tour-offer";
  // Say what it IS and what it costs. Joel's walk: "I'm not sure why I would
  // even choose 'not now' - it's not obvious this is a tour." If the offer does
  // not explain itself, declining it is a coin flip.
  bar.innerHTML =
    `<span class="tour-offer-ico">🧭</span>
     <span class="tour-offer-txt"><b>First time here?</b> Take a two minute guided tour —
       it points at each part of the app and explains what it does. Nothing is changed
       or built along the way, and you can leave at any point.</span>
     <button onclick="this.closest('.tour-offer').remove(); startTour();">Start the tour</button>
     <button class="secondary" onclick="_tourMarkLater(); this.closest('.tour-offer').remove();"
       title="Hides it for now. It will offer again next time you open the app, and every panel has a 'Need help?' link.">Maybe later</button>`;
  host.parentNode.insertBefore(bar, host);
};

// A 'Need help?' link for a panel, wired to that panel's chapter.
window.tourHelpLink = function (chapter) {
  return `<button class="tour-help" onclick="startTour('${chapter}')" `
       + `title="Show me how this section works">Need help?</button>`;
};
