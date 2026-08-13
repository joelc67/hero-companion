# Hero Companion — agent instructions (any AI assistant)

Hero Companion is a City of Heroes: Homecoming build planner: a Flask backend
(`server/`), a vanilla-JS single-page app (`static/`), game data extracted from
the live client (`data/`), and an ILP-based build optimizer with a certified
champion roster (`benchmarks/`).

## Orient with the knowledge graph FIRST

This repo has a prebuilt knowledge graph. For ANY question about the codebase,
run these before grepping or reading raw source:

    graphify query "<your question>"
    graphify path "<thing A>" "<thing B>"     # how two things relate
    graphify explain "<concept>"              # one focused concept

They return a small scoped subgraph — far cheaper than reading files. After
changing code, run `graphify update .` to keep the graph current.

## The rulebook

`CLAUDE.md` in this directory is the project's standing rulebook: design
doctrines, hard-won traps, and the current state. It is long — do not read it
all up front. Read the section relevant to what you touch, and treat its
rulings as binding.

## Hard rules for any agent in this repo

- Do NOT commit, push, tag, or publish releases unless Joel explicitly asks.
- Do NOT start long optimization/certification runs; those are scheduled
  deliberately and have their own protocol in CLAUDE.md.
- Never rewrite `data/powers.json` wholesale (additive patch tools only).
- The game client is the source of truth over any parse or guess; when the
  tool and the game disagree, the game is right.
- Test against scratch copies, never real saves in `saves/`.
- Keep replies short: outcome first, details only on request.
