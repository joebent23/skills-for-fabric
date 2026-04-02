# Azure DevOps Deployment for Fabric

This resource covers automating Microsoft Fabric deployments using Azure DevOps Pipelines with the `fabric-cicd` Python library.

> Ref: https://learn.microsoft.com/fabric/cicd/tutorial-fabric-cicd-azure-devops

## When to Use

- Teams using Azure DevOps for source control and CI/CD
- Organizations with existing ADO infrastructure (Variable Groups, Key Vault integration, Environments)
- Enterprises requiring centralized approval gates and audit trails
- Teams using Azure DevOps Repos for Fabric Git integration

## Prerequisites

| # | Prerequisite | Details |
|---|---|---|
| 1 | Azure DevOps Organization & Project | A project with Repos and Pipelines enabled |
| 2 | Microsoft Fabric Workspaces | Three workspaces — one each for dev, test, and prod |
| 3 | Service Principal (SPN) | An Entra ID App Registration with a client secret |
| 4 | SPN Permissions in Fabric | SPN must be added as Member or Admin on each target workspace |
| 5 | Azure Key Vault | A Key Vault with three secrets: Tenant ID, Client ID, Client Secret |
| 6 | Fabric Git Integration | Dev workspace connected to the `dev` branch of the ADO repo |
| 7 | Python 3.9+ | Used in the pipeline agent to run the deployment script |
| 8 | Fabric Admin Setting | "Service principals can use Fabric APIs" must be enabled in Fabric Admin Portal |

## Service Principal Setup

Same steps as described in [github-actions-deployment.md § Service Principal Setup](github-actions-deployment.md#service-principal-setup). The SPN must:

1. Be created in Entra ID with a client secret
2. Be enabled in Fabric tenant settings ("Service principals can use Fabric APIs")
3. Be added as Member/Admin on each target workspace

## Secret Management with Azure Key Vault

### Create Key Vault Secrets

Store SPN credentials in Azure Key Vault (never in ADO variable values or repo files):

| Secret Name | Description | Example |
|---|---|---|
| `aztenantid` | Entra ID tenant GUID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `azclientid` | SPN application (client) ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `azspnsecret` | SPN client secret value | `your-secret-value` |

Grant the ADO service connection (or project identity) **Get** and **List** permissions on the Key Vault secrets (via Access Policy or RBAC role `Key Vault Secrets User`).

### Sensitive Variable Group: `fabric_cicd_group_sensitive`

1. Navigate to Pipelines → Library → + Variable group
2. Name: `fabric_cicd_group_sensitive`
3. Toggle on **Link secrets from an Azure key vault as variables**
4. Select Azure subscription and Key Vault
5. Add the three secrets: `aztenantid`, `azclientid`, `azspnsecret`
6. Save

These secrets are fetched at runtime and automatically masked in logs — you see `***` instead of values.

### Non-Sensitive Variable Group: `fabric_cicd_group_non_sensitive`

1. Create another variable group (not Key Vault linked)
2. Name: `fabric_cicd_group_non_sensitive`
3. Add variables:

| Variable Name | Value | Description |
|---|---|---|
| `devWorkspaceName` | `MyProject-Dev` | Dev workspace display name |
| `testWorkspaceName` | `MyProject-Test` | Test workspace display name |
| `prodWorkspaceName` | `MyProject-Prod` | Prod workspace display name |
| `gitDirectory` | `fabric` | Repo folder with Fabric item definitions |

ADO injects these as **uppercase environment variables** (e.g., `TESTWORKSPACENAME`). The deployment script reads them dynamically using `os.environ[f"{target_env}WorkspaceName".upper()]`.

## ADO Environments & Approval Gates

Create environments at Pipelines → Environments:

| Environment Name | Approval Required? | Purpose |
|---|---|---|
| `dev` | No (auto-deploy) | Development — auto-triggered |
| `test` | Yes — add approvers | Testing gate — pauses pipeline for review |
| `prod` | Yes — add approvers | Production gate — requires sign-off |

For `test` and `prod`: Click environment → ⋮ → Approvals and checks → + Add check → Approvals → add required approvers.

When the pipeline YAML uses `environment: $(target_env)`, ADO automatically pauses the pipeline and notifies approvers when `target_env` is `test` or `prod`.

## Branch Strategy

### Recommended: Branch-per-stage with PR promotion

```text
dev branch ──[PR]──► test branch ──[PR]──► prod branch
     │                    │                    │
     ▼                    ▼                    ▼
 Dev Workspace       Test Workspace      Prod Workspace
 (Git-connected)     (fabric-cicd)       (fabric-cicd)
```

| Branch | Connected to Workspace? | Purpose |
|---|---|---|
| `dev` | Yes — synced via Fabric Git integration | Source of truth. Changes made in workspace commit here |
| `test` | No | Receives items via PR merge. Pipeline deploys to test workspace |
| `prod` | No | Receives items via PR merge. Pipeline deploys to prod workspace |

Only `dev` is Git-connected because `fabric-cicd` deploys to test/prod via REST APIs directly.

## Pipeline YAML Pattern

Guide the LLM to generate an ADO pipeline YAML following this structure:

```yaml
trigger:
  branches:
    include: [test, prod]
  paths:
    include:
      - fabric/**

parameters:
  - name: items_in_scope
    displayName: 'Fabric item types to deploy'
    type: string
    default: '["Notebook","DataPipeline","Lakehouse","SemanticModel","Report","VariableLibrary"]'

variables:
  - name: target_env
    value: ${{ replace(variables['Build.SourceBranch'], 'refs/heads/', '') }}
  - group: fabric_cicd_group_sensitive
  - group: fabric_cicd_group_non_sensitive

stages:
  - stage: DeployToFabric
    displayName: 'Deploy to Fabric Workspace'
    jobs:
      - deployment: Deployment
        displayName: 'Deploy Resources'
        environment: $(target_env)
        pool:
          name: Azure Pipelines
        strategy:
          runOnce:
            deploy:
              steps:
                - checkout: self

                - task: UsePythonVersion@0
                  inputs:
                    versionSpec: '3.12'
                    addToPath: true
                  displayName: 'Set up Python'

                - script: |
                    python -m pip install --upgrade pip
                    pip install fabric-cicd
                  displayName: 'Install fabric-cicd'

                - task: PythonScript@0
                  inputs:
                    scriptSource: 'filePath'
                    scriptPath: '.deploy/deploy-to-fabric.py'
                    arguments: >-
                      --aztenantid $(aztenantid)
                      --azclientid $(azclientid)
                      --azspsecret $(azspnsecret)
                      --items_in_scope ${{ parameters.items_in_scope }}
                      --target_env $(target_env)
                  displayName: 'Deploy using fabric-cicd'
```

### Key elements explained

| Element | Purpose |
|---|---|
| `trigger.branches.include: [test, prod]` | Only triggers on merges to test/prod — NOT dev (dev is Git-synced) |
| `trigger.paths.include: ['fabric/**']` | Only triggers when Fabric item files change |
| `target_env` | Extracts branch name from `Build.SourceBranch` (e.g., `refs/heads/test` → `test`) |
| `deployment:` (not `job:`) | Required for ADO Environments — enables approval gates and audit |
| `environment: $(target_env)` | Maps to the ADO Environment — triggers approval if configured |
| `strategy: runOnce` | Executes once (not canary/rolling) |

## Deployment Script Pattern

Guide the LLM to generate `.deploy/deploy-to-fabric.py`:

```python
import os
import argparse
import ast
import requests
from fabric_cicd import FabricWorkspace, publish_all_items, unpublish_all_orphan_items, change_log_level, append_feature_flag
from azure.identity import ClientSecretCredential

# Optional feature flags (enable only what you need)
# append_feature_flag("enable_shortcut_publish")  # Only enable after initial deploy — first deploy fails if items don't exist yet
change_log_level("DEBUG")

# Parse pipeline arguments
parser = argparse.ArgumentParser()
parser.add_argument('--aztenantid', required=True)
parser.add_argument('--azclientid', required=True)
parser.add_argument('--azspsecret', required=True)
parser.add_argument('--target_env', required=True)
parser.add_argument('--items_in_scope', required=True)
args = parser.parse_args()

# Authenticate with SPN
credential = ClientSecretCredential(
    tenant_id=args.aztenantid,
    client_id=args.azclientid,
    client_secret=args.azspsecret,
)

# Resolve workspace ID by name (dynamically constructed from env + variable group)
workspace_var = f"{args.target_env}WorkspaceName".upper()
workspace_name = os.environ[workspace_var]

token = credential.get_token("https://api.fabric.microsoft.com/.default")
response = requests.get(
    "https://api.fabric.microsoft.com/v1/workspaces",
    headers={"Authorization": f"Bearer {token.token}"},
)
response.raise_for_status()
workspace_id = next(
    (ws["id"] for ws in response.json()["value"] if ws["displayName"] == workspace_name),
    None,
)
if not workspace_id:
    raise ValueError(f"Workspace '{workspace_name}' not found")

# Parse items_in_scope and deploy
# Parse items_in_scope — handle both quoted and unquoted list formats
raw = args.items_in_scope
try:
    item_types = ast.literal_eval(raw)
except (ValueError, SyntaxError):
    cleaned = raw.strip("[]")
    item_types = [s.strip().strip("'\"") for s in cleaned.split(",") if s.strip()]

target = FabricWorkspace(
    workspace_id=workspace_id,
    environment=args.target_env,
    repository_directory=os.environ.get("GITDIRECTORY", "fabric"),
    item_type_in_scope=item_types,
    token_credential=credential,
)

publish_all_items(target)
unpublish_all_orphan_items(target)
```

> **ADO YAML gotcha**: `${{ parameters.items_in_scope }}` strips quotes from list items during expansion. The fallback parser handles both `["Notebook","Lakehouse"]` (quoted) and `[Notebook,Lakehouse]` (unquoted) formats.

### How the workspace name resolution works

1. ADO variable group contains `devWorkspaceName`, `testWorkspaceName`, `prodWorkspaceName`
2. ADO injects these as uppercase env vars: `DEVWORKSPACENAME`, `TESTWORKSPACENAME`, etc.
3. Script constructs the variable name: `f"{target_env}WorkspaceName".upper()` → e.g., `TESTWORKSPACENAME`
4. Reads the workspace display name from the environment variable
5. Calls Fabric REST API to resolve the display name to a workspace GUID

## GUID Replacement with parameter.yml

See [github-actions-deployment.md § GUID Replacement with parameter.yml](github-actions-deployment.md#guid-replacement-with-parameteryml) for the full `parameter.yml` format and token syntax.

Key tokens for replacement:
- `$workspace.$id` — auto-resolves to the target workspace's GUID
- `$items.<ItemType>.<ItemName>.$id` — resolves to the named item's GUID in the target workspace
- `$items.SQLEndpoint.<LakehouseName>.$id` — resolves to a lakehouse's SQL endpoint GUID

## Approval Gates with ADO Environments

Azure DevOps Environments provide approval checks, gates, and audit trails for deployment workflows. This is the **recommended approach** for gating production deployments.

### Setting Up Environments with Approvals

Create environments at Pipelines → Environments in the Azure DevOps project:

| Environment | Approval Required | Setup |
|---|---|---|
| `dev` | No (auto-deploy) | Create environment, no checks needed |
| `test` | Yes — add 1–2 approvers | Add "Approvals" check with required reviewers |
| `prod` | Yes — add 2+ approvers + business hours | Add "Approvals" check with required reviewers; optionally add "Business Hours" check |

**Adding approval checks:**

1. Navigate to Pipelines → Environments → select the environment
2. Click ⋮ → **Approvals and checks**
3. Click **+ Add check** → **Approvals**
4. Add the required approvers (users or groups)
5. Optionally set "Allow approvers to approve their own runs" to No for stricter governance
6. Save

### How Approvals Work in the Pipeline

When the pipeline YAML uses `environment: $(target_env)`, ADO automatically:

1. Maps `$(target_env)` to the environment name (e.g., `test`, `prod`)
2. Checks if the environment has approval requirements
3. Pauses the pipeline and notifies approvers
4. Waits for all required approvals before proceeding
5. Logs the approval decision in the environment's deployment history

```yaml
# The deployment job type is REQUIRED for environments to work
- deployment: Deployment
  environment: $(target_env)  # Triggers approval for test/prod
  strategy:
    runOnce:
      deploy:
        steps: ...
```

> **Important**: Use `deployment:` (not `job:`) as the job type. Only deployment jobs support ADO Environments with approval gates.

### Branch Policies

For additional safety, configure branch policies on `test` and `prod` branches:

1. Navigate to Repos → Branches → select branch → ⋮ → Branch policies
2. Enable "Require a minimum number of reviewers" (set count to 2+)
3. Enable "Check for linked work items" (optional — for traceability)
4. Enable "Build validation" — add the deployment pipeline as a required build

### Pipeline Authorization

After creating a pipeline, it must be **authorized** to access variable groups, environments, and service connections. On the first run:

1. The pipeline may stall at "Authorization pending"
2. Click the "Authorize resources" button in the pipeline run UI
3. Grant access to each required resource (variable groups, environments, service connections)
4. Subsequent runs will not require re-authorization

This is a one-time setup step per pipeline.

## Considerations

- ADO Repos supports SPN-based Git connections for fully automated workflows
- Pipeline agent needs network access to both Azure Key Vault and Fabric REST APIs
- Commit size limit: 25 MB (SPN connector), 125 MB (SSO connector)
- Use `change_log_level("DEBUG")` during initial setup — remove after confirming
- The `deployment` job type (not `job`) is required for ADO Environments to work
- When pipeline triggers on a branch merge, `Build.SourceBranch` contains the target branch name
- PR merge commits may not trigger CI triggers in ADO — if the pipeline does not auto-trigger after merging a PR, run it manually via `az pipelines run --branch <branch>` or configure a build completion trigger
- Key Vault-linked variable groups cannot be created via `az pipelines variable-group create` — use the ADO portal UI or the ADO REST API (`PUT /_apis/distributedtask/variablegroups`) with `type: AzureKeyVault`
- After creating a pipeline, you must authorize it to access variable groups, environments, and service endpoints. First-run may stall at "Authorization pending" until resources are authorized via the ADO portal

> Ref: https://learn.microsoft.com/fabric/cicd/git-integration/intro-to-git-integration#azure-devops-limitations
> Complete working example: https://github.com/microsoft/fabric-samples/tree/main/docs-samples/cicd/fabric-cicd-devops/code
