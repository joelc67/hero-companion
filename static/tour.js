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

// ── Engine ───────────────────────────────────────────────────────────────────
let _tourSteps = [], _tourAt = 0, _tourOpen = false;

const _tourSeen = () => {
  try { return localStorage.getItem("cohTourOffered") === "1"; } catch (e) { return false; }
};
const _tourMarkOffered = () => {
  try { localStorage.setItem("cohTourOffered", "1"); } catch (e) {}
};

function _tourVisible(el) {
  if (!el) return false;
  // Two traps here, both found by driving this in a real browser rather than
  // reasoning about it:
  //   - width>0 && height>0 is wrong: a flex/grid container can compute to zero
  //     WIDTH while being fully visible and full height (#entry-cards does), so
  //     the tour offer never appeared.
  //   - offsetParent !== null is wrong: it is ALWAYS null for position:fixed
  //     elements, so every modal and overlay read as invisible and lost its
  //     spotlight -- including the opening screen, the tour's own first step.
  // getClientRects() is empty for display:none and for detached nodes, which is
  // the question actually being asked.
  const cs = getComputedStyle(el);
  return cs.display !== "none" && cs.visibility !== "hidden"
      && el.getClientRects().length > 0;
}

function _tourEls() {
  let sh = document.getElementById("tour-shade");
  if (!sh) {
    sh = document.createElement("div"); sh.id = "tour-shade"; sh.className = "tour-shade";
    document.body.appendChild(sh);
    const tip = document.createElement("div"); tip.id = "tour-tip"; tip.className = "tour-tip";
    document.body.appendChild(tip);
    // Clicking the shade leaves the tour. Leaving is NOT a decision to never see
    // it again (Joel's rule) - the offer setting is untouched by this.
    sh.addEventListener("click", endTour);
  }
  return { shade: sh, tip: document.getElementById("tour-tip") };
}

function _tourPlace(step) {
  const { shade, tip } = _tourEls();
  const el = step.target ? document.querySelector(step.target) : null;
  const here = _tourVisible(el);
  // ON SCREEN and WORTH SPOTLIGHTING are different questions. A full-screen
  // overlay reports a rect covering everything (and #entry-overlay reports zero
  // width outright), and cutting a hole around the entire viewport communicates
  // nothing while looking broken. Those steps get a centred card and the normal
  // explanation -- the subject IS present, it just cannot be pointed AT.
  const r0 = here ? el.getBoundingClientRect() : null;
  const area = r0 ? r0.width * r0.height : 0;
  // Never trust the viewport to be reportable. Some embedded/headless browsers
  // return 0 for window.innerWidth, and dividing by that silently disabled every
  // spotlight in testing. If we cannot measure the screen, fall back to "has
  // area, so point at it" rather than to "point at nothing".
  const vw = window.innerWidth || document.documentElement.clientWidth || 0;
  const vh = window.innerHeight || document.documentElement.clientHeight || 0;
  const screen = vw * vh;
  const spot = here && area > 0 && (screen === 0 || area < screen * 0.7);
  const total = _tourSteps.length;
  const body = (here ? step.body : (step.absent || step.body))
    .split("\n\n").map(p => `<p>${escHtml(p)}</p>`).join("");
  tip.innerHTML =
    `<div class="tour-head"><b>${escHtml(step.title)}</b>
       <span class="muted small">${_tourAt + 1} of ${total}</span></div>
     ${body}
     ${here ? "" : `<p class="muted small">Not on screen right now, so there is nothing to point at yet.</p>`}
     <div class="tour-nav">
       <button class="secondary" onclick="endTour()">Close</button>
       <span class="tour-spacer"></span>
       <button class="secondary" onclick="tourStep(-1)"${_tourAt === 0 ? " disabled" : ""}>← Back</button>
       <button onclick="tourStep(1)">${_tourAt === total - 1 ? "Done" : "Next →"}</button>
     </div>`;

  if (spot) {
    el.scrollIntoView({ block: "center", behavior: "smooth" });
    const r = el.getBoundingClientRect(), pad = 6;
    shade.style.setProperty("--hx", `${r.left - pad}px`);
    shade.style.setProperty("--hy", `${r.top - pad}px`);
    shade.style.setProperty("--hw", `${r.width + pad * 2}px`);
    shade.style.setProperty("--hh", `${r.height + pad * 2}px`);
    shade.classList.add("tour-has-hole");
    // Put the card where it does not cover what it is describing.
    const below = r.bottom + 12, above = r.top - 12;
    const roomBelow = window.innerHeight - r.bottom;
    tip.style.left = `${Math.max(12, Math.min(r.left, window.innerWidth - 380))}px`;
    if (roomBelow > 220) { tip.style.top = `${below}px`; tip.style.bottom = "auto"; }
    else { tip.style.top = "auto"; tip.style.bottom = `${window.innerHeight - above}px`; }
  } else {
    shade.classList.remove("tour-has-hole");
    tip.style.left = "50%"; tip.style.top = "50%"; tip.style.bottom = "auto";
    tip.style.transform = "translate(-50%, -50%)";
  }
  if (spot) tip.style.transform = "none";
}

window.tourStep = function (delta) {
  const next = _tourAt + delta;
  if (next < 0) return;
  if (next >= _tourSteps.length) return endTour();
  _tourAt = next;
  _tourPlace(_tourSteps[_tourAt]);
};

window.endTour = function () {
  _tourOpen = false;
  const sh = document.getElementById("tour-shade"), tip = document.getElementById("tour-tip");
  if (sh) sh.remove();
  if (tip) tip.remove();
  document.removeEventListener("keydown", _tourKeys);
};

function _tourKeys(e) {
  if (!_tourOpen) return;
  if (e.key === "Escape") { e.preventDefault(); endTour(); }
  else if (e.key === "ArrowRight") tourStep(1);
  else if (e.key === "ArrowLeft") tourStep(-1);
}

// chapter: undefined = the short first-run tour; a chapter key = that section
// only; "all" = every step.
window.startTour = function (chapter) {
  _tourSteps = chapter === "all" ? TOUR_STEPS.slice()
    : chapter ? TOUR_STEPS.filter(s => s.chapter === chapter)
      : TOUR_STEPS.filter(s => s.spine);
  if (!_tourSteps.length) return;
  _tourAt = 0; _tourOpen = true;
  _tourMarkOffered();
  _tourEls();
  _tourPlace(_tourSteps[0]);
  document.addEventListener("keydown", _tourKeys);
};

// The first-run OFFER. One line, dismissible, and dismissing it only stops the
// OFFER - the tour stays reachable from every 'Need help?' link forever.
window.maybeOfferTour = function () {
  if (_tourSeen()) return;
  if (document.querySelector(".tour-offer")) return;   // called from init AND showEntry
  const host = document.getElementById("entry-cards");
  if (!host || !_tourVisible(host)) return;
  const bar = document.createElement("div");
  bar.className = "tour-offer";
  bar.innerHTML =
    `<span>New here? Take the two minute tour.</span>
     <button onclick="startTour(); this.parentNode.remove();">Show me around</button>
     <button class="secondary" onclick="_tourMarkOffered(); this.parentNode.remove();">No thanks</button>`;
  host.parentNode.insertBefore(bar, host);
};
window._tourMarkOffered = _tourMarkOffered;

// A 'Need help?' link for a panel, wired to that panel's chapter.
window.tourHelpLink = function (chapter) {
  return `<button class="tour-help" onclick="startTour('${chapter}')" `
       + `title="Show me how this section works">Need help?</button>`;
};
