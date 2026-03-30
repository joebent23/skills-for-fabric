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

**Key capabilities:**
- Full, deterministic deployments from source control to workspace
- Automatic dependency resolution (deploys semantic models before reports)
- Environment-specific GUID replacement via `parameter.yml`
- Orphan cleanup for items removed from source
- Works with GitHub Actions, Azure DevOps, and local development

**Supported item types include:** Notebook, DataPipeline, Lakehouse, SemanticModel, Report, Environment, Warehouse, Eventhouse, Eventstream, KQLDatabase, KQLQueryset, SparkJobDefinition, VariableLibrary, and more. See the full list at the library documentation.

**Core pattern:**

```python
from fabric_cicd import FabricWorkspace, publish_all_items, unpublish_all_orphan_items

target = FabricWorkspace(
    workspace_id="<workspace-guid>",
    repository_directory="<path-to-git-repo-items>",
    environment="<target-env>",
    item_type_in_scope=["Notebook", "DataPipeline", "Lakehouse", "Environment"],
)

publish_all_items(target)
unpublish_all_orphan_items(target)
```

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

> The `environment` parameter passed to `FabricWorkspace()` must match a key in `replace_with`.

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
| GUID replacement not working | `environment` param doesn't match `parameter.yml` keys | Ensure environment value matches a key in `replace_with` |
| Deployment pipeline deploy fails | Items not paired or workspace not assigned | Verify stage assignment and item pairing |
| Git sync conflict | Both workspace and repo have changes | Use `update-from-git` or `commit-to-git`; resolve conflicts first |
| Variable library values wrong in target | Active value set not matching stage | Set the correct active value set per workspace |

> Ref: https://learn.microsoft.com/fabric/cicd/troubleshoot-cicd
