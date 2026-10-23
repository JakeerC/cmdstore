# cmdstore Issues and Upgrade Backlog

**Status legend:** `Open` = confirmed gap or defect; `Planned` = accepted for a roadmap phase; `Deferred` = intentionally postponed.

## P0 — Correctness and release safety

### CMD-001 — Add an automated test suite

- **Status:** Open
- **Severity:** Critical
- **Area:** Quality
- **Evidence:** No `tests/` directory, test dependency, or CI workflow is committed.
- **Impact:** Regressions in JSON persistence, fzf parsing, fallback selection, import, and CLI dispatch can ship unnoticed.
- **Acceptance criteria:** Tests cover store creation, config deep merge, add/list/filter, usage increments, delete confirmation policy, import duplicate handling, fzf selection parsing, and CLI smoke paths using temporary directories.
- **Plan:** Release 0.7.

### CMD-002 — Make JSON writes atomic

- **Status:** Open
- **Severity:** Critical
- **Area:** Storage
- **Evidence:** `store.py` writes directly to `commands.json` and `config.json` with `json.dump`.
- **Impact:** A process interruption or disk error can leave a truncated file. The loader then returns an empty list/config, which can hide data loss.
- **Acceptance criteria:** Write to a same-directory temporary file, flush and replace atomically, preserve file permissions where possible, and report failures without replacing the last valid file.
- **Plan:** Release 0.7.

### CMD-003 — Stop silently treating malformed JSON as empty data

- **Status:** Open
- **Severity:** Critical
- **Area:** Storage
- **Evidence:** `_load_commands` and `_load_config` catch `JSONDecodeError` and return `[]` or `{}`.
- **Impact:** Corruption is indistinguishable from a new/empty store and can cause later writes to overwrite recoverable data.
- **Acceptance criteria:** Emit an actionable error, preserve the corrupt file, and provide a recovery or backup path. Add a `doctor` command or documented repair procedure.
- **Plan:** Release 0.7.

### CMD-004 — Fix fzf multi-select input separation

- **Status:** Open
- **Severity:** High
- **Area:** Import / fzf
- **Evidence:** `run_fzf_multi_select` passes `"".join(fzf_input)` rather than newline-separated records.
- **Impact:** Multiple history entries can be concatenated into one fzf input record, making import selection incorrect and potentially causing an interactive command to wait unexpectedly.
- **Acceptance criteria:** Each item is separated by exactly one newline, empty selections are handled, and the behavior is covered by a subprocess-mocking test.
- **Plan:** Release 0.7.

### CMD-005 — Make the documented Ruff check reproducible

- **Status:** Open
- **Severity:** High
- **Area:** Tooling
- **Evidence:** `uv run ruff check .` exits 2 because Ruff is not installed in the project environment; `uvx ruff check .` passes. `pyproject.toml` only declares `twine` in the dev group.
- **Impact:** A contributor following the natural `uv run` workflow cannot run the configured lint check from a fresh environment.
- **Acceptance criteria:** Add Ruff to the dev dependency group, lock it with uv, and make `uv run ruff check .` pass. Move deprecated top-level Ruff `isort` configuration under `[tool.ruff.lint.isort]`.
- **Plan:** Release 0.7.

### CMD-006 — Add CI and release checks

- **Status:** Open
- **Severity:** High
- **Area:** Delivery
- **Evidence:** No `.github/workflows/` directory is committed.
- **Impact:** Packaging, lint, and compatibility failures are discovered only locally.
- **Acceptance criteria:** CI runs on supported Python versions, executes lint/tests/compile/build, and publishes only from an intentional release path.
- **Plan:** Release 0.7.

## P1 — Core workflow gaps

### CMD-007 — Honor the existing auto-copy configuration

- **Status:** Open
- **Severity:** High
- **Area:** UX / configuration
- **Evidence:** `auto_copy.enabled` and `auto_copy.show_notification` are defined in defaults and documented, but search always calls `pyperclip.copy` and always prints a copied message.
- **Impact:** User configuration does not match runtime behavior; clipboard access is an unavoidable side effect of search.
- **Acceptance criteria:** Disabled auto-copy leaves the clipboard unchanged; notification visibility follows configuration; clipboard errors provide a useful fallback.
- **Plan:** Release 0.7.

### CMD-008 — Add update/edit support

- **Status:** Planned
- **Severity:** High
- **Area:** CRUD
- **Evidence:** The CLI supports add, search, list, delete, and import, but records cannot be edited after creation.
- **Impact:** Users must delete and recreate commands to correct tags, descriptions, tools, or command text.
- **Acceptance criteria:** Provide stable-ID and interactive edit flows, validate fields, update `updated_at`, and preserve the record ID and usage history.
- **Plan:** Release 0.8.

### CMD-009 — Add deterministic `show` and `copy` commands

- **Status:** Planned
- **Severity:** High
- **Area:** Scriptability
- **Evidence:** Search is the only path that resolves a record and copies it; it is interactive by design.
- **Impact:** Scripts and shell aliases cannot reliably consume a selected command without driving fzf.
- **Acceptance criteria:** `show` emits human-readable or JSON output; `copy` accepts an ID or deterministic query; machine-readable output includes stable IDs and no ANSI escape codes.
- **Plan:** Release 0.8.

### CMD-010 — Add explicit command execution with safety controls

- **Status:** Deferred
- **Severity:** High
- **Area:** Safety
- **Evidence:** The current product copies commands but does not execute them, and records have no safety metadata.
- **Impact:** Adding execution without safeguards would make destructive or secret-bearing commands too easy to run.
- **Acceptance criteria:** Execution is opt-in, requires an explicit confirmation policy, shows the exact command, supports dry-run/print mode, and warns on destructive or credential-like patterns.
- **Plan:** Release 0.9 or later.

### CMD-011 — Improve duplicate detection and add behavior

- **Status:** Planned
- **Severity:** Medium
- **Area:** Data quality
- **Evidence:** `add_command` always appends a new record; import only compares stripped command text when configured to skip duplicates.
- **Impact:** Repeated imports and manual adds create redundant records and dilute usage ranking.
- **Acceptance criteria:** Normalize safely for comparison, report existing matches, allow intentional duplicates with an explicit flag, and never alter the stored command text unexpectedly.
- **Plan:** Release 0.8.

### CMD-012 — Add import dry-run and shell-aware parsing

- **Status:** Planned
- **Severity:** High
- **Area:** Import
- **Evidence:** Import treats history as plain lines, defaults to Bash, and does not distinguish metadata/timestamps or shell-specific formats.
- **Impact:** Zsh extended history, Fish history, multiline commands, blank lines, and shell metadata can be imported incorrectly.
- **Acceptance criteria:** Detect or explicitly select shell format, preview normalized candidates, support `--dry-run`, and report added/skipped/invalid/suspicious counts separately.
- **Plan:** Release 0.8/0.9.

## P2 — Portability, safety, and maintainability

### CMD-013 — Add schema versioning and migrations

- **Status:** Planned
- **Severity:** Medium
- **Area:** Persistence
- **Evidence:** Records and config have no schema version or migration mechanism.
- **Impact:** Adding fields or changing storage backends will require fragile implicit compatibility behavior.
- **Acceptance criteria:** Store a schema version, validate records on load, provide migrations, and keep a backup before migration.
- **Plan:** Release 0.8.

### CMD-014 — Use timezone-aware timestamps and usage metadata

- **Status:** Planned
- **Severity:** Medium
- **Area:** Data model
- **Evidence:** `datetime.now().isoformat()` creates a naive local timestamp; only `created_at` and cumulative `used_count` are recorded.
- **Impact:** Cross-machine stores and recency ranking are ambiguous.
- **Acceptance criteria:** Use UTC-aware timestamps, add `updated_at` and `last_used_at`, and define backwards-compatible parsing for existing records.
- **Plan:** Release 0.9.

### CMD-015 — Make terminal output configurable in practice

- **Status:** Open
- **Severity:** Medium
- **Area:** UX / portability
- **Evidence:** `colors_enabled`, `emoji_enabled`, and `compact_mode` exist in default config but the rendering code always emits ANSI styles and does not implement these options.
- **Impact:** Piped output, minimal terminals, and scripts receive formatting that configuration says should be optional.
- **Acceptance criteria:** Add `--no-color`, detect TTY capability, honor config, keep fzf preview behavior readable, and ensure JSON output is clean.
- **Plan:** Release 0.8.

### CMD-016 — Improve clipboard portability and diagnostics

- **Status:** Planned
- **Severity:** Medium
- **Area:** Platform support
- **Evidence:** Clipboard failures from `pyperclip.copy` are not handled in the search fallback path.
- **Impact:** Search can fail after selection even though the command itself was valid.
- **Acceptance criteria:** Catch clipboard-specific errors, print platform-specific remediation, allow `--print`/stdout fallback, and test with a mocked clipboard backend.
- **Plan:** Release 0.8.

### CMD-017 — Separate domain, persistence, and presentation responsibilities

- **Status:** Planned
- **Severity:** Medium
- **Area:** Architecture
- **Evidence:** `CommandStore` handles JSON I/O, business rules, fzf/fallback selection, clipboard copying, and terminal messages.
- **Impact:** Small changes require broad integration testing and make alternate interfaces/backends difficult.
- **Acceptance criteria:** Introduce repository and service boundaries while preserving the public CLI; domain methods return data/errors rather than printing.
- **Plan:** Release 0.8/0.9.

### CMD-018 — Protect secrets and destructive commands

- **Status:** Planned
- **Severity:** High
- **Area:** Privacy / safety
- **Evidence:** History import can store any selected shell line, including tokens, passwords, private URLs, or destructive commands; there is no warning or redaction.
- **Impact:** A local dotfiles-backed store can accidentally commit secrets or make dangerous commands easier to reuse.
- **Acceptance criteria:** Add configurable secret-pattern detection, redaction/warning prompts, an allowlist/denylist policy, and documentation that the store may contain sensitive data.
- **Plan:** Release 0.9.

## Deferred ideas

- SQLite backend and full-text indexing: useful when store size or concurrent usage justifies the migration.
- Cloud synchronization: privacy, conflict resolution, and secret handling need a clear product decision first.
- Semantic/embedding search: defer until exact fuzzy search and metadata are measured as insufficient.
- Plugin ecosystem: define stable repository/service interfaces first.
- Shell keybindings: valuable, but should build on deterministic `copy`, `show`, and import APIs.

## Suggested issue order

`CMD-001` → `CMD-002` → `CMD-003` → `CMD-004` → `CMD-005` → `CMD-006` → `CMD-007` → `CMD-008` → `CMD-009` → `CMD-011` → `CMD-012` → `CMD-013` → `CMD-015` → `CMD-016` → `CMD-014` → `CMD-018` → `CMD-010`.
