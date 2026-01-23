
# Copilot instructions for life-coach

Purpose
- Provide compact, actionable guidance so an AI coding agent becomes productive in this repository quickly.

Quick context
- This repository is a product-spec/design workspace for the "Life Coach" MVP. Primary files live under `docs/` and describe product goals, Raspberry Pi deployment, hardware mappings, and expected deliverables.
- Key documents: [docs/PRD.md](docs/PRD.md) and [docs/概要设计-MVP.md](docs/概要设计-MVP.md).

What an agent should assume
- This repo is documentation-first. Do not add runtime code, CI, or scaffolding without explicit consent from the human owner.
- Preserve Chinese headings and section labels when editing; you may add an English summary below a Chinese heading if it clarifies intent.

Primary tasks for agents (concrete)
- Improve clarity, structure, and acceptance criteria in `docs/PRD.md` (product goals, P0/P1 features, performance/security targets).
- Extract implementation notes, hardware mappings, and deployment checklist from `docs/概要设计-MVP.md` (Raspberry Pi specifics).
- Consolidate TODOs and open questions into `docs/proposals/` or inline "Open Questions" sections in the same docs.

Project-specific patterns and examples (use these in edits)
- Hardware & deployment: `docs/概要设计-MVP.md` expects deployables such as `deploy.sh`, `start.sh`, `stop.sh`, GPIO wiring diagrams, and model packages (Whisper Tiny INT4, Phi-2 INT4). When documenting deployment, reference the expected GPIO pins: GPIO2 (record), GPIO3 (AI trigger), GPIO17 (red LED), GPIO18 (green LED).
- Storage and paths: default Pi path `/home/pi/LifeCoach/` (概要设计) and PRD path `我的文档/Life Coach/对话记录` are canonical references for examples and instructions.
- Interfaces & services: follow the local-function-call style described (e.g., `audio_record.start()`, `asr.transcribe_stream()`, `ai.process_text()`). Document changes to these interfaces in prose and example signatures, not code.
- Data policies: emphasize "本地存储优先、本地加密" (AES-128) and backup rules (daily 03:00, retain 2 backups) when editing privacy/security sections.

Actionable editing rules (project-specific)
- Edit only Markdown files unless explicitly asked. Small scripts referenced in docs (e.g., `deploy.sh`) may be proposed but DO NOT create them without approval—create a `docs/proposals/` markdown first.
- When updating Chinese text: keep original Chinese headings unchanged; append a one-line English summary if helpful. Preserve numbered lists and P0/P1 priority markings.
- When extracting acceptance criteria, include measurable targets from `docs/PRD.md` (startup ≤3s, ASR latency ≤1s/句话 for lightweight model, AI process ≤5–10s for short dialogs) and note any platform caveats (Raspberry Pi targets have relaxed timings in `概要设计-MVP.md`).

What NOT to do
- Do not add application scaffolding (`src/`, `package.json`, systemd services) or CI workflows without explicit instruction.

Integration and external dependencies (document-only)
- The docs reference optional external model sources (Hugging Face ARM mirrors) and system packages (PyTorch ARM, FFmpeg). If work requires downloading models or creating scripts, note the mirror URLs and propose an offline-packaging step in `docs/proposals/`.

Examples of helpful edits (concrete suggestions)
- In `docs/PRD.md`: convert performance rows into a short "Acceptance Criteria" section with bullet checks and reference numbers.
- In `docs/概要设计-MVP.md`: add a one-page "Deployment Checklist" listing required deliverables (`deploy.sh`, model ZIPs, `start.sh`, hardware wiring diagram, `GPIO` mapping) and include exact file/path names to deliver.
- Create `docs/proposals/deploy-scripts.md` when proposing scripts—include expected commands and `systemd` unit examples, but only create actual scripts after owner approval.

If you need to add code or automation
- First, create a short proposal in `docs/proposals/` describing the file(s) to add, exact contents, and a brief justification. Wait for user approval before creating scripts or binaries.

Feedback loop and commit rules
- After substantive edits, add a one-paragraph summary at the top of the modified file describing what changed and why. Use Git-friendly, single-line commit messages (e.g., "docs: clarify deployment checklist and GPIO mapping").
- When uncertain, ask one focused question per PR/commit (e.g., "Confirm GPIO pins: should record use GPIO2 or GPIO4?").

Contact the maintainer
- If unclear, ask the user a focused question before making structural changes.

— End of instructions —

Please review and tell me what to add or change.
