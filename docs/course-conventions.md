# Course Conventions (for authors and contributors)

This file is the contract every lesson, lab and exercise in this repo follows.
If you contribute, read it once. If you are a learner, you can skip it — but
it explains *why* every lesson looks the same (predictability lowers cognitive load).

---

## 1. Teaching model

Every piece of content follows the same learning loop, grounded in what the
learning-science literature agrees works for adults learning technical skills:

| Step | What the learner does | Why it works |
|---|---|---|
| **Situate** | Reads a realistic ticket from a teammate at Kestrel Pay | Problems before solutions create a "need to know" |
| **Predict** | Answers 2–3 questions *before* reading | Pre-testing primes attention, even when wrong |
| **Learn** | Reads short sections: concept → diagram → code → pitfall | Dual coding (words + visuals), worked examples |
| **Do** | Runs, breaks and extends real code in the lab | Active practice beats re-reading |
| **Check** | Self-quiz with hidden answers | Retrieval practice |
| **Explain** | Explains the idea in their own words | The Feynman technique exposes gaps |
| **Review** | Answers questions from earlier modules | Spaced repetition / interleaving |
| **Go deeper** | Curated free resources, ranked | Depth on demand, not upfront |

## 2. The story: Kestrel Pay

The learner is the **new AI engineer at Kestrel Pay**, a fictional mid-size
fintech (cards, payments, ~800 employees). Over the course they take two
prototypes to production:

- **Track A — `fraud-service`** (classic ML): a fraud-scoring model for card
  transactions. Data: `datasets/fraud/` (synthetic, generated locally).
- **Track B — `docs-assistant`** (LLM app): an internal assistant that answers
  employee and customer questions from the company handbook with citations.
  Data: `datasets/handbook/`.

Recurring characters (always refer to them by name or with they/them):

| Name | Role | Typical ask |
|---|---|---|
| **Maya** | Engineering manager (your manager) | Scope, deadlines, "is it ready?" |
| **Diego** | SRE / platform lead | Latency, on-call, Kubernetes, SLOs |
| **Priya** | Security & compliance lead | Auth, PII, prompt injection, audits |
| **Sam** | Data scientist who built the prototypes | Notebooks, "it works on my machine" |
| **Lena** | Head of Customer Support (business owner of docs-assistant) | Answer quality, cost |
| **Omar** | Risk analyst (business owner of fraud-service) | False positives, thresholds |

Each lesson opens with a short message from one of them (`📨 The situation`).

## 3. Lesson template

Titles use ':' as the separator: `# Lesson N.L: Title`, `# Module N: Title`,
`# 🛠 Lab N: Title`, `# Module N quiz: Title`.

Every lesson file is `modules/NN-name/LL-lesson-slug.md` and uses this skeleton
(sections may be omitted only if truly not applicable):

```markdown
# Lesson N.L: Title

> ⏱ ~45 min · 🎚 Level: Core | Advanced · 🧰 Needs: lesson N.(L-1)

<!-- breadcrumb -->
[Course home](../../README.md) › [Module N](README.md) › Lesson N.L

## 📨 The situation
> **From: Name (Role)**
> Short in-story message (3–8 lines) that creates the need for this lesson.

## 🎯 By the end you can
- Measurable objectives with action verbs (explain, implement, choose, measure, debug)

## 🤔 Predict first
1. Question (answer it in your head or a notebook before reading)

## 1. First concept
Plain-language explanation → analogy → diagram (mermaid) → minimal code.

> 💡 **Production tip:** ...
> ⚠️ **Common mistake:** ...
> 🔎 **Under the hood:** ... (optional deeper detail)

## 🧪 Try it
Concrete hands-on steps against the module lab, with expected output.

## 🏭 In the real world
A short real-world framing or case (no invented quotes of real companies).

## ✅ Check yourself
<details>
<summary>Q1. ...</summary>

Answer + why.
</details>

## 💬 Explain it back
One prompt that asks the learner to explain the idea to someone else.

## 🔑 Key takeaways
- 3–6 bullets

## 📚 Go deeper (free)
| | Resource | Why read it | Time |
|---|---|---|---|
| ⭐ | Title (link) | ... | 20 min |
| 🔍 | ... | Optional depth | ... |

---
⬅️ [Previous](...) · ➡️ [Next](...)
```

## 4. Module template

Every module folder `modules/NN-name/` contains:

```
README.md          overview, story, objectives, lesson table, lab, checkpoint, self-assessment
LL-*.md            lessons
lab/               runnable, tested code + lab/README.md (step-by-step: each step is a
                   "### Step N · Title" heading under "## 📋 Steps" or a "## Part X · …";
                   an optional step ends its title with "(optional…)")
quiz.md            end-of-module quiz (10–15 Qs, mixed with 2–3 spaced-review Qs from earlier modules)
cheatsheet.md      one-page summary to review later
```

Every quiz question uses one format, so tools (and the Real Env platform) can read it. A
spaced-review question carries 🔁 and, in parentheses, the module(s) it reviews, optionally
with topics (`*(Module 2, retrieval; Module 3, caching)*`); a short title is optional:

```markdown
**13.** 🔁 *(Module 2)* *Optional title.* The question…

<details><summary>Answer</summary>

The answer, with a link to the lesson.

</details>
```

Each quiz states its pass mark once, in words, and annotates that line with the number of
points needed to move on, as an HTML comment GitHub doesn't show. The Real Env platform reads
it as the performance review's pass mark:

```markdown
**Scoring:** 13–15 → move on · 10–12 → re-read the lessons… <!-- pass: 13 -->
```

Module `README.md` must include:
1. 🧭 a "where you are" course map (mermaid, current module highlighted)
2. 📨 the module story
3. 🎯 module objectives
4. 📖 lesson table (lesson, what you'll learn, time)
5. 🛠 the lab summary and **Definition of Done** checklist
6. 📊 a self-assessment rubric (1 = never heard of it … 4 = could teach it)
7. 🎤 "Interview corner": 3–5 system-design questions this module prepares you for

### Lab checks

A lab may have a `lab.yaml` next to its README listing commands that verify steps, for the
Real Env CLI (`realenv check lab-N`). Only steps a command can verify are listed; the rest
are done on trust. Each check names its step by ID and runs from the lab folder as an
argument list (never a shell string):

```yaml
lab: lab-1
checks:
  - step: lab-1-step-4
    run: [uv, run, pytest]
    output: 32 passed        # text the output must contain
    timeout: 300             # seconds; default 60
    # exit: 0                # expected exit code; the default
```

A step with several checks is verified when all of them pass. When a lab's expected output
changes (say, a new test), update its check in the same change.

### Stable IDs

Every module, lesson, lab, lab step, predict-first question, check-yourself question,
explain-it-back prompt and quiz question carries a stable ID as an HTML comment, which GitHub
doesn't show. Learner progress on the Real Env platform is keyed by these IDs, so they outlive
edits, reordering and translations. (Interview-corner questions, rubric rows, "Try it",
"Break it" and "Extend it" have no IDs yet.)

| What | Where the ID goes | Shape | Example |
|---|---|---|---|
| Module, lesson, lab | Line after the `#` title | `m-M`, `l-M-L`, `lab-M` | `<!-- id: l-2-5 -->` |
| Predict-first question | End of its `1. …` line | `p-M-L-N` | `1. Which finds "T+2" better…? <!-- id: p-2-5-1 -->` |
| Check-yourself question | End of its `<summary>` | `c-M-L-N` | `<summary>Q1. … <!-- id: c-2-5-1 --></summary>` |
| Explain it back | Line after its heading | `e-M-L` | `<!-- id: e-2-5 -->` |
| Quiz question | End of its `**N.**` line | `q-M-N` | `**13.** … <!-- id: q-2-13 -->` |
| Lab step | Line after its heading | `lab-M-step-N` | `<!-- id: lab-1-step-3 -->` |

M, L and N are numbers without leading zeros. Rules:

- **An ID is a name, not a position.** It never changes, even when the item moves to another
  place in the same lesson, quiz or lab, so its number can drift from the visible numbering.
- **Never reuse an ID.** `tools/issued-ids.txt` lists every ID ever issued. A new item takes
  the next number for its kind and place that isn't listed (even if it sits between two
  others) and is added to the file. A removed item's line becomes `<id> retired`.
- **Wording fixes keep the ID; a new question gets a new ID.** If an edit changes what the
  question asks or what the right answer is, retire the old ID and issue a new one, so
  nobody's history points at a question they never saw.
- An item that moves to another lesson or module is a new item there: new ID, old one retired.

`python3 tools/check_ids.py` checks all of this (and that items use the formats above, and that each translation keeps its original's IDs, see [Translations](#7-translations)); CI
runs it.

## 5. Code conventions (labs)

- Python **3.11+**, managed with **[uv](https://docs.astral.sh/uv/)**. Each lab has its own
  `pyproject.toml` and is runnable with `uv sync && uv run pytest`.
- Labs are **self-contained**: a lab never imports from another module's lab.
  When a later lab needs earlier code, it includes its own (evolved) copy.
  This lets a learner start any module without finishing the previous lab.
- Paths to shared data are resolved from the repo root:
  `REPO_ROOT = Path(__file__).resolve().parents[N]` or the `KESTREL_DATA_DIR` env var.
- Same package layout in every lab that has a service:

```
lab/
  pyproject.toml
  README.md
  src/kestrel_<name>/
    api/        # FastAPI routers, request/response schemas (HTTP only)
    domain/     # business logic, pure Python, no framework imports
    adapters/   # LLM, embeddings, vector store, model artifact, DB clients
    config.py   # pydantic-settings, env prefix KESTREL_
    main.py     # app factory: create_app()
  tests/
```

- Libraries (prefer these, so learners see the same tools across modules):
  FastAPI, pydantic v2, pydantic-settings, structlog, httpx, pytest, scikit-learn,
  numpy, pandas, mlflow, qdrant-client (in-memory mode), rank-bm25,
  sentence-transformers (optional), prometheus-client, opentelemetry-sdk.
- **Everything must run for free, offline, on a laptop CPU.**
  - LLM providers behind one interface (`adapters/llm.py`):
    - `fake` (default): deterministic, no network — used by tests and CI.
    - `ollama`: local models (`KESTREL_OLLAMA_MODEL`, default `qwen2.5:1.5b-instruct`).
    - `openai`: any OpenAI-compatible endpoint (`KESTREL_OPENAI_BASE_URL`, `KESTREL_OPENAI_API_KEY`).
  - Embeddings: `hash` (default, deterministic, no download) or
    `sentence-transformers` (`all-MiniLM-L6-v2`, optional extra).
  - Select with `KESTREL_LLM_PROVIDER` and `KESTREL_EMBEDDINGS_PROVIDER`.
- Tests must pass with **no network and no API keys** (`fake` + `hash` providers).
- Type hints everywhere; small functions; docstrings explain *why*, not *what*.
- Comments in code may say `# 📖 See lesson 2.4` to link code back to theory.

## 6. Writing style

- Second person ("you"), active voice, short paragraphs.
- Explain every acronym the first time it appears in a lesson.
- One idea per section. Prefer a table or diagram over a long paragraph.
- Use **mermaid** for diagrams (GitHub renders it natively).
- Numbers must be realistic and labelled as approximate when they vary by hardware.
- Never invent statistics, quotes or "case studies" attributed to real companies.
  Link to the real public write-up instead.
- Resources: free only, prefer primary sources (official docs, original papers,
  well-known practitioner blogs). Mark the one to read first with ⭐.
- Links: use the canonical URL. If unsure of an exact URL, link the project's
  home page rather than guessing a deep link.

## 7. Translations

Translated editions live under `i18n/<locale>/`, mirroring the repo's own paths file for file
(`i18n/es/modules/00-foundations/01-setup-your-workbench.md` translates
`modules/00-foundations/01-setup-your-workbench.md`). A translated file keeps everything that
isn't words: the ID comments, emoji, section numbers, `<details>` and code, comments included.
Only the structure words change, as each edition's README lists (Spanish:
[`i18n/es/README.md`](../i18n/es/README.md)).

- Each edition's `translated-from.yaml` names the English commit each file was translated
  from, so the platform can tell when a section goes stale.
- A first draft may be machine-assisted, but every translation is reviewed by a person in its
  PR before it is merged.
- An English edit that changes structure (adds a question, a step or a numbered section) needs
  the same change in each translation, or the translated module stops being published until
  it's updated. `tools/check_ids.py` checks each translated file has exactly its original's IDs.
