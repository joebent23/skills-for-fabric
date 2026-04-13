---
name: cicd-authoring-cli
description: >
  Automate Microsoft Fabric CI/CD workflows using the fabric-cicd Python library,
  Fabric REST APIs, Git integration, deployment pipelines, and variable libraries
  from CLI environments. Use when the user wants to: (1) deploy Fabric items to
  workspaces via fabric-cicd, (2) set up Git integration for a workspace,
  (3) automate deployments with GitHub Actions or Azure DevOps,
  (4) provision and configure workspaces for dev/test/prod,
  (5) manage environment-specific configuration with variable libraries,
  (6) use Fabric deployment pipelines programmatically,
  (7) configure service principal authentication for CI/CD automation.
  Triggers: "Fabric CI/CD", "fabric-cicd", "Fabric deployment pipeline setup",
  "Fabric Git integration setup", "promote items to production in Fabric",
  "automate Fabric deployment", "CI/CD pipeline for Fabric workspace",
  "Fabric GitHub Actions deployment", "Fabric Azure DevOps deployment",
  "Fabric variable library CI/CD", "service principal Fabric automation".
---

> **Update Check — ONCE PER SESSION (mandatory)**
> The first time this skill is used in a session, run the **check-updates** skill before proceeding.
> - **GitHub Copilot CLI / VS Code**: invoke the `check-updates` skill.
> - **Claude Code / Cowork / Cursor / Windsurf / Codex**: compare local vs remote package.json version.
> - Skip if the check was already performed earlier in this session.

> **CRITICAL NOTES**
> 1. To find the workspace details (including its ID) from workspace name: list all workspaces and, then, use JMESPath filtering
> 2. To find the item details (including its ID) from workspace ID, item type, and item name: list all items of that type in that workspace and, then, use JMESPath filtering

> **MUST NEVER — Deployment Guardrails**
> 1. **MUST NEVER** use raw REST API calls (`updateDefinition`, `createItemWithDefinition`) to deploy items to workspaces — **always** use the `fabric-cicd` Python library. Raw API calls bypass dependency ordering, skip GUID replacement, and can corrupt Git-connected workspace sync state.
> 2. **MUST NEVER** deploy directly to a Git-connected workspace via API or `fabric-cicd` — the dev workspace should only receive changes via Git sync. Use `fabric-cicd` to deploy to non-Git-connected target workspaces (test, prod).
> 3. **MUST NEVER** mix deployment approaches within a single workflow — choose one approach (fabric-cicd, deployment pipelines, or Git-based) and use it consistently throughout.
> 4. **MUST ALWAYS** validate deployments after execution — a successful API response (HTTP 200) does NOT guarantee correct deployment. Items can deploy but be blank, misconfigured, or fail at runtime. See [Post-Deployment Validation](#post-deployment-validation) and [gotchas.md](references/gotchas.md).

# CI/CD Authoring — CLI Skill

| Topic | Section |
|---|---|
| Shared knowledge | [Prerequisite Knowledge](#prerequisite-knowledge) |
| Deployment resources | [Deployment Approaches](#prerequisite-knowledge) |
| Validation before deploy | [Pre-Flight Validation](#pre-flight-validation) |
| Consistent workflow | [Standard Deployment Flow](#standard-deployment-flow) |
| Choosing an approach | [CI/CD Decision Framework](#cicd-decision-framework) |
| Guardrails | [Must/Prefer/Avoid](#mustpreferavoid) |
| Library & parameterisation | [Core Concepts](#core-concepts) |
| Known pitfalls | [Critical Gotchas Summary](#critical-gotchas-summary) |
| After deployment | [Post-Deployment Operations](#post-deployment-operations) |
| Item type matrix | [Supported Items Reference](#supported-items-reference) |

## Prerequisite Knowledge

Read these companion documents — they contain foundational context this skill depends on:

- [COMMON-CORE.md](../../common/COMMON-CORE.md) — Fabric REST API patterns, authentication, token audiences, workspace/item discovery
- [COMMON-CLI.md](../../common/COMMON-CLI.md) — `az rest`, `az login`, token acquisition, Fabric REST via CLI
- [ITEM-DEFINITIONS-CORE.md](../../common/ITEM-DEFINITIONS-CORE.md) — Definition envelope, per-item-type parts, platform file format

For deployment approach details, see the resources in this skill:

| Deployment Approach | Resource | When to Use |
|---|---|---|
| Local development | [local-deployment.md](references/local-deployment.md) | Developer testing items locally before pushing |
| GitHub Actions | [github-actions-deployment.md](references/github-actions-deployment.md) | Teams using GitHub for source control and CI/CD |
| Azure DevOps | [azure-devops-deployment.md](references/azure-devops-deployment.md) | Teams using Azure DevOps for source control and CI/CD |
| Fabric deployment pipelines | [deployment-pipelines.md](references/deployment-pipelines.md) | Stage-to-stage promotion within Fabric |
| Variable libraries | [variable-libraries.md](references/variable-libraries.md) | Stage-aware configuration management (connections, item refs, parameters) |
| Cross-item references | [cross-item-references.md](references/cross-item-references.md) | How items reference each other across environments (notebooks→lakehouses, pipelines→notebooks, etc.) |
| **Critical gotchas** | **[gotchas.md](references/gotchas.md)** | **Known deployment pitfalls by item type — read before deploying** |

---

## Pre-Flight Validation

**Before attempting any CI/CD operation, run these checks in order.** Each check includes the exact command, what success looks like, and what failure means. Stop at the first failure and resolve it before continuing.

### Check 1: Authentication

Verify an active Azure session exists and can acquire a Fabric API token.

```bash
# Verify login session is active
az account show --query "{user:user.name, tenant:tenantId}" -o table

# Verify Fabric API token can be acquired
az account get-access-token --resource https://api.fabric.microsoft.com --query "{expires:expiresOn}" -o table
```

| Result | Meaning | Fix |
|---|---|---|
| User and tenant displayed | Session active | Proceed |
| `Please run 'az login'` | No active session | Run `az login` (interactive) or `az login --service-principal` (SPN) |
| `AADSTS700016` | App registration not found | Check client ID is correct |
| `AADSTS7000215` | Invalid client secret | Rotate secret in Entra ID, update Key Vault |

> Ref: [COMMON-CLI.md § Authentication Recipes](../../common/COMMON-CLI.md#authentication-recipes)

### Check 2: Fabric API Access

Verify the current identity can reach the Fabric API and list workspaces.

```bash
az rest --method get \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces?roles=Admin,Member,Contributor" \
  --query "value | length(@)" -o tsv
```

| Result | Meaning | Fix |
|---|---|---|
| Number > 0 | Identity has workspace access | Proceed |
| `0` | Identity has no workspace roles | Add identity to workspaces (see [Granting Workspace Access](#granting-workspace-access-programmatically)) |
| `401 Unauthorized` | Token audience wrong or SPN not enabled | Check tenant setting "Service principals can use Fabric APIs" is enabled |
| `403 Forbidden` | Identity lacks permissions | For SPNs: verify the SPN is in the tenant setting allowlist |

### Check 3: Target Workspaces Exist and Have Capacity

For each target workspace (dev, test, prod), verify it exists, the identity has a role, and capacity is assigned.

```bash
# Check workspace exists and has capacity
az rest --method get \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces" \
  --query "value[?displayName=='<workspace-name>'].{name:displayName, id:id, capacity:capacityId}" -o table
```

| Result | Meaning | Fix |
|---|---|---|
| Row with name, id, and capacity GUID | Workspace exists with capacity | Proceed |
| Empty result | Workspace doesn't exist OR identity has no role on it | Create workspace or add identity to it |
| `capacityId` is null/empty | No capacity assigned | Assign capacity: `POST /v1/workspaces/{id}/assignToCapacity` |

> **Capacity is required** for Lakehouse, Warehouse, Notebook execution, and most item creation. Without it, item creation fails with `FeatureNotAvailable`.

### Check 4: Identity Role on Target Workspaces

Verify the identity has sufficient permissions (Member or Admin) on each target workspace.

```bash
# List role assignments on the workspace
az rest --method get \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<workspaceId>/roleAssignments" \
  --query "value[?principal.id=='<identity-object-id>'].{role:role, type:principal.type}" -o table
```

| Result | Meaning | Fix |
|---|---|---|
| `Member` or `Admin` | Sufficient for deployment | Proceed |
| `Contributor` | Can deploy items but cannot manage Git connection | Sufficient for `fabric-cicd` deployments; upgrade to Admin if Git connection setup needed |
| `Viewer` | Read-only — cannot deploy | Upgrade role to Member or Admin |
| Empty result | Identity has no role | Add via `POST /v1/workspaces/{id}/roleAssignments` (see [Granting Workspace Access](#granting-workspace-access-programmatically)) |

### Check 5: Available Capacity

If workspaces need to be created, verify that capacity is available.

```bash
az rest --method get \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/capacities" \
  --query "value[?state=='Active'].{name:displayName, id:id, sku:sku, region:region}" -o table
```

| Result | Meaning | Fix |
|---|---|---|
| One or more active capacities | Can assign to workspaces | Proceed |
| Empty result | No capacity available to this identity | Provision capacity via Azure portal or contact Fabric admin |

### Check 6: Python and fabric-cicd (for fabric-cicd deployments)

```bash
python --version
pip show fabric-cicd 2>/dev/null || echo "NOT INSTALLED"
```

| Result | Meaning | Fix |
|---|---|---|
| Python 3.9–3.13 + fabric-cicd version shown | Ready | Proceed |
| Python 3.14+ | Not yet supported | Use `py -3.13` (Windows) or `pyenv` to select 3.9–3.13 |
| `NOT INSTALLED` | Package missing | Run `pip install fabric-cicd` |

### Check 7: Git Integration Status (if using Git-connected dev workspace)

```bash
az rest --method get \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<devWorkspaceId>/git/status"
```

| Result | Meaning | Fix |
|---|---|---|
| JSON with `repositoryName`, `branchName` | Git connected | Proceed |
| `404` or `GitConnectionNotFound` | Not connected to Git | Connect via `POST /v1/workspaces/{id}/git/connect` (see [Git Integration APIs](#git-integration-apis)) |
| `WorkspaceNotConnectedToGit` | Connection dropped | Reconnect |

### Check 8: Item Definitions Valid (for fabric-cicd deployments)

Verify the local repository has the expected structure: each item folder must contain a `.platform` file with valid JSON, and content files matching the item type. See [local-deployment.md § Repository Structure](references/local-deployment.md#step-2-set-up-repository-structure) for the required format and [gotchas.md](references/gotchas.md) for item-type-specific pitfalls.

| Result | Meaning | Fix |
|---|---|---|
| `.platform` files found and valid JSON | Items structured correctly | Proceed |
| No `.platform` files | Items not in Fabric Git format | Bootstrap from existing workspace (see [local-deployment.md § Bootstrapping](references/local-deployment.md#bootstrapping-from-an-existing-workspace)) |
| Invalid JSON | Malformed metadata | Check for syntax errors, missing commas, or encoding issues |

---

## Standard Deployment Flow

**Every CI/CD setup MUST follow this workflow.** This ensures consistency regardless of which deployment approach is chosen. Do not deviate from this sequence.

### Phase 1: Gather Requirements

Before writing any code or configuration, ask the user:

1. **Deployment approach**: Which approach fits their team? If unsure, guide them through the [CI/CD Decision Framework](#cicd-decision-framework) or point to the [official Microsoft decision guide](https://learn.microsoft.com/fabric/cicd/manage-deployment)
2. **Item types in scope**: Which Fabric item types will be deployed? (Notebook, Lakehouse, DataPipeline, SemanticModel, Report, VariableLibrary, etc.)
3. **Environments**: How many stages? (dev/test/prod or a subset)
4. **Existing infrastructure**: Are workspaces already created? Is there a service principal? Is capacity assigned? For workspace provisioning, reference the FabricAdmin agent capabilities
5. **Source control**: GitHub or Azure DevOps? Is the dev workspace already Git-connected?
6. **Cross-item references**: Do items reference other items (notebooks → lakehouses, pipelines → notebooks, reports → semantic models)? This determines whether `parameter.yml`, variable libraries, or both are needed

### Phase 2: Pre-Flight Validation

Run all applicable [Pre-Flight Validation](#pre-flight-validation) checks. Stop at the first failure and resolve before proceeding.

### Phase 3: Repository Structure

Generate the repository structure with item definition folders following the [Fabric Git source format](https://learn.microsoft.com/fabric/cicd/git-integration/source-code-format). Include:

- Item folders with `.platform` files and content files
- `parameter.yml` if GUID replacement is needed
- Variable library definitions if using variable libraries
- Deployment script (`.deploy/deploy-to-fabric.py` or equivalent)
- CI/CD pipeline YAML (if using GitHub Actions or Azure DevOps)

### Phase 4: Configuration

- Generate `parameter.yml` with find/replace pairs for all environment-specific GUIDs
- Create variable library definitions with value sets for each environment
- Configure CI/CD secrets (GitHub Secrets or Azure Key Vault → ADO Variable Groups)
- Set up approval gates for test and production environments

### Phase 5: Deploy

Execute the deployment using the chosen approach. **Always use `fabric-cicd`** for deploying to non-Git-connected workspaces.

### Phase 6: Validate

Run post-deployment validation at minimum Tiers 1–3 (see [Post-Deployment Validation](#post-deployment-validation)):

1. **Tier 1**: Verify items exist in target workspace
2. **Tier 2**: Verify content is correct (especially notebooks — check for blank deployments)
3. **Tier 3**: Run key notebooks/pipelines and verify execution succeeds
4. **Tier 4** (optional): Verify data exists in lakehouses/warehouses

---

## CI/CD Decision Framework

If the user is unsure which deployment approach to use, guide them through the decision by asking qualifying questions about their team, tooling, and requirements. For comprehensive guidance, point them to the [official Microsoft CI/CD decision guide](https://learn.microsoft.com/fabric/cicd/manage-deployment).

### Qualifying Questions

Ask these questions to recommend an approach:

| Question | If the answer is... | Recommend |
|---|---|---|
| Do you use GitHub or Azure DevOps for source control? | GitHub | Option 2 with GitHub Actions |
| | Azure DevOps | Option 2 with Azure DevOps Pipelines |
| | Neither / Fabric only | Option 3 (Deployment Pipelines) |
| How many people are on your team? | Small team (1–3 analysts) | Option 3 — lightest weight, no external CI/CD tooling needed |
| | Medium team (4–15 engineers) | Option 2 — `fabric-cicd` with GH Actions or ADO |
| | Large org / enterprise | Option 2 with approval gates and Key Vault |
| Do items need different GUIDs per environment? | Yes (lakehouse IDs, connections, etc.) | Option 2 with `parameter.yml` and/or variable libraries |
| | No — same config everywhere | Option 1 or 3 (simpler) |
| Do you need approval gates before production? | Yes | Option 2 with GH Environments or ADO Environments |
| | No | Any option works |

### Microsoft's Four Options

> Ref: https://learn.microsoft.com/fabric/cicd/manage-deployment

| Option | Name | Source of Truth | Key Tool | Best For |
|---|---|---|---|---|
| **1** | Git-based (Gitflow) | Git repo (branch per stage) | Fabric Git APIs | Teams wanting full Git control per stage |
| **2** | Git + Build environment | Git repo (trunk-based) | `fabric-cicd` Python library | Teams needing env-specific GUID replacement — **most common for enterprise CI/CD** |
| **3** | Deployment pipelines | Git for dev only; Fabric for promotion | Deployment pipeline APIs | Teams preferring Fabric-native promotion, smaller teams |
| **4** | ISV multi-tenant | Git repo (trunk-based) | `fabric-cicd` + per-customer config | ISVs with separate workspaces per customer |

### How this skill's resources map to Microsoft's options

| This skill's resource | Covers MS Option(s) | Notes |
|---|---|---|
| [local-deployment.md](references/local-deployment.md) | Option 2 (local) | Developer testing with `fabric-cicd` before pushing |
| [github-actions-deployment.md](references/github-actions-deployment.md) | Option 2 (GH Actions) | Automated `fabric-cicd` deployment via GitHub |
| [azure-devops-deployment.md](references/azure-devops-deployment.md) | Option 2 (ADO) | Automated `fabric-cicd` deployment via Azure DevOps |
| [deployment-pipelines.md](references/deployment-pipelines.md) | Option 3 | Fabric-native stage-to-stage promotion |

> **Option 1 (pure Gitflow)** is a variant of Option 2 where each stage has its own primary branch connected to a workspace via Fabric Git APIs. The same `fabric-cicd` tooling applies — see the branch strategy sections in the GitHub Actions and Azure DevOps resources.

> **Option 4 (ISV multi-tenant)** is a variant of Option 2 with per-customer workspaces and parallel deployments. This skill's patterns apply but the orchestration layer (deploying to hundreds of workspaces) is out of scope.

> **Bulk Import Item Definitions API (beta)**: Microsoft also offers a [Bulk Import API](https://learn.microsoft.com/rest/api/fabric/core/items/bulk-import-item-definitions(beta)) as an alternative to `fabric-cicd` for Option 2. It sends all item definition files in a single REST call and relies on Fabric's server-side dependency handling. It is simpler (no Python library needed), but it is currently in **beta**, does not support `parameter.yml` GUID replacement, and does not provide orphan cleanup. This skill recommends `fabric-cicd` over the Bulk Import API for production CI/CD. See the [Bulk Import tutorial](https://learn.microsoft.com/fabric/cicd/tutorial-bulkapi-cicd) for details.

### When to use `fabric-cicd` (Options 1 & 2)

Prefer the `fabric-cicd` Python library when:
- Deploying from Git as single source of truth
- Needing deterministic, full deployments
- Requiring GUID replacement across environments (lakehouse IDs, connection IDs)
- Wanting orphan cleanup (removing items no longer in source)
- Integrating with GitHub Actions or Azure DevOps pipelines

### When to use Fabric deployment pipelines (Option 3)

Prefer deployment pipelines when:
- Using source control only for development, not release
- Deployment rules and autobinding suffice for config management
- Wanting Fabric-native features: change comparison, deployment history, visual pipeline UI
- Linear promotion model fits the team workflow

---

## Must/Prefer/Avoid

### MUST DO

- **Always use `fabric-cicd`** for deploying items to non-Git-connected workspaces — never use raw REST API `updateDefinition` or `createItemWithDefinition`
- **Always validate deployments** — run at least Tier 1–3 post-deployment validation checks (see [Post-Deployment Validation](#post-deployment-validation))
- **Authenticate with service principal** for unattended CI/CD — use `ClientSecretCredential` from `azure-identity` or `az login --service-principal`
- **Enable tenant admin setting** "Service principals can use Fabric APIs" before SPN-based automation works
- **Add SPN as Member or Admin** on each target Fabric workspace
- **Store secrets in Azure Key Vault** — never in source code, pipeline YAML, or plain-text config
- **Use `parameter.yml`** for environment-specific GUID replacement when using `fabric-cicd` (workspace IDs, lakehouse IDs, SQL endpoint IDs, connection IDs)
- **Scope item types explicitly** via `item_type_in_scope` — deploy only the item types you intend to manage
- **Test deployments in a dev/test workspace** before promoting to production
- **Resolve workspace ID by name dynamically** via REST API — do not hardcode workspace GUIDs
- **Use variable libraries** for stage-aware configuration when items consume workspace-specific settings (connections, item references, parameters)
- **Read [gotchas.md](references/gotchas.md)** before deploying any item type — it contains critical pitfalls that cause silent failures

### PREFER

- Trunk-based branching with `parameter.yml` for GUID replacement over branch-per-stage workflows
- Separate workspaces per environment (dev/test/prod) for isolation and independent permissions
- Small, frequent deployments over large batch releases
- Approval gates (GitHub Environments or ADO Environments) before production deployments
- `unpublish_all_orphan_items()` to keep target workspaces clean — but be cautious with selective deployments
- Variable libraries over hardcoded item references or connection strings
- `change_log_level("DEBUG")` during initial CI/CD setup for troubleshooting

### AVOID

- Hardcoded workspace IDs, lakehouse IDs, or FQDNs — discover dynamically or parameterize
- Storing SPN credentials in pipeline YAML or repo files — always use Key Vault or GitHub Secrets
- Deploying to production without approval gates
- Using `unpublish_all_orphan_items()` with narrowed `items_in_scope` unless you understand that it will delete items of those types not found in the source branch
- Deploying items that are not supported by `fabric-cicd` or Git integration — check the supported item types list
- Mixing Git integration direction (committing from workspace while also pushing from CI/CD) — choose one source of truth
- Skipping post-deployment validation (row counts, schema checks, data source connectivity)
- Using Fabric deployment pipelines with workspace network access protection (inbound/outbound) — this is not supported

---

## Core Concepts

### The `fabric-cicd` Python Library

`fabric-cicd` is Microsoft's open-source Python library for code-first Fabric deployments. It abstracts Fabric REST APIs and handles dependency ordering, definition upload, and environment-specific configuration.

> Ref: https://microsoft.github.io/fabric-cicd/latest/
> Ref: https://learn.microsoft.com/rest/api/fabric/articles/fabric-ci-cd

**Supported item types:** ApacheAirflowJob, CopyJob, DataAgent, DataPipeline, Dataflow, Environment, Eventhouse, Eventstream, GraphQLApi, KQLDashboard, KQLDatabase, KQLQueryset, Lakehouse, MirroredDatabase, MLExperiment, MountedDataFactory, Notebook, Reflex, Report, SemanticModel, SparkJobDefinition, SQLDatabase, UserDataFunction, VariableLibrary, Warehouse.

#### FabricWorkspace Constructor

Import from `fabric_cicd`. Guide the LLM to construct with these parameters:

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `workspace_id` | `str` | One of `workspace_id` or `workspace_name` | `None` | Target workspace GUID. Takes precedence if both provided |
| `workspace_name` | `str` | One of `workspace_id` or `workspace_name` | `None` | Target workspace display name — resolved to ID via API |
| `repository_directory` | `str` | Yes | — | Local directory path containing item definition folders |
| `environment` | `str` | For parameterization | `"N/A"` | Must match a key in `parameter.yml` `replace_value` (e.g., `"test"`, `"prod"`) |
| `item_type_in_scope` | `list[str]` | No | All types | Limits which item types are deployed (e.g., `["Notebook", "Lakehouse"]`) |
| `token_credential` | `TokenCredential` | No | `DefaultAzureCredential` | From `azure-identity` — use `ClientSecretCredential` for SPN auth |

#### publish_all_items

Deploys all in-scope items from the repository to the target workspace. Handles dependency ordering automatically (e.g., semantic models before reports).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `fabric_workspace_obj` | `FabricWorkspace` | — | Required: the workspace object |
| `item_name_exclude_regex` | `str` | `None` | Regex to skip items by name (e.g., `".*_draft"`) |
| `folder_path_exclude_regex` | `str` | `None` | Regex to skip folders — **experimental**, requires `enable_experimental_features` + `enable_exclude_folder` flags |
| `folder_path_to_include` | `list[str]` | `None` | Deploy only from these folders (e.g., `["/release"]`) — **experimental**, requires `enable_experimental_features` + `enable_include_folder` flags |
| `items_to_include` | `list[str]` | `None` | Deploy only these items (format: `"ItemName.ItemType"`) — **experimental**, requires `enable_experimental_features` + `enable_items_to_include` flags |
| `shortcut_exclude_regex` | `str` | `None` | Regex to skip Lakehouse shortcuts — **experimental**, requires `enable_shortcut_exclude` + `enable_shortcut_publish` flags |

#### unpublish_all_orphan_items

Removes items from the workspace that are no longer in the repository. Only affects item types in `item_type_in_scope`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `fabric_workspace_obj` | `FabricWorkspace` | — | Required: the workspace object |
| `item_name_exclude_regex` | `str` | `"^$"` | Regex to preserve items from deletion (e.g., `".*_keep"`) |
| `items_to_include` | `list[str]` | `None` | Only unpublish these specific items — **experimental** |

#### deploy_with_config

A simplified alternative that uses a YAML config file. The LLM should generate the config file and call `deploy_with_config(config_file_path, environment, token_credential)`. Returns a `DeploymentResult` with `status` (`COMPLETED` / `FAILED`), `message`, and optional `responses`.

> Ref: https://microsoft.github.io/fabric-cicd/latest/code_reference/#fabric_cicd.deploy_with_config

#### Feature Flags

Feature flags enable opt-in capabilities. Call `append_feature_flag("<flag>")` **before** `publish_all_items` or `unpublish_all_orphan_items`.

**Data safety flags** — required for `unpublish_all_orphan_items` to delete data-containing items:

| Flag | Enables Deletion Of |
|---|---|
| `enable_lakehouse_unpublish` | Lakehouses |
| `enable_warehouse_unpublish` | Warehouses |
| `enable_eventhouse_unpublish` | Eventhouses |
| `enable_kqldatabase_unpublish` | KQL Databases |
| `enable_sqldatabase_unpublish` | SQL Databases |

> **Critical**: Without these flags, `unpublish_all_orphan_items()` warns but skips these item types. This prevents accidental data loss. Enable only when you intend for orphan cleanup to remove stale data-containing items.

**Deployment behaviour flags:**

| Flag | Purpose |
|---|---|
| `enable_shortcut_publish` | Deploy Lakehouse shortcuts alongside the Lakehouse item. Safe to enable even if no shortcuts exist — the library silently skips if no `shortcuts.metadata.json` is found. Only enable when your Lakehouse definitions include shortcut metadata |
| `enable_shortcut_exclude` | Allow `shortcut_exclude_regex` parameter (selective shortcut deployment) |
| `enable_exclude_folder` | Allow `folder_path_exclude_regex` parameter (skip folders) |
| `enable_include_folder` | Allow `folder_path_to_include` parameter (deploy only specific folders) |
| `enable_items_to_include` | Allow `items_to_include` parameter (selective item deployment) |
| `enable_experimental_features` | Required prerequisite for `enable_exclude_folder`, `enable_include_folder`, and `enable_items_to_include` |
| `enable_environment_variable_replacement` | Use CI/CD pipeline variables for replacement instead of `parameter.yml` |
| `continue_on_shortcut_failure` | Continue deployment if shortcuts fail to publish (instead of stopping). Useful when shortcut targets may not exist yet in the target workspace |

**Operational flags:**

| Flag | Purpose |
|---|---|
| `enable_response_collection` | Collect API responses — access via `workspace.responses` after deployment |
| `disable_print_identity` | Suppress the executing identity name from log output |
| `disable_workspace_folder_publish` | Skip deploying workspace subfolder structure |

> **Feature flag guidance**: Only enable flags you actually need. Flags are additive — enabling a flag that isn't applicable (e.g., `enable_shortcut_publish` without shortcuts) is harmless but adds unnecessary processing. The data safety flags (`enable_*_unpublish`) should only be enabled when you explicitly want orphan cleanup to delete those item types.

> **Known issue — Variable Library with Item/Connection References**: Deploying a variable library containing item reference or connection reference variables fails with `ReferencedEntityAccessDenied` if the deploying identity (SPN) does not have read access to the referenced item or connection. Ensure the SPN has at least read permission on all items and connections referenced in variable library values.

#### Logging and Debugging

Call `change_log_level("DEBUG")` to enable verbose output showing all API calls. Logs are written to `fabric_cicd.error.log` by default. Call `disable_file_logging()` for console-only output.

### Parameter Files for GUID Replacement

When items contain hardcoded GUIDs (workspace IDs, lakehouse IDs, SQL endpoint IDs), `fabric-cicd` uses `parameter.yml` to replace them per environment.

Place `parameter.yml` alongside item definitions in the repository. Define find/replace pairs per environment:

```yaml
find_replace:
  - find_value: "dev-workspace-guid"
    replace_value:
      PPE: "test-workspace-guid"
      PROD: "prod-workspace-guid"
  - find_value: "dev-lakehouse-guid"
    replace_value:
      PPE: "test-lakehouse-guid"
      PROD: "prod-lakehouse-guid"
```

> The `environment` parameter passed to `FabricWorkspace()` must match a key in `replace_value`.

> **When parameter.yml is NOT needed**: If your items do not contain hardcoded GUIDs from the dev workspace (e.g., plain notebooks that don't use `%%configure` with lakehouse IDs, or items that use variable libraries for all environment-specific values), you can omit `parameter.yml` entirely. The `environment` parameter on `FabricWorkspace` is also optional when no parameterization is needed.

### Service Principal Authentication for CI/CD

Service principal (SPN) authentication is required for unattended CI/CD. Setup requires:

1. **Create Entra ID app registration** with a client secret (or certificate)
2. **Enable tenant setting**: Admin Portal → Tenant Settings → "Service principals can use Fabric APIs" → Include the SPN or its security group
3. **Add SPN to workspaces**: Add as Member or Admin on each target workspace
4. **Store credentials securely**: Azure Key Vault with secrets for tenant ID, client ID, client secret

**Authentication in `fabric-cicd`:**

```python
from azure.identity import ClientSecretCredential

credential = ClientSecretCredential(
    tenant_id="<tenant-id>",
    client_id="<client-id>",
    client_secret="<client-secret>",
)

target = FabricWorkspace(
    workspace_id="<workspace-id>",
    repository_directory="<repo-dir>",
    environment="PROD",
    item_type_in_scope=["Notebook", "Lakehouse"],
    token_credential=credential,
)
```

**Interactive authentication** (local development): Use `az login` — `fabric-cicd` picks up the `DefaultAzureCredential` automatically.

### Workspace Provisioning for CI/CD

Provision separate workspaces for each environment stage. Guide the LLM to generate commands for:

1. **Create workspaces** via REST API — one per environment (dev, test, prod)
2. **Assign capacity** — each workspace must have Fabric capacity for item creation
3. **Grant SPN access** — add the service principal as Member or Admin on each workspace
4. **Grant team member access** — add users/groups with appropriate roles
5. **Configure Git integration** on the dev workspace (connect to repo branch)

> Ref: [COMMON-CORE.md § Create Workspace](../../common/COMMON-CORE.md#create-workspace)
> Ref: [COMMON-CORE.md § Workspace Role Assignment](../../common/COMMON-CORE.md#workspace-role-assignment)

Workspace naming convention: `{project}-{env}` (e.g., `sales-analytics-dev`, `sales-analytics-test`, `sales-analytics-prod`)

### Granting Workspace Access Programmatically

This is a critical CI/CD prerequisite — if the SPN lacks workspace access, all deployments fail with `403 Forbidden`.

For the workspace role assignment API patterns, see [COMMON-CORE.md § Workspace Role Assignment](../../common/COMMON-CORE.md#workspace-role-assignment). The CI/CD-specific steps are:

**Step 1: Find the SPN's object ID**

The role assignment API requires the SPN's **object ID** (the enterprise application / service principal object ID), NOT the application (client) ID.

```bash
# Find the SPN object ID from the application (client) ID
az rest --method get \
  --url "https://graph.microsoft.com/v1.0/servicePrincipals?\$filter=appId eq '<client-id>'" \
  --query "value[0].id" -o tsv
```

Alternatively, find it in the Azure portal: Entra ID → Enterprise applications → search by app name → copy the **Object ID**.

**Step 2: Add the SPN to each target workspace**

Use the role assignment API from [COMMON-CORE.md](../../common/COMMON-CORE.md#workspace-role-assignment) with `"type": "ServicePrincipal"` and role `"Member"` or `"Admin"`. Add the SPN to every target workspace (dev, test, prod).

**Step 3: Verify access**

```bash
az rest --method get \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<workspaceId>/roleAssignments"
```

> **Note**: The SPN only appears in Fabric portal search if "Service principals can use Fabric APIs" is enabled in tenant settings.

### Role Selection Guide for CI/CD

| Role | Can deploy items | Can manage Git connection | Can manage workspace settings | Recommended for |
|---|---|---|---|---|
| **Admin** | ✅ | ✅ | ✅ | SPN that manages full lifecycle including Git setup |
| **Member** | ✅ | ❌ | ❌ | SPN used only for `fabric-cicd` deployments |
| **Contributor** | ✅ | ❌ | ❌ | Team members who deploy but don't manage workspace |
| **Viewer** | ❌ | ❌ | ❌ | Read-only access — not for CI/CD |

### Variable Libraries

Variable libraries provide stage-aware configuration for Fabric items. They are the **recommended Fabric-native approach** for managing environment-specific values, complementing or replacing `parameter.yml` GUID replacement.

> For comprehensive guidance including variable types, value sets, consumption patterns, Git integration, and REST APIs, see [variable-libraries.md](references/variable-libraries.md).

**When to use variable libraries vs parameter.yml:**
- **Variable libraries**: Runtime configuration — values resolve when items execute, not at deploy time. Changes propagate immediately without redeployment. Best for connections, item references, and runtime parameters
- **parameter.yml**: Deploy-time configuration — GUIDs replaced in definition files before upload. Best for IDs baked into item definitions (e.g., `%%configure` lakehouse IDs when not using variable library syntax)
- **Both together**: Use variable libraries for runtime config and `parameter.yml` for any remaining deploy-time GUIDs

**Key patterns:**
- Define variables with value sets for each stage (dev/test/prod)
- One value set is active per workspace — determines runtime values
- After first deployment to a new workspace, set the correct active value set via API
- Supported consumers: Pipelines (`@pipeline().libraryVariables`), Notebooks (`notebookutils.variableLibrary`), Dataflows Gen2, Lakehouses (shortcuts), Copy Jobs, User Data Functions
- Variable libraries are a supported `fabric-cicd` item type — include `"VariableLibrary"` in `item_type_in_scope`
- Use **item reference** variables for lakehouse/warehouse references that differ per stage
- Use **connection reference** variables for external data connections that differ per stage

### Git Integration APIs

For automating Git operations on workspaces:

| Operation | API | Notes |
|---|---|---|
| Connect workspace to Git | `POST /v1/workspaces/{id}/git/connect` | Requires workspace admin |
| Initialize connection | `POST /v1/workspaces/{id}/git/initializeConnection` | Sets initial sync direction |
| Get status | `GET /v1/workspaces/{id}/git/status` | Shows item sync state |
| Commit to Git | `POST /v1/workspaces/{id}/git/commitToGit` | Push workspace changes to repo |
| Update from Git | `POST /v1/workspaces/{id}/git/updateFromGit` | Pull repo changes to workspace |
| Disconnect | `POST /v1/workspaces/{id}/git/disconnect` | Remove Git connection |

> Ref: https://learn.microsoft.com/fabric/cicd/git-integration/git-automation

**Supported Git providers:** Azure DevOps (cloud), GitHub (cloud), GitHub Enterprise (cloud).

---

## Critical Gotchas Summary

These are the most dangerous deployment pitfalls — deployments that succeed (HTTP 200) but produce broken items. For full details and all item types, see [gotchas.md](references/gotchas.md).

| Gotcha | Item Type | What Happens | Prevention |
|---|---|---|---|
| **Silent blank notebook** | Notebook | `.py` format deploys successfully but notebook appears blank in Fabric | Use `.ipynb` format, or follow strict whitespace rules in `.py` format. Always verify content size after deploy |
| **Missing lakehouse binding** | Notebook | Notebook has content but `RunNotebook` fails with generic error | Ensure `default_lakehouse`, `default_lakehouse_name`, AND `default_lakehouse_workspace_id` are all present in metadata. Use `%%configure` with variable library (recommended) or `parameter.yml` |
| **Minimal `definition.pbism`** | SemanticModel | Deploy fails with `Workload_FailedToParseFile` | Use exactly `{"version":"1.0","settings":{}}` — no extra properties |
| **Raw REST API deployment** | All | Breaks Git sync, skips dependency ordering, no GUID replacement | ALWAYS use `fabric-cicd` library — NEVER `updateDefinition` API directly |
| **First pipeline deploy fails** | Deployment Pipelines | `WorkloadUnavailable` after assigning workspaces to stages | Wait 60–120s after workspace assignment before first deploy |
| **Variable library active set** | VariableLibrary | Deploys with default value set active — wrong config for target env | Set active value set via API after first deployment to each workspace |

---

## Post-Deployment Operations

After deploying items, common post-deployment tasks include:

1. **Refresh semantic models** — trigger refresh via `POST .../jobs/instances?jobType=Refresh`
2. **Run notebooks** — trigger execution via `POST .../jobs/instances?jobType=RunNotebook`
3. **Trigger pipelines** — run data pipelines via `POST .../jobs/instances?jobType=Pipeline`
4. **Set data source credentials** — configure credentials for semantic models or other data items
5. **Validate deployment** — run post-deployment validation checks (see below)
6. **Update Power BI apps** — app content is NOT automatically updated by deployment; use API to update
7. **Set variable library active value set** — after first deployment to a new workspace, activate the correct value set via `PATCH /v1/workspaces/{id}/variableLibraries/{varLibId}`

> Ref: [COMMON-CORE.md § Job Execution](../../common/COMMON-CORE.md#job-execution)

### Post-Deployment Validation

**A successful deployment response does NOT guarantee a correct deployment.** Items can deploy but be blank, misconfigured, or fail at runtime. Always validate at minimum Tiers 1–3 after every deployment.

For comprehensive per-item-type gotchas, see [gotchas.md](references/gotchas.md).

#### Tier 1 — Item Existence

Verify all expected items exist in the target workspace:

```bash
az rest --method get \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<workspaceId>/items" \
  --query "value[].{name:displayName, type:type}" -o table
```

Compare the item list against the expected items from the repository. Flag any missing items.

#### Tier 2 — Content Verification

For **notebooks**: Retrieve the definition and verify the payload is not blank (a blank notebook is ~26 bytes — just `# Fabric notebook source`):

```bash
az rest --method post \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<wsId>/items/<itemId>/getDefinition"
```

Decode the Base64 payload and check that actual cell content exists. Any notebook with real content should be significantly larger than 26 bytes.

#### Tier 3 — Execution Verification

Run key notebooks or pipelines to verify they execute successfully:

```bash
# Trigger notebook execution
az rest --method post \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<wsId>/items/<notebookId>/jobs/instances?jobType=RunNotebook"
```

Poll the returned operation until completion. A `Failed` result indicates configuration issues — typically missing lakehouse binding, missing connections, or incorrect variable library values.

#### Tier 4 — Data Verification (Optional)

For items that produce data (notebooks writing to lakehouses), verify data exists. **Do not rely on the Lakehouse Tables REST API** — it may return empty results for Spark-managed Delta tables. Instead, run a validation notebook that reads expected tables, checks row counts, and prints a pass/fail summary.

---

## Power BI Item Deployment

Deploying SemanticModel and Report items requires extra care compared to Fabric-native items (Notebook, Lakehouse). Common pitfalls include definition format errors and identity attribution differences.

**For comprehensive guidance** on creating and deploying semantic models (TMDL format, required files, minimal content, gotchas), see:
- [powerbi-authoring-cli SKILL.md](../powerbi-authoring-cli/SKILL.md) — TMDL CRUD lifecycle, definition structure, authoring scope matrix
- [ITEM-DEFINITIONS-CORE.md § SemanticModel](../../common/ITEM-DEFINITIONS-CORE.md#semanticmodel) — Required parts for TMSL and TMDL formats
- [ITEM-DEFINITIONS-CORE.md § Report](../../common/ITEM-DEFINITIONS-CORE.md#report) — Required parts for PBIR and PBIR-Legacy formats

**Key gotchas for CI/CD deployment of Power BI items:**

- **`definition.pbism` must be minimal** — use `{"version":"1.0","settings":{}}` only. Additional properties like `enablePowerBiDataSourceApp` cause `Workload_FailedToParseFile` errors
- **Report creation is not supported by `powerbi-authoring-cli`** — Reports use a separate PBIR definition format. For CI/CD, author reports in Power BI Desktop, commit to Git, and deploy via `fabric-cicd`
- **Autobinding handles report-to-model references** — when promoting via deployment pipelines, reports automatically rebind to the paired semantic model in the target stage
- **`fabric-cicd` resolves dependency ordering** — semantic models deploy before reports automatically

---

## Identity Best Practices

When mixing `az login` (user identity) for local development and SPN for CI/CD automation, be aware of identity attribution differences:

- **Fabric-native items** (Notebook, Lakehouse, DataPipeline): `createdBy` reflects the calling identity correctly
- **Power BI items** (SemanticModel, Report): May show different ownership attribution depending on the deployment mechanism (direct API vs deployment pipeline internal behaviour)
- **Deployment pipelines** may internally attribute Power BI items differently than the calling identity

**Recommendations:**
- Use a **single SPN identity** for all automated deployments to maintain consistent ownership attribution
- Avoid mixing `az login` user deployments with SPN deployments to the same workspace
- Verify item ownership post-deployment if governance requires clear attribution — use `POST /v1.0/myorg/admin/workspaces/getInfo` (Power BI Admin API) to inspect `createdBy` and `modifiedBy`

---

## Examples

### Deploy Notebooks Locally with fabric-cicd

```bash
# Install fabric-cicd
pip install fabric-cicd

# Authenticate
az login
```

```python
from fabric_cicd import FabricWorkspace, publish_all_items

workspace = FabricWorkspace(
    workspace_id="<your-workspace-id>",
    repository_directory="./fabric_items",
    item_type_in_scope=["Notebook", "Lakehouse"],
)

publish_all_items(workspace)
```

> Ref: https://learn.microsoft.com/fabric/cicd/tutorial-fabric-cicd-local

### Connect a Workspace to Git via REST API

Use `POST /v1/workspaces/{id}/git/connect` with the `gitProviderDetails` body. See the [Git Integration APIs](#git-integration-apis) table for the full endpoint list and the [COMMON-CLI.md](../../common/COMMON-CLI.md) patterns for `az rest` body construction.

> Ref: https://learn.microsoft.com/fabric/cicd/git-integration/git-automation

### Resolve Workspace ID by Name

> Ref: [COMMON-CLI.md § Workspace Lookup](../../common/COMMON-CLI.md) — use `az rest` with JMESPath filtering on `displayName`

---

## Supported Items Reference

Not all Fabric items support Git integration and deployment equally. Before building a CI/CD pipeline, verify item support:

> Git integration supported items: https://learn.microsoft.com/fabric/cicd/git-integration/intro-to-git-integration#supported-items
> Deployment pipeline supported items: https://learn.microsoft.com/fabric/cicd/deployment-pipelines/intro-to-deployment-pipelines#supported-items
> fabric-cicd supported items: https://microsoft.github.io/fabric-cicd/latest/#supported-item-types

**Working examples and item definition formats:**

| Resource | What it contains |
|---|---|
| [fabric-cicd sample workspace](https://github.com/microsoft/fabric-cicd/tree/main/sample/workspace) | Verified item definitions — the format `fabric-cicd` is tested against |
| [ITEM-DEFINITIONS-CORE.md](../../common/ITEM-DEFINITIONS-CORE.md) | Required parts, formats, and decoded content for every supported item type |
| [gotchas.md](references/gotchas.md) | Per-item-type deployment pitfalls and prevention guidance |
| [cross-item-references.md](references/cross-item-references.md) | How items reference each other across environments |

### Item Type Quick Reference

Every item folder must contain a `.platform` file. The table below shows the main content files and cross-item references for each supported type:

| Item Type | Content Files | Has Cross-Item References? | Key Gotcha |
|---|---|---|---|
| **ApacheAirflowJob** | `apacheairflowjob-content.json`, `dags/*.py` | May reference other items in DAGs | — |
| **CopyJob** | `copyjob-content.json` | ✅ Source/destination lakehouses (`workspaceId`, `artifactId`) | Use variable library connection refs per environment |
| **DataPipeline** | `pipeline-content.json`, `.schedules` | ✅ Notebook IDs, lakehouse IDs in activities | Replace activity `notebookId`/`workspaceId` via `parameter.yml` or variable library |
| **Dataflow** | `mashup.pq`, `queryMetadata.json` | May reference connections | Power Query format |
| **Environment** | `environment.yml`, `Sparkcompute.yml`, custom `.whl`/`.jar` files | Referenced by notebooks/jobs via environment ID | Custom libraries stored in `Libraries/` folder |
| **Eventhouse** | `EventhouseProperties.json`, child KQL DB folders | ✅ Child KQL DBs reference parent via `parentEventhouseItemId` | Deploy parent before children |
| **Eventstream** | `eventstream.json`, `eventstreamProperties.json` | ✅ Sources/destinations reference other items (`workspaceId`, `itemId`) | Complex JSON with sources, operators, destinations |
| **GraphQLApi** | `graphql-definition.json` | May reference data sources | — |
| **KQLDashboard** | `RealTimeDashboard.json` | ✅ Data sources reference Eventhouses/KQL DBs | Dashboard queries embed data source references |
| **KQLDatabase** | `DatabaseProperties.json`, `DatabaseSchema.kql` | ✅ Parent Eventhouse ID | Schema includes table/mapping/policy definitions |
| **KQLQueryset** | `RealTimeQueryset.json` | ✅ `databaseItemId` references KQL DB | — |
| **Lakehouse** | `lakehouse.metadata.json`, optional `shortcuts.metadata.json` | ✅ Shortcuts reference other lakehouses | See [gotchas.md § Lakehouse](references/gotchas.md#lakehouse) |
| **MirroredDatabase** | `mirroring.json` | May reference external sources | — |
| **MLExperiment** | `mlexperiment.metadata.json` | Minimal — `{"dependencies":[]}` | — |
| **Notebook** | `notebook-content.py` or `.ipynb` | ✅ Default lakehouse + environment bindings | See [gotchas.md § Notebook](references/gotchas.md#notebook) — **highest risk item type** |
| **Reflex** | `ReflexEntities.json` | May reference Eventstreams | — |
| **Report** | `definition.pbir`, `report.json`, `Staticreferences/` | ✅ Semantic model binding via `byConnection` or `byPath` | Do not author manually — use Power BI Desktop |
| **SemanticModel** | `definition.pbism`, `definition/*.tmdl` (TMDL) or `model.bim` (TMSL) | ✅ Reports bind to it | See [gotchas.md § SemanticModel](references/gotchas.md#semanticmodel) |
| **SparkJobDefinition** | `SparkJobDefinitionV1.json`, `Main/*.py`, `Libs/*.py` | ✅ Default lakehouse ID, environment ID | Similar binding issues as Notebooks |
| **SQLDatabase** | `.sqlproj`, `.gitignore` | Minimal | SQL project format |
| **UserDataFunction** | `definition.json`, `function_app.py`, `.references/functions.json` | Minimal | Python runtime function |
| **VariableLibrary** | `variables.json`, `settings.json`, `valueSets/*.json` | Consumed by many item types | See [gotchas.md § VariableLibrary](references/gotchas.md#variablelibrary) |
| **Warehouse** | `.platform` only (minimal) | Minimal | Data not deployed — structure only |

---

## Troubleshooting

| Issue | Likely Cause | Resolution |
|---|---|---|
| `401 Unauthorized` on deployment | Wrong token audience or SPN not enabled | Use `https://api.fabric.microsoft.com/.default` scope; verify tenant setting |
| `403 Forbidden` on workspace operations | SPN lacks workspace role | Add SPN as Member or Admin on workspace |
| Items not deploying | Item type not in `item_type_in_scope` | Add the item type to scope list |
| GUID replacement not working | `environment` param doesn't match `parameter.yml` keys | Ensure environment value matches a key in `replace_value` |
| Deployment pipeline deploy fails | Items not paired or workspace not assigned | Verify stage assignment and item pairing |
| Git sync conflict | Both workspace and repo have changes | Use `update-from-git` or `commit-to-git`; resolve conflicts first |
| Variable library values wrong in target | Active value set not matching stage | Set the correct active value set per workspace |
| `Workload_FailedToParseFile` for SemanticModel | `definition.pbism` contains unsupported properties | Strip to `{"version":"1.0","settings":{}}` — extra properties are rejected |
| `WorkspaceMigrationOperationInProgress` (HTTP 400) | Concurrent deployment pipeline operations | Only one pipeline operation can run at a time; wait for current operation to complete before retrying |
| `No matching distribution found` for fabric-cicd | Python version 3.14+ not yet supported | Use Python 3.9–3.13; on Windows use `py -3.13`, on Linux use `pyenv` to select a compatible version |
| `createdBy` blank on Power BI items | Identity attribution differs by item type and deployment mechanism | Use a single SPN identity for all deployments; see [Identity Best Practices](#identity-best-practices) |
| `PyToIPynbFailure: prologue is invalid` | Notebook `.py` file doesn't start with required prologue | The first line of any `.py` notebook file MUST be exactly `# Fabric notebook source`. No comments, blank lines, or other content before it |
| `ReferencedEntityAccessDenied` deploying variable library | SPN lacks read access to items/connections referenced in variable library | Ensure the SPN has at least read permission on all items and connections referenced in variable library item reference and connection reference variables |
| `Alm_InvalidRequest_WorkloadUnavailable` on first deploy | Workload services not yet initialized after workspace assignment to pipeline | Wait 60–120s after workspace assignment, then retry. Deploy PBI items first, then Fabric-native items. Subsequent deploys work normally |
| Lakehouse Tables API returns empty `data: []` | Spark-managed Delta tables not visible via REST API | Tables created by `saveAsTable()` may not surface in `GET .../lakehouses/{id}/tables`. Use notebook execution for data verification instead |
| Notebook deploys successfully but appears blank in Fabric | FabricGitSource `.py` format has incorrect whitespace or compact JSON | The `.py` format is whitespace-sensitive — blank lines required after markers, multi-line JSON in `# META` blocks. See [local-deployment.md § Item definition formats](references/local-deployment.md#step-2-set-up-repository-structure) or use `.ipynb` format instead |
| Notebook deploys but `RunNotebook` fails with "Job instance failed without detail error" | Notebook metadata missing `default_lakehouse` and/or `default_lakehouse_workspace_id` | The `# META dependencies.lakehouse` block must include all three fields: `default_lakehouse` (GUID), `default_lakehouse_name`, and `default_lakehouse_workspace_id` (GUID). Fix with either: (A) add all three GUIDs to `parameter.yml` for deploy-time replacement, or (B) use variable library `%%configure` for runtime resolution — see [local-deployment.md](references/local-deployment.md) and [variable-libraries.md](references/variable-libraries.md) |

> Ref: https://learn.microsoft.com/fabric/cicd/troubleshoot-cicd
