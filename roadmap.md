# cmdstore Upgrade Roadmap

**Document status:** Proposed  
**Baseline:** `cmdstore` 0.6.0  
**Scope:** CLI reliability, command-library workflows, portability, and release quality

## Product direction

`cmdstore` should become a fast, dependable command library for developers: save a command once, find it quickly, understand what it does, and copy or run it safely from any supported shell.

The strongest product loop is:

1. Capture a command with useful metadata.
2. Search using natural fuzzy text, tags, tools, and recency.
3. Preview the full command and its safety context.
4. Copy or explicitly execute it.
5. Learn from usage without making the local store fragile.

## Priorities

### P0 — Reliability before expansion

These upgrades should land before adding broad integrations.

- Add automated tests for storage, config merging, filtering, import, selection parsing, and CLI behavior.
- Make JSON writes atomic and resilient to interruption or concurrent invocations.
- Validate and migrate stored data instead of silently treating malformed JSON as an empty store.
- Fix multi-line fzf input handling and standardize subprocess error behavior.
- Make clipboard failures actionable and honor the existing `auto_copy` configuration.
- Add non-interactive flags and exit codes so scripts can safely use `list`, `search`, `add`, `delete`, and `import`.
- Add CI for supported Python versions, linting, packaging, and tests.

**Exit criteria:** A fresh checkout has one documented check command, core behavior is covered by tests, interrupted writes do not destroy the store, and every command has predictable success, cancellation, and error behavior.

### P1 — Core command-management experience

- Add `edit` and `update` commands for descriptions, tags, tools, and command text.
- Add `show <id>` or `show <query>` for deterministic, non-interactive inspection.
- Add duplicate-aware `add` behavior with an explicit `--force` or `--duplicate` choice.
- Add richer search filters: multiple tags, negative filters, free-text filtering, shell/tool filters, and sort flags.
- Add `copy <id>` and `run <id>` as explicit actions instead of making copy an implicit side effect of search.
- Add favorites, pinning, aliases, and a “recently used” view.
- Add import preview, normalization, shell-history parsing, and a dry-run mode.

**Exit criteria:** A user can maintain the whole library without editing JSON manually and can use the library both interactively and in scripts.

### P2 — Portability and safety

- Detect Bash, Zsh, Fish, and PowerShell history formats.
- Support platform-aware clipboard providers with clear diagnostics.
- Add `--no-color`, `--json`, `--quiet`, and terminal capability detection.
- Use timezone-aware UTC timestamps and include `updated_at`, `last_used_at`, and optional source metadata.
- Add command safety hints for destructive patterns such as `rm -rf`, force pushes, database drops, and credential-bearing arguments.
- Add redaction rules and a secret warning before importing or storing likely credentials.
- Provide export/import formats such as JSON, JSONL, and Markdown with schema versioning.

**Exit criteria:** The same workflows behave consistently on macOS, Linux, and Windows where the underlying shell and clipboard are available, and risky commands receive a visible safety signal.

### P3 — Scale and ecosystem

- Replace the JSON list with a small repository abstraction so SQLite can be introduced without changing the CLI.
- Add full-text indexing when the library becomes large enough to need it.
- Add shell integrations for keybindings and command capture.
- Add optional Git-backed synchronization for stores intentionally placed in dotfiles repositories.
- Add plugin hooks for command sources, metadata enrichment, and display renderers.
- Consider semantic search only after exact/fuzzy search, tags, and usage ranking are demonstrably insufficient.

**Exit criteria:** Storage and integrations are extensible without coupling the CLI to one backend or one terminal UI.

## Recommended release sequence

### Release 0.7 — Quality foundation

1. Establish `tests/` and test fixtures using temporary store directories.
2. Extract storage, validation, sorting, and import logic into small testable units.
3. Add atomic writes, schema validation, and clear error types.
4. Fix fzf input/newline handling, clipboard configuration, and duplicate UI output.
5. Add `ruff`, test, type-check, build, and smoke-test commands to CI.
6. Document supported checks and compatibility assumptions.

### Release 0.8 — Complete CRUD and scriptability

1. Implement `edit`, `show`, `copy`, and optional `run`.
2. Add stable IDs to all machine-readable outputs.
3. Add `--json`, `--non-interactive`, and explicit cancellation/error exit codes.
4. Add duplicate detection and import dry-run.
5. Add schema versioning and a migration command.

### Release 0.9 — Better discovery and safety

1. Add combined search filters and configurable ranking.
2. Add favorites, aliases, recent commands, and last-used timestamps.
3. Add shell-aware history parsing and secret detection.
4. Add export/import documentation and compatibility tests.

### Release 1.0 — Stable local command library

1. Define the public CLI and JSON schema as compatibility contracts.
2. Publish platform support and dependency policy.
3. Add release automation, changelog generation, and signed/reproducible artifacts where practical.
4. Evaluate SQLite and shell integrations using real usage data rather than adding them preemptively.

## Feature ranking

| Feature | User value | Complexity | Recommendation |
|---|---:|---:|---|
| Atomic storage and validation | High | Medium | Do first |
| Tests and CI | High | Medium | Do first |
| `edit` / `show` / `copy` | High | Low | Do next |
| JSON and non-interactive output | High | Medium | Do next |
| Better history import | High | Medium | Do next |
| Favorites and aliases | Medium | Low | Do after CRUD |
| Safety warnings and redaction | High | Medium | Do before `run` |
| SQLite backend | Medium | Medium | Defer until scale requires it |
| Semantic search | Unclear | High | Defer |
| Cloud sync | Unclear | High | Defer; privacy-sensitive |

## Architectural target

Keep the current lightweight Python CLI, but separate responsibilities:

```text
CLI adapters
  ├── argparse commands and exit codes
  ├── terminal/fzf/fallback presentation
  └── JSON and human-readable renderers

Application services
  ├── add/update/delete/show/search/import
  ├── ranking and filtering
  └── safety and duplicate policies

Domain model
  ├── CommandRecord
  ├── StoreConfig
  └── schema validation/migrations

Repository ports
  ├── JSON repository (current/default)
  └── SQLite repository (future)
```

The CLI should not know how records are serialized, and the repository should not print terminal output. This makes the important behavior testable without spawning fzf or requiring a clipboard.

## Success metrics

- Core unit and integration tests cover the storage and import paths.
- `cmdstore` never loses an existing store because of a partial write.
- Search-to-copy takes one interactive action after the search prompt opens.
- Non-interactive commands produce stable output and exit codes.
- Import reports added, skipped, invalid, and suspicious entries separately.
- A new contributor can install the project and run the documented checks successfully.
