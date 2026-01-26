
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

## Development workflow and debugging style

This section captures the maintainer's preferred development and debugging workflow based on actual working sessions.

### Problem diagnosis approach
**Always diagnose before fixing**: When a feature isn't working:
1. Read log output first (e.g., `journalctl -u lifecoach --no-pager -n 100 | grep ...`)
2. Read relevant source code to understand the issue (use `read_file`, `grep_search`)
3. Identify root cause (missing attributes, wrong data types, incorrect assumptions)
4. Only then propose a fix

Example from session: When OLED副屏 wasn't updating, checked logs → found `'LifeCoachApp' object has no attribute 'display_controller'` → read `__init__` → discovered correct name is `self.display` → fixed attribute reference.

### Incremental fixes with validation
**Fix one issue at a time, deploy immediately**:
- Fix a single, well-defined problem
- Deploy to target device (Raspberry Pi via `scp` + `systemctl restart`)
- Verify with logs or user testing before moving to next issue
- If fix reveals another issue (e.g., `recording_count` → `today_count`), fix and redeploy

Do NOT batch multiple unrelated fixes in one deployment cycle.

### Debugging instrumentation
**Add temporary debug logs when diagnosis is unclear**:
- Add `print(f"[DEBUG] variable={value}")` statements to trace execution
- Include context: object state, variable values, branch taken
- Remove or comment out debug logs after issue is resolved (or leave if helpful for future debugging)

Example:
```python
print(f"[OLED调试] display={self.display is not None}, accumulated_text长度={len(self.accumulated_text)}")
if self.display:
    print(f"[OLED调试] 正在调用update_stats更新副屏...")
```

### Code verification before deployment
**Always verify assumptions about code structure**:
- Check attribute names exist in `__init__` (e.g., `self.display` vs `self.display_controller`)
- Verify method signatures match call sites (parameter names, types)
- Read existing code patterns before adding similar functionality
- Use `grep_search` or `list_code_usages` to find all references

### Git commit discipline
**Commit immediately after successful fix with detailed message**:
- Commit message structure:
  ```
  <type>: <short summary>
  
  <detailed explanation>
  - Bullet point 1: what was wrong
  - Bullet point 2: how it was fixed
  - Bullet point 3: technical details
  
  <verification notes>
  ```
- Types: `fix:`, `feat:`, `refactor:`, `docs:`, `test:`
- Include root cause analysis in commit body
- Reference specific files and line numbers when helpful
- Push immediately after commit (`git push`)

Example commit message from session:
```
fix: 修复实时转录音频归一化和OLED副屏显示

核心问题修复:
1. **音频归一化**: VAD输出的音频数据未归一化(int16范围)，导致实时转录失败
   - 在audio_recorder_real.py的_on_vad_segment中添加归一化检查
   - 检测峰值>1.0时自动归一化(除以32768)
   
2. **OLED副屏显示**: 实时转录文本未同步到OLED副屏
   - 修复属性名错误: display_controller→display, recording_count→today_count

测试验证:
- 实时转录正常返回文本(之前返回空)
- 音频数据范围正常(Peak<1.0)
```

### Multi-step problem solving
**For complex issues with multiple symptoms**:
1. Identify the primary symptom (e.g., "实时转录返回空文本")
2. Gather evidence (logs showing audio range 134579 instead of 1.0)
3. Trace through the data flow (VAD → audio_recorder → ASR)
4. Find the broken link (missing normalization in `_on_vad_segment`)
5. Fix and verify primary issue resolves
6. If secondary issues appear (OLED not updating), repeat process

### Communication with maintainer
**During debugging session**:
- Report what you found: "错误信息：`'LifeCoachApp' object has no attribute 'display_controller'`"
- Explain root cause: "问题是属性名错误：应该是`self.display`而不是`self.display_controller`"
- State the fix: "我已修复属性名并部署"
- Provide verification command: "现在请在树莓派上录音测试，应该能看到OLED副屏更新"

**Keep responses concise**: Don't repeat long code blocks unless necessary. Use file links: `[main.py](main.py#L495-L535)`.


### Most Important instruction
** Do not commit code changes without explicit user approval. Always create a proposal in `docs/proposals/` first if new scripts or significant changes are needed. **

— End of instructions —
