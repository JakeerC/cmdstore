# cmdstore Project Context

**Reviewed:** October 20, 2026  
**Repository:** `cmdstore`  
**Current version:** 0.6.0

## What the project is

`cmdstore` is a local Python CLI for saving, finding, and reusing shell commands. It stores command records as JSON, uses `fzf` for interactive selection when available, falls back to a numbered terminal UI when fzf is unavailable or disabled, and copies a selected command to the clipboard.

The intended primary user is a developer who repeatedly forgets or retypes commands for tools such as Git, npm, uv, Node, and shell utilities.

## Current user flows

### Add

```bash
cmdstore add "npm run dev" -d "Start development server" -t npm dev --tool npm
```

The command is stored with a UUID, description, tags, tool, creation timestamp, and usage count. With no command argument, the CLI prompts for fields interactively.

### Search and copy

```bash
cmdstore search
cmdstore search --tool npm
cmdstore search --tag python
```

Search sorts according to local configuration, presents fzf with a preview when enabled, increments usage for the selected record, and copies the command to the clipboard.

### List

```bash
cmdstore list
cmdstore list --tool npm
```

List renders human-readable records and can group by tool through configuration.

### Delete

```bash
cmdstore delete
```

Delete supports fzf multi-select, a numbered fallback selector, confirmation, and batch removal.

### Import

```bash
cmdstore import --file ~/.zsh_history --limit 200
```

Import reads recent lines, removes exact duplicate lines, lets the user select entries, and stores selected commands with configurable default metadata.

### Store configuration

```bash
cmdstore --set-store ~/dotfiles/.cmdstore
cmdstore --store ~/dotfiles/.cmdstore list
```

The effective store path is selected in this order:

1. `--store` for the current invocation.
2. `~/.cmdstore_config.json` global setting.
3. `~/.cmdstore` default.

Each store contains `commands.json` and `config.json`.

## Technology and repository shape

- Python package under `src/cmdstore/`.
- Python requirement: `>=3.12`.
- Build backend: Hatchling.
- Package manager/lockfile: uv and `uv.lock`.
- Runtime dependency: `pyperclip`.
- Optional external terminal dependency: `fzf`.
- CLI framework: Python standard-library `argparse`.
- Formatting/lint configuration: Ruff in `pyproject.toml`.
- Current persistence: JSON files in a user-selected directory.
- Current release metadata: package version 0.6.0.

Important modules:

| Module | Responsibility |
|---|---|
| `cli.py` | Argument parsing and dispatch |
| `store.py` | Storage, CRUD-like operations, sorting, import, and output |
| `config.py` | Global store-path configuration |
| `fzf_integration.py` | fzf subprocess calls, preview scripts, selection parsing |
| `fallback_ui.py` | Numbered interactive selection when fzf is unavailable |
| `colors.py` | ANSI terminal styling |

## Current record shape

```json
{
  "id": "uuid",
  "command": "npm run dev",
  "description": "Start development server",
  "tags": ["npm", "dev"],
  "tool": "npm",
  "created_at": "2024-01-01T12:00:00",
  "used_count": 5
}
```

The record is intentionally simple, but it lacks schema versioning, update timestamps, last-used timestamps, source/shell information, and safety metadata.

## Current architecture observations

### Strengths

- Small dependency footprint and easy local installation.
- Clear user-facing command model: add, search, list, delete, import.
- fzf preview and fallback UI make the central workflow usable across more environments.
- Configurable store location supports dotfiles and local version-control workflows.
- UUIDs allow records to be selected without relying on command text parsing alone.

### Constraints

- `CommandStore` combines persistence, domain logic, presentation, clipboard behavior, and subprocess fallback logic.
- JSON list storage rewrites the whole file for every mutation.
- There are no committed automated tests or CI workflows.
- Most commands are interactive, which makes automation and smoke testing harder.
- fzf and clipboard availability vary by operating system and terminal environment.
- User commands can contain secrets or destructive operations, but there is no warning or redaction policy.

## Quality baseline observed on October 20, 2026

Checks run from the repository root:

| Check | Result | Notes |
|---|---|---|
| `uv run python -m compileall -q src` | Passed | Source compiles under the uv-managed Python 3.12 environment. |
| `uv build` | Passed | Source distribution and wheel built successfully. |
| `uv run cmdstore --help` | Passed | CLI entry point is available. |
| `uvx ruff check .` | Passed | Ruff reports no lint violations, with a configuration deprecation warning. |
| `uv run ruff check .` | Failed / exit 2 | The project environment does not provide a `ruff` executable. This was unrelated to the documentation-only change; `ruff` is not declared in the dev dependency group. |
| Automated tests | Not available | No `tests/` directory or test runner configuration is committed. |

The reproducible local lint command is currently `uvx ruff check .`. The project should eventually declare Ruff in its development dependencies so `uv run ruff check .` works from a fresh checkout.

## Product decisions to preserve

- Keep the local-first model as the default.
- Keep fzf optional rather than making it a Python runtime dependency.
- Keep a fallback UI for environments without fzf.
- Preserve the current JSON store format through an explicit migration path.
- Do not add cloud sync or semantic search before reliability, safety, and scriptability are solved.

## Immediate next slice

The highest-value implementation slice is the 0.7 quality foundation:

1. Add tests around store creation, config merging, add/list/filter, duplicate import, and selection parsing.
2. Introduce atomic JSON writes and explicit malformed-store errors.
3. Fix the fzf multi-select input separator and honor `auto_copy.enabled`.
4. Add Ruff to the dev dependency group and move deprecated Ruff settings under `[tool.ruff.lint]`.
5. Add a minimal CI workflow that runs lint, tests, compile, and build.
