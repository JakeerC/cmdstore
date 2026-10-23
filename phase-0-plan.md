# cmdstore Phase 0 Plan

**Handoff target:** agy agent  
**Status:** Ready for implementation  
**Prepared:** October 21, 2026  
**Repository:** `cmdstore`  
**Baseline:** `main` at `c451843` (`0.6.0`)  
**Source documents:** `roadmap.md`, `issues.md`, `context.md`

## 1. Goal

Deliver the reliability and release-quality foundation before adding new command-management features.
At the end of Phase 0:

- core storage, configuration, filtering, importing, selection parsing, and CLI smoke paths have automated coverage;
- an interrupted write cannot replace a valid JSON store with a partial file;
- malformed existing JSON fails loudly and cannot be mistaken for an empty store;
- fzf multi-select receives one newline-delimited item per record;
- search honors `auto_copy.enabled` and `auto_copy.show_notification`;
- lint, tests, compilation, packaging, and smoke checks run from a fresh checkout;
- behavior remains compatible with the current `commands.json` and `config.json` shapes.

The implementation should preserve the local-first workflow, optional fzf integration, fallback UI, and configurable store path.

## 2. Scope alignment

For this plan, **Phase 0 means the tracked P0 issues `CMD-001` through `CMD-007` and the Release 0.7 “Quality foundation” sequence**. Those are the concrete, currently accepted work items in `issues.md`.

The roadmap also mentions a larger non-interactive CLI surface and explicit exit-code behavior under P0. The Release 0.7 issue list does not define acceptance criteria for that work, while Release 0.8 does. Do not expand Phase 0 into full `--json`, `--non-interactive`, `show`, `copy`, or deterministic delete/import flows without an owner decision. Phase 0 should establish typed errors and predictable internal outcomes so that those flags can be added cleanly in Phase 1/Release 0.8.

## 3. Current state and constraints

- `CommandStore` currently combines JSON persistence, domain operations, terminal output, fzf/fallback selection, and clipboard behavior in `src/cmdstore/store.py`.
- Existing JSON writes use direct `open(..., "w")` and `json.dump`.
- Malformed `commands.json` and `config.json` are silently treated as `[]` and `{}`.
- `run_fzf_multi_select` concatenates records with no separator.
- Search always calls `pyperclip.copy` and always prints a copied notification.
- There is no committed `tests/` directory or CI workflow.
- Ruff is configured, but only `twine` is in the dev dependency group; `uv run ruff check .` is currently unavailable in a fresh project environment.
- The working tree already contains pre-existing untracked planning files: `context.md`, `issues.md`, and `roadmap.md`. Do not overwrite or delete them.
- No code changes have been made by this planning task.

## 4. Workstreams and dependency order

### Workstream A — Test foundation (`CMD-001`)

**Depends on:** none. Start here and keep tests close to each subsequent fix.

Add a pytest-based test suite using temporary directories and mocked external integrations. Do not require fzf, a system clipboard, a real home directory, or a user terminal in automated tests.

Create a fixture strategy centered on `CommandStore(tmp_path / "store")`; each test must own its store and must not touch `~/.cmdstore` or `~/.cmdstore_config.json`.

Minimum test coverage:

1. Store initialization creates `commands.json` and `config.json` with valid JSON.
2. Nested configuration merging preserves unspecified defaults and applies user overrides.
3. Default configuration values do not leak mutations between store instances; use a deep copy, not a shallow top-level copy.
4. Add, list, tool filtering, tag filtering, configured sorting, and usage-count increments.
5. Import removes exact duplicates, skips existing commands when configured, and reports counts.
6. Empty selection and cancellation are handled consistently for fzf and fallback selection.
7. `format_commands_for_fzf`, `extract_command_id`, and `extract_command_from_selection` handle normal selections and command text containing delimiter-like content as far as the current line format permits.
8. fzf subprocess calls are mocked to verify arguments, newline-separated input, return-code handling, and selected-line parsing.
9. Auto-copy enabled/disabled behavior and notification behavior are tested with a mocked clipboard.
10. Malformed JSON and atomic-write failures are tested without losing the last valid file.
11. CLI smoke tests use a temporary `--store` path and exercise `--help`, add, list, and at least one filtered path.

Suggested test files (the exact split may change if the implementation extracts modules):

```text
tests/conftest.py
tests/test_store_creation_and_config.py
tests/test_store_commands.py
tests/test_import.py
tests/test_storage_errors.py
tests/test_fzf_integration.py
tests/test_cli_smoke.py
```

### Workstream B — Storage safety (`CMD-002`, `CMD-003`)

Keep the public `CommandStore` API stable while extracting the smallest useful persistence helpers. A new `storage.py`, `repository.py`, or `errors.py` is acceptable if it reduces coupling; do not perform a broad architecture rewrite in this phase.

#### Atomic writes

Implement one shared JSON-write helper used by commands, local config, and any future global-config write that is in scope:

1. Create the temporary file in the target file’s directory so `os.replace` is same-filesystem.
2. Serialize with the current readable, indented JSON format.
3. Flush and call `os.fsync` before replacement.
4. Replace with `os.replace` only after the temporary file is complete.
5. Preserve existing file permissions where practical.
6. Clean up a temporary file after any failure.
7. Raise an explicit, actionable storage error; never silently continue as if the write succeeded.

Atomic replacement protects against partial files after interruption. It does not merge simultaneous logical updates from two processes. Do not claim lost-update prevention unless a separate locking strategy is implemented and tested; record that limitation in the handoff if it remains.

#### Loading and validation

Introduce typed errors with the file path and recovery guidance, for example `StoreDataError` / `MalformedStoreError`:

- an existing malformed JSON file must raise an error rather than return an empty list or config;
- a missing file may still be initialized as today;
- a valid JSON document with the wrong top-level shape must also fail clearly;
- existing records with the current optional fields remain readable, with defaults applied only to missing optional fields;
- required record fields (`id`, `command`) and basic types should be validated before mutation;
- no implicit schema migration is required in Phase 0;
- the corrupt file must remain untouched so the user can copy or repair it;
- document a manual recovery path in `README.md` (copy the corrupt file, restore a known-good backup, or repair the JSON before retrying).

Use `copy.deepcopy(DEFAULT_CONFIG)` when constructing defaults so nested lists/dicts cannot be shared across instances.

### Workstream C — fzf and selection behavior (`CMD-004`)

Update `src/cmdstore/fzf_integration.py` without changing the visible record format:

- pass `"\n".join(fzf_input)` to every multi-select subprocess call;
- return `[]` for a successful multi-select with no selected lines;
- return `None` for cancellation/non-zero fzf status;
- use `splitlines()` for stdout parsing so trailing newlines do not create phantom selections;
- preserve the existing `FileNotFoundError` signal so `CommandStore` can use the fallback UI;
- make other subprocess failures actionable and consistent rather than silently looking like cancellation;
- keep preview-script cleanup in a `finally` block.

Remove the duplicate “Select commands to import” message in `import_from_history` while touching the import path.

The test must assert that two input records such as `alpha` and `beta` are passed to subprocess as `alpha\nbeta`, not `alphabeta`.

### Workstream D — Clipboard configuration (`CMD-007`)

Centralize the post-selection behavior so fzf and fallback paths behave identically:

1. Always increment usage after a valid selection, regardless of clipboard availability.
2. If `auto_copy.enabled` is false, do not call `pyperclip.copy` and do not print a copied notification.
3. If auto-copy is enabled, call the clipboard once with the selected command.
4. Show the success notification only when `auto_copy.show_notification` is true.
5. Catch clipboard-specific failures and print an actionable warning that names the selected command path or suggests a print/paste fallback; do not discard the valid selected command.
6. Keep the return value as the selected command so a future non-interactive/print interface can reuse it.

The plan does not add `copy` or `run` commands, and it does not add secret detection. Those belong to later roadmap phases.

### Workstream E — Tooling and CI (`CMD-005`, `CMD-006`)

Update project tooling so a fresh checkout can run the same checks locally and in CI:

- add `pytest` and `ruff` to the dev dependency group;
- update `uv.lock` through uv, not by hand;
- move deprecated `[tool.ruff.isort]` settings to `[tool.ruff.lint.isort]`;
- keep the current Ruff rule selection unless a test/tooling change requires a focused adjustment;
- add `.github/workflows/ci.yml` with Python 3.12 and 3.13 matrix coverage, matching the project classifiers;
- install dependencies from the lockfile in CI;
- run lint, tests, compilation, build, and CLI smoke checks;
- do not add publishing credentials or release publishing to this workflow.

The required local check contract after this workstream is:

```bash
uv sync --dev --locked
uv run ruff check .
uv run pytest -q
uv run python -m compileall -q src
uv build
uv run cmdstore --help
uv run cmdstore --version
```

If a dedicated type checker is required, stop at the tooling decision gate before adding one: the repository currently has no type-checker configuration, and introducing one may require broader annotation work. Do not silently add a strict type-check gate that is not reproducible locally.

### Workstream F — Documentation and release notes

Update `README.md` only after the behavior is implemented and verified:

- document the reproducible check commands;
- explain malformed-store errors and the manual recovery procedure;
- document that auto-copy can be disabled and that clipboard failures do not invalidate the selected command;
- document fzf fallback and the current limitation that fzf treats each input record as one line;
- keep the JSON examples compatible with the current schema;
- add a short 0.7/Phase 0 release-notes section only if the project has an established release-notes location.

Do not mark roadmap/issues entries complete until the checks below have actually run.

## 5. Proposed implementation sequence

Use one focused change at a time. Keep the working tree reviewable and run the smallest relevant test after each step.

### Step 0 — Establish the baseline

1. Re-read this plan, `roadmap.md`, `issues.md`, and `context.md`.
2. Run `git status --short --branch` and preserve the pre-existing untracked planning files.
3. Run the current baseline commands to record any starting failures:

   ```bash
   uv run python -m compileall -q src
   uv build
   uv run cmdstore --help
   uvx ruff check .
   ```

4. Do not change behavior until the baseline is recorded in the implementation handoff or PR description.

### Step 1 — Add the test harness and fixtures

1. Add pytest and Ruff to the dev dependency group and update `uv.lock`.
2. Add the temporary-store fixtures and the initial tests for creation, config merging, add/list/filter, import duplicate handling, and selection parsing.
3. Run `uv run pytest -q` and use failures to define the smallest production changes needed.

### Step 2 — Extract and harden persistence

1. Add typed storage errors and validation helpers.
2. Replace direct JSON writes with the atomic helper.
3. Replace silent malformed-file fallbacks with explicit errors.
4. Add focused tests for malformed JSON, wrong top-level shapes, write failure cleanup, and preservation of the prior valid file.
5. Run storage tests, then the complete test suite.

### Step 3 — Fix fzf input and external-process outcomes

1. Correct multi-select input joining and stdout splitting.
2. Normalize empty selection/cancellation behavior.
3. Preserve fallback behavior for missing fzf and surface non-missing subprocess failures.
4. Remove duplicate import prompt output.
5. Run fzf integration tests and import tests without requiring the fzf binary.

### Step 4 — Apply clipboard configuration consistently

1. Move post-selection copy/notification logic into one helper or one clearly shared path.
2. Add the disabled, notification-disabled, successful-copy, and clipboard-error cases.
3. Run search/fallback tests with `pyperclip.copy` mocked.

### Step 5 — Define current CLI outcomes without expanding the CLI

1. Keep argparse usage errors on argparse’s existing exit path.
2. Make storage errors distinguishable from an empty store and ensure they reach the CLI as a non-zero result.
3. Preserve user cancellation as a non-destructive outcome; choose and document its exit behavior only if the implementation changes `main()` to return status codes.
4. Do not add the full non-interactive flag surface in this phase. If the owner wants that included, create a separate acceptance decision before coding it.

### Step 6 — Add CI and documentation

1. Move Ruff isort configuration to the current table location.
2. Add the CI matrix and exact check commands.
3. Update README troubleshooting and contributor checks.
4. Run every local check from a clean temporary store and inspect the final diff.

## 6. Acceptance checklist

Phase 0 is complete only when all of the following are true and evidenced by commands:

### Tests

- [ ] `tests/` is committed and pytest runs without fzf or clipboard services.
- [ ] Store creation, deep config merge, default isolation, add/list/filter/sort, usage increments, import duplicates, selection parsing, and CLI smoke paths are covered.
- [ ] The atomic-write failure test proves the previous valid file remains readable.
- [ ] The malformed-JSON test proves corruption is reported and not treated as an empty store.
- [ ] The fzf subprocess mock proves multi-select records are newline-separated.
- [ ] Auto-copy tests prove disabled copy does not touch the clipboard and notification config is honored.

### Behavior

- [ ] Existing valid stores continue to load with the current JSON shape.
- [ ] New writes are atomic and leave no temporary file after success or failure.
- [ ] A malformed existing store stops the operation with a path-specific recovery message.
- [ ] fzf cancellation, empty selection, missing binary, and non-zero subprocess status have distinct, documented behavior.
- [ ] Fallback selection still works when fzf is disabled or unavailable.
- [ ] Search selection still increments usage even when clipboard copy is disabled or unavailable.

### Tooling and delivery

- [ ] `uv run ruff check .` passes without the deprecated configuration warning.
- [ ] `uv run pytest -q` passes.
- [ ] `uv run python -m compileall -q src` passes.
- [ ] `uv build` passes.
- [ ] `uv run cmdstore --help` and `uv run cmdstore --version` pass.
- [ ] CI runs the same checks on Python 3.12 and 3.13.
- [ ] README documents the check command and malformed-store recovery.

## 7. File ownership map for agy

Expected implementation touch points:

| Path | Expected work |
|---|---|
| `src/cmdstore/store.py` | Use storage helpers, validate data, honor copy config, preserve current user flows |
| `src/cmdstore/fzf_integration.py` | Fix multi-select separators and subprocess result handling |
| `src/cmdstore/config.py` | Use safe/atomic global config writes if included in the shared helper scope |
| `src/cmdstore/errors.py` or `src/cmdstore/storage.py` | Optional focused extraction for typed errors, validation, and atomic JSON I/O |
| `tests/` | New pytest suite and temporary-store fixtures |
| `pyproject.toml` | Dev dependencies and Ruff configuration location |
| `uv.lock` | Lockfile update generated by uv |
| `.github/workflows/ci.yml` | New lint/test/compile/build/smoke workflow |
| `README.md` | Reproducible checks and recovery/configuration documentation |

Avoid unrelated changes to `roadmap.md`, `issues.md`, `context.md`, package version metadata, or the public JSON record shape until Phase 0 is verified.

## 8. Decisions already made

- Keep JSON as the default backend; no SQLite work in Phase 0.
- Keep fzf optional; never add it as a Python runtime dependency.
- Keep the numbered fallback UI.
- Preserve existing command IDs and JSON fields.
- Treat a malformed existing file as an error, never as an empty store.
- Prefer a small persistence extraction over a full service/repository rewrite.
- Use tests and mocks instead of requiring a real terminal, fzf binary, or clipboard provider.
- Do not add command execution, secret detection, schema migrations, or cloud sync.

## 9. Open decisions / stop conditions

Ask the owner before proceeding if any of these become necessary:

1. **Full scriptability in Phase 0:** whether to pull the roadmap’s broader non-interactive flags and explicit exit-code contract forward from Release 0.8.
2. **Type checking:** whether to add and configure a type checker, and which one, instead of limiting the quality gate to Ruff, pytest, compile, and build.
3. **Cross-process locking:** atomic replacement prevents partial writes but not lost updates from simultaneous writers. Add locking only with a defined cross-platform strategy and tests.
4. **Corrupt-file recovery command:** this plan uses an actionable error plus documented manual recovery. Add `cmdstore doctor` only if the owner wants a new command in Release 0.7.
5. **Clipboard failure exit status:** the selected command remains valid when copying fails; do not make a clipboard provider outage look like data loss without an explicit CLI policy.

## 10. First action for the next agent

From the repository root, start with:

```bash
git status --short --branch
uv run python -m compileall -q src
uv build
uv run cmdstore --help
uvx ruff check .
```

Then implement **Workstream A, Step 1**: add the test/dev-tooling foundation and temporary-store fixtures. Keep this file as the source of truth for scope, and update the implementation handoff with actual command results after each workstream.
