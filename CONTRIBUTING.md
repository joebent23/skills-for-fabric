# Contributing to Fabric Skills

Thank you for your interest in contributing to Microsoft Fabric Skills!

## Quick Start


1. Read the **[Skill Authoring Guide](docs/skill-authoring-guide.md)** — comprehensive how-to
2. Review the **[Quality Requirements](docs/quality-requirements.md)** — what makes a good skill
3. Check the **[Skill Catalog](docs/skill-catalog.md)** — see existing skills as examples

### EXAMPLE:  **[Create a new skill](prompt_examples/skills-creator/CreateAFabricSkill.txt)** — see how to use CLI to create a skill


## Key Guidelines (Summary)

For detailed documentation, see the `docs/` folder. Here's the quick summary:

### Skill Structure

Each skill lives in its own folder under `skills/` with a `SKILL.md` file.

```
skills/my-skill/
├── SKILL.md              # Required
└── references/           # Optional
```

### Naming Convention

- **Developer skills**: `{endpoint}-authoring-cli` (e.g., `sqldw-authoring-cli`)
- **Consumer skills**: `{endpoint}-consumption-cli` (e.g., `sqldw-consumption-cli`)
- **Agents**: `{persona}` (e.g., `FabricDataEngineer`, `FabricAdmin`) for cross-endpoint orchestration

### What Goes Where

| Content Type | Location | See Guide |
|--------------|----------|-----------|
| Agent definition | `agents/{persona}.agent.md` | [Architecture Overview](docs/architecture-overview.md) |
| Skill definition | `skills/{name}/SKILL.md` | [Skill Authoring](docs/skill-authoring-guide.md) |
| Shared reference docs | `common/` | [Common Folder](docs/common-folder-guide.md) |
| Plugin bundles | `plugins/` | [Plugins](docs/plugins-guide.md) |
| MCP server config | `mcp-setup/` | [MCP Servers](docs/mcp-servers-guide.md) |

### What to Avoid

- ❌ Executable scripts or implementation code in skills (use guidance and principles instead)
- ❌ Skills over 15,000 tokens (split or move content to common/)
- ❌ Overlapping trigger phrases with other skills
- ❌ Vague descriptions without action verbs or technologies
- ❌ Code templates that users copy-paste (enable LLM to generate code on-demand)

See: [Quality Requirements](docs/quality-requirements.md)

## Testing Your Skill Locally

### Install Pre-commit Hook (Recommended)

Install the pre-commit hook to run quality and security checks automatically before each commit:

```bash
# Windows (PowerShell)
Copy-Item .github\hooks\pre-commit .git\hooks\pre-commit

# macOS/Linux
cp .github/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

The hook runs on your machine (Windows/Linux/Mac) and blocks commits with critical issues.

### GitHub Copilot CLI

```bash
# Symlink to personal skills
# Windows
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.copilot\skills\{skill-name}" -Target ".\skills\{skill-name}"

# macOS/Linux
ln -s $(pwd)/skills/{skill-name} ~/.copilot/skills/{skill-name}
```

Then start a new Copilot CLI session and test prompts that should trigger your skill.

### Verifying Skill Loading

In Copilot CLI, you can check which skills are loaded:

```
/skills list
```

## Cross-Tool Compatibility

When adding a new skill or agent, update these compatibility files if needed:

- `compatibility/CLAUDE.md` - Add skill reference
- `compatibility/.cursorrules` - Add relevant rules
- `compatibility/AGENTS.md` - Add for Codex/Jules
- `compatibility/.windsurfrules` - Add for Windsurf

## Pull Request Checklist

- [ ] Skill folder and `SKILL.md` created
- [ ] Agent file `{persona}.agent.md` created in `agents/` (if introducing cross-endpoint orchestration)
- [ ] Description is clear and discoverable
- [ ] Reference documentation links are valid
- [ ] At least one example provided
- [ ] Tested locally with Copilot CLI
- [ ] Updated compatibility files (if applicable)
- [ ] Updated `CHANGELOG.md` with your changes (see below)
- [ ] Updated relevant specs/docs if behavior changed (see `docs/`)
- [ ] **Security**: No hardcoded secrets or credentials
- [ ] **Security**: Reviewed against docs/RAI_THREAT_MODEL.md
- [ ] **Security**: Added tests for prompt injection resistance (if applicable)
- [ ] **Security**: All CI security checks pass (CodeQL, secret scanning, prompt linting)
- [ ] Quality check passes (see below)

## Automated Quality Checks

When you submit a PR that modifies files in `skills/`, an automated quality check runs. The check validates:

### Critical Issues (Block PR)

| Check | Description |
|-------|-------------|
| **YAML Frontmatter** | Must have `name` and `description` fields |
| **Update Notice** | Must include the update check blockquote (except `check-updates`) |
| **Finding workspaces and items** | Must include instructions and references on how to find workspaces and items |
| **Cross-References** | All relative links must point to existing files |
| **Trigger Uniqueness** | Trigger phrases must not conflict with other skills |
| **Semantic Disambiguation** | Descriptions must not overlap >30% with other skills |

### Warnings (Review Recommended)

| Check | Description |
|-------|-------------|
| **Must/Prefer/Avoid Sections** | Should include guidance sections |
| **Examples** | Should include code or prompt/response examples |
| **Code Block Tags** | All code blocks should have language tags (```bash, ```sql, etc.) |
| **Description Quality** | Should start with action verb, mention technologies |
| **Naming Convention** | Should follow `{endpoint}-authoring-{access}` or `{endpoint}-consumption-{access}` pattern |
| **External Links** | URLs should be accessible (sampled, rate-limited) |

### Running Locally

Test your skill before submitting:

```bash
# Install dependencies
pip install PyYAML requests

# Run quality check
python .github/workflows/quality_checker.py
```

### Fixing Common Issues

| Issue | Fix |
|-------|-----|
| Missing frontmatter | Add `---` delimited YAML at file start with `name:` and `description:` |
| Missing update notice | Add the blockquote from CONTRIBUTING.md template |
| Broken reference | Fix relative path or update referenced file location |
| Untagged code block | Add language after opening ``` (e.g., ```bash) |
| Semantic conflict | Differentiate description from conflicting skill |

## Maintaining the Changelog

When adding or modifying skills, update `CHANGELOG.md` at the repository root:

1. Add your changes under the `[Unreleased]` section
2. Use these categories:
   - **Added** - New skills or features
   - **Changed** - Changes to existing skills
   - **Fixed** - Bug fixes
   - **Removed** - Removed skills or features
3. Keep entries concise and user-focused

Example:
```markdown
## [Unreleased]

### Added
- New `realtime-dev` skill for Real-Time Intelligence workloads

### Changed
- Updated `warehouse-dev` with new COPY INTO examples
```

When a release is made, maintainers will move `[Unreleased]` entries to a versioned section.

## Creating a Release (Maintainers)

To create a full release (catalog update, version stamp, tag, and GitHub release), run:

```powershell
# Preview changes locally (no commit/push)
.\ReleaseScripts\CreateFullRelease.ps1

# Full release: commit, tag, push, and create GitHub Release
.\ReleaseScripts\CreateFullRelease.ps1 --commit-and-push
```

This interactive script will:
1. Regenerate the skill catalog from `skills/*/SKILL.md` frontmatter
2. Show the 3 most recent version tags and suggest the next patch version
3. Stamp the version in `package.json`, `marketplace.json`, and related files
4. Commit, tag, push, and create a GitHub Release

**Prerequisites:** `git`, `python`, and `gh` (GitHub CLI) must be installed and in PATH.

## Generating Changelog (Maintainers)

Use the changelog generator to create release notes from merged PRs:

```bash
# Preview changes since last release
python .github/scripts/generate_changelog.py

# Update [Unreleased] section with PR summaries
python .github/scripts/generate_changelog.py --update

# Finalize a release (creates versioned section)
python .github/scripts/generate_changelog.py --release 0.2.0
```

For best results, set `GITHUB_TOKEN` to fetch PR titles and labels:
```bash
export GITHUB_TOKEN=ghp_your_token_here
```

The generator categorizes PRs by title prefix or labels:
- `feat:`, `add:`, `new:` → **Added**
- `fix:`, `bug:` → **Fixed**
- `docs:` → **Documentation**
- `refactor:`, `update:` → **Changed**

## Documentation

For detailed contributor guides:

| Guide | Purpose |
|-------|---------|
| [Architecture Overview](docs/architecture-overview.md) | Repository structure |
| [Skill Authoring Guide](docs/skill-authoring-guide.md) | Create skills (comprehensive) |
| [Common Folder Guide](docs/common-folder-guide.md) | Shared reference docs |
| [Plugins Guide](docs/plugins-guide.md) | Skill bundling |
| [Quality Requirements](docs/quality-requirements.md) | Quality standards |
| [Testing Guide](docs/testing-guide.md) | Tests and CI/CD |
| [MCP Servers Guide](docs/mcp-servers-guide.md) | MCP registration |
| [Skill Catalog](docs/skill-catalog.md) | Existing skills |

For planning documents (ADRs, specs, RFCs): see [docs/README.md](docs/README.md)

## Questions?

Open an issue or ask in discussions!
