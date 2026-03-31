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

# CI/CD Authoring — CLI Skill

## Prerequisite Knowledge

Read these companion documents — they contain foundational context this skill depends on:

- [COMMON-CORE.md](../../common/COMMON-CORE.md) — Fabric REST API patterns, authentication, token audiences, workspace/item discovery
- [COMMON-CLI.md](../../common/COMMON-CLI.md) — `az rest`, `az login`, token acquisition, Fabric REST via CLI
- [ITEM-DEFINITIONS-CORE.md](../../common/ITEM-DEFINITIONS-CORE.md) — Definition envelope, per-item-type parts, platform file format

For deployment approach details, see the resources in this skill:

| Deployment Approach | Resource | When to Use |
|---|---|---|
| Local development | [local-deployment.md](resources/local-deployment.md) | Developer testing items locally before pushing |
| GitHub Actions | [github-actions-deployment.md](resources/github-actions-deployment.md) | Teams using GitHub for source control and CI/CD |
| Azure DevOps | [azure-devops-deployment.md](resources/azure-devops-deployment.md) | Teams using Azure DevOps for source control and CI/CD |
| Fabric deployment pipelines | [deployment-pipelines.md](resources/deployment-pipelines.md) | Stage-to-stage promotion within Fabric |
| Variable libraries | [variable-libraries.md](resources/variable-libraries.md) | Stage-aware configuration management (connections, item refs, parameters) |

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

Verify the local repository has the expected structure before deploying.

```bash
# Check that .platform files exist in item folders
find ./fabric_items -name ".platform" -type f | head -5

# Verify a .platform file is valid JSON
cat ./fabric_items/MyNotebook.Notebook/.platform | python -m json.tool > /dev/null && echo "VALID" || echo "INVALID JSON"
```

| Result | Meaning | Fix |
|---|---|---|
| `.platform` files found and valid JSON | Items structured correctly | Proceed |
| No `.platform` files | Items not in Fabric Git format | Bootstrap from existing workspace (see [local-deployment.md § Bootstrapping](resources/local-deployment.md#bootstrapping-from-an-existing-workspace)) |
| Invalid JSON | Malformed metadata | Check for syntax errors, missing commas, or encoding issues |

---

## CI/CD Decision Framework

Help the user choose the right deployment approach based on their situation:

| Question | Option 1: Git-based (Gitflow) | Option 2: Git + Build env | Option 3: Deployment pipelines |
|---|---|---|---|
| **Source of truth** | Git repo (branch per stage) | Git repo (trunk-based) | Git for dev only; Fabric for promotion |
| **Branching model** | Multiple primary branches (dev/test/prod) | Single main branch with release pipelines | Main branch, stage-to-stage deploy |
| **Config management** | Post-deployment API calls | `parameter.yml` GUID replacement in build env | Deployment rules + autobinding |
| **Key tool** | Fabric Git APIs | `fabric-cicd` Python library | Deployment pipeline APIs |
| **Best for** | Teams wanting full Git control per stage | Teams needing env-specific GUID replacement | Teams preferring Fabric-native promotion |

> Ref: https://learn.microsoft.com/fabric/cicd/manage-deployment

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

- **Authenticate with service principal** for unattended CI/CD — use `ClientSecretCredential` from `azure-identity` or `az login --service-principal`
- **Enable tenant admin setting** "Service principals can use Fabric APIs" before SPN-based automation works
- **Add SPN as Member or Admin** on each target Fabric workspace
- **Store secrets in Azure Key Vault** — never in source code, pipeline YAML, or plain-text config
- **Use `parameter.yml`** for environment-specific GUID replacement when using `fabric-cicd` (workspace IDs, lakehouse IDs, SQL endpoint IDs, connection IDs)
- **Scope item types explicitly** via `item_type_in_scope` — deploy only the item types you intend to manage
- **Test deployments in a dev/test workspace** before promoting to production
- **Resolve workspace ID by name dynamically** via REST API — do not hardcode workspace GUIDs
- **Use variable libraries** for stage-aware configuration when items consume workspace-specific settings (connections, item references, parameters)

### PREFER

- `fabric-cicd` Python library over raw REST API calls — it handles dependency ordering, definition upload, and orphan cleanup
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

**Step 1: Find the SPN's object ID**

The role assignment API requires the SPN's **object ID** (also called the enterprise application / service principal object ID), NOT the application (client) ID.

```bash
# Find the SPN object ID from the application (client) ID
az rest --method get \
  --url "https://graph.microsoft.com/v1.0/servicePrincipals?\$filter=appId eq '<client-id>'" \
  --query "value[0].id" -o tsv
```

Alternatively, find it in the Azure portal: Entra ID → Enterprise applications → search by app name → copy the **Object ID**.

**Step 2: Add the SPN to the workspace**

```bash
# Grant SPN "Member" role on the workspace
az rest --method post \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<workspaceId>/roleAssignments" \
  --body '{
    "principal": {
      "id": "<spn-object-id>",
      "type": "ServicePrincipal"
    },
    "role": "Member"
  }'
```

Available roles: `Admin`, `Member`, `Contributor`, `Viewer`. For CI/CD deployments, use **Member** (can create and modify items) or **Admin** (full control including workspace settings and Git connection).

**Step 3: Add users or groups**

```bash
# Grant a user "Contributor" role
az rest --method post \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<workspaceId>/roleAssignments" \
  --body '{
    "principal": {
      "id": "<user-or-group-object-id>",
      "type": "User"
    },
    "role": "Contributor"
  }'
```

For groups, use `"type": "Group"` with the Entra security group's object ID.

**Step 4: Verify access**

```bash
# List current role assignments on a workspace
az rest --method get \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<workspaceId>/roleAssignments"
```

### Granting Access via Fabric UI (Manual Fallback)

When programmatic access is not possible (e.g., initial setup by a tenant admin):

1. Open the Fabric portal → navigate to the workspace
2. Click **Manage access** (gear icon or "..." menu → Manage access)
3. Click **Add people or groups**
4. Search for the SPN by its app registration display name
5. Select the role: **Member** (recommended for CI/CD) or **Admin**
6. Click **Add**

> **Note**: The SPN only appears in the search if "Service principals can use Fabric APIs" is enabled in tenant settings.

### Role Selection Guide for CI/CD

| Role | Can deploy items | Can manage Git connection | Can manage workspace settings | Recommended for |
|---|---|---|---|---|
| **Admin** | ✅ | ✅ | ✅ | SPN that manages full lifecycle including Git setup |
| **Member** | ✅ | ❌ | ❌ | SPN used only for `fabric-cicd` deployments |
| **Contributor** | ✅ | ❌ | ❌ | Team members who deploy but don't manage workspace |
| **Viewer** | ❌ | ❌ | ❌ | Read-only access — not for CI/CD |

### Variable Libraries

Variable libraries provide stage-aware configuration for Fabric items. They are the **recommended Fabric-native approach** for managing environment-specific values, complementing or replacing `parameter.yml` GUID replacement.

> For comprehensive guidance including variable types, value sets, consumption patterns, Git integration, and REST APIs, see [variable-libraries.md](resources/variable-libraries.md).

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

## Post-Deployment Operations

After deploying items, common post-deployment tasks include:

1. **Refresh semantic models** — trigger refresh via `POST .../jobs/instances?jobType=Refresh`
2. **Run notebooks** — trigger execution via `POST .../jobs/instances?jobType=RunNotebook`
3. **Trigger pipelines** — run data pipelines via `POST .../jobs/instances?jobType=Pipeline`
4. **Set data source credentials** — configure credentials for semantic models or other data items
5. **Validate deployment** — check item existence, verify connections, run test queries
6. **Update Power BI apps** — app content is NOT automatically updated by deployment; use API to update

> Ref: [COMMON-CORE.md § Job Execution](../../common/COMMON-CORE.md#job-execution)

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

```bash
az rest --method post \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<workspaceId>/git/connect" \
  --body '{
    "gitProviderDetails": {
      "organizationName": "<org>",
      "projectName": "<project>",
      "gitProviderType": "AzureDevOps",
      "repositoryName": "<repo>",
      "branchName": "main",
      "directoryName": "/fabric_items"
    }
  }'
```

### Resolve Workspace ID by Name

```bash
az rest --method get \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces" \
  --query "value[?displayName=='my-workspace-dev'].id" -o tsv
```

---

## Supported Items Reference

Not all Fabric items support Git integration and deployment equally. Before building a CI/CD pipeline, verify item support:

> Git integration supported items: https://learn.microsoft.com/fabric/cicd/git-integration/intro-to-git-integration#supported-items
> Deployment pipeline supported items: https://learn.microsoft.com/fabric/cicd/deployment-pipelines/intro-to-deployment-pipelines#supported-items
> fabric-cicd supported items: https://microsoft.github.io/fabric-cicd/latest/#supported-item-types

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
| Notebook deploys successfully but appears blank in Fabric | FabricGitSource `.py` format has incorrect whitespace or compact JSON | The `.py` format is whitespace-sensitive — blank lines required after markers, multi-line JSON in `# META` blocks. See [local-deployment.md § Item definition formats](resources/local-deployment.md#step-2-set-up-repository-structure) or use `.ipynb` format instead |

> Ref: https://learn.microsoft.com/fabric/cicd/troubleshoot-cicd
