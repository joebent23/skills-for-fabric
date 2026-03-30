# GitHub Actions Deployment for Fabric

This resource covers automating Microsoft Fabric deployments using GitHub Actions workflows with the `fabric-cicd` Python library.

> Ref: https://learn.microsoft.com/fabric/cicd/manage-deployment

## When to Use

- Teams using GitHub for source control and CI/CD
- Automating deployments on merge to specific branches
- Multi-environment promotion (dev → test → prod) with approval gates
- Organizations preferring GitHub-native CI/CD tooling

## Prerequisites

- GitHub repository containing Fabric item definitions in Git source format
- Service principal (SPN) with Fabric API access enabled (see [SPN Setup](#service-principal-setup))
- SPN added as Member or Admin on each target Fabric workspace
- GitHub repository secrets or environment secrets configured
- Dev workspace connected to the `dev` branch via Fabric Git integration

## Service Principal Setup

Before any automated deployment works, the SPN must be configured:

1. **Create Entra ID app registration** at https://entra.microsoft.com → App registrations
2. **Create a client secret** under Certificates & secrets (note expiry — rotate before it expires)
3. **Create the enterprise application (service principal)** — the app registration alone is not enough. Run `az ad sp create --id <appId>` to create the service principal object. This gives you the **object ID** needed for workspace role assignments.
4. **Enable tenant setting**: Fabric Admin Portal → Tenant Settings → Developer settings → "Service principals can use Fabric APIs" → Enable and add the SPN (or its security group) to the allowlist. If this setting is scoped to a specific security group, you must also add the SPN to that group: `az ad group member add --group <group-name-or-id> --member-id <spn-object-id>`
5. **Add SPN to workspaces**: In each target workspace (dev, test, prod) → Manage access → Add the SPN as **Member** or **Admin**

Without steps 4 and 5, all API calls from the SPN will return `403 Forbidden`.

## Secrets Configuration

### Repository-Level Secrets

For simple setups, add secrets at Settings → Secrets and variables → Actions → New repository secret:

| Secret Name | Value | Source |
|---|---|---|
| `AZURE_TENANT_ID` | Entra ID tenant GUID | Azure portal → Entra ID → Overview |
| `AZURE_CLIENT_ID` | SPN application (client) ID | App registration → Overview |
| `AZURE_CLIENT_SECRET` | SPN client secret value | App registration → Certificates & secrets |

### Environment-Level Secrets (Recommended for Production)

For gated deployments, create **GitHub Environments** at Settings → Environments:

| Environment | Protection Rules | Secrets |
|---|---|---|
| `dev` | None (auto-deploy) | `WORKSPACE_NAME` = `myproject-dev` |
| `test` | Required reviewers | `WORKSPACE_NAME` = `myproject-test` |
| `prod` | Required reviewers + wait timer | `WORKSPACE_NAME` = `myproject-prod` |

Add the SPN secrets (`AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`) at the repository level. Add the workspace-specific `WORKSPACE_NAME` at each environment level.

> **Note**: GitHub environments must be created before setting variables on them. Create environments via Settings → Environments in the GitHub UI, or via the API: `gh api --method PUT repos/{owner}/{repo}/environments/{name}`. Setting variables on a non-existent environment returns 404.

## Branch Strategy

### Recommended: Branch-per-stage with PR promotion

```text
dev branch ──[PR]──► test branch ──[PR]──► main/prod branch
     │                    │                      │
     ▼                    ▼                      ▼
 Dev Workspace       Test Workspace        Prod Workspace
 (Git-connected)     (fabric-cicd)         (fabric-cicd)
```

- **`dev` branch**: Connected to dev workspace via Fabric Git integration. Developers commit changes here.
- **`test` branch**: NOT connected to a workspace. Receives promoted items via PR merge. Pipeline deploys to test workspace using `fabric-cicd`.
- **`main`/`prod` branch**: NOT connected to a workspace. Receives promoted items via PR from test. Pipeline deploys to prod workspace.

Only `dev` is Git-connected because `fabric-cicd` handles deployment to test/prod via REST APIs.

> **Branch naming**: The workflow triggers on `test` and `prod` branches. GitHub creates repositories with `main` as the default branch. You should either: (a) create a separate `prod` branch and use `main` for development/integration, or (b) rename the trigger to `main` instead of `prod` and use `main` as your production branch. Choose one approach and be consistent.

### Alternative: Trunk-based with environment parameter

Single `main` branch. The workflow takes `environment` as a parameter. `parameter.yml` handles GUID replacement. Simpler branching but requires manual trigger or dispatch event for per-environment control.

## Workflow YAML Pattern

Guide the LLM to generate a workflow following this structure:

```yaml
name: Deploy Fabric Items

on:
  push:
    branches: [test, prod]
    paths:
      - 'fabric/**'
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options: [test, prod]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment || (github.ref_name == 'test' && 'test') || (github.ref_name == 'prod' && 'prod') }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install fabric-cicd
        run: pip install fabric-cicd azure-identity requests

      - name: Deploy to Fabric workspace
        env:
          AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
          AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
          AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
          WORKSPACE_NAME: ${{ vars.WORKSPACE_NAME }}
          TARGET_ENV: ${{ github.ref_name }}
          ITEMS_IN_SCOPE: '["Notebook","DataPipeline","Lakehouse","SemanticModel","Report","Environment"]'
          REPOSITORY_DIRECTORY: 'fabric'
        run: python .deploy/deploy-to-fabric.py
```

### Key elements explained

| Element | Purpose |
|---|---|
| `paths: ['fabric/**']` | Only trigger when Fabric item files change |
| `environment:` | Maps to GitHub Environment — gates deployment with approval rules |
| `workflow_dispatch` | Allows manual triggering with environment selection |
| `actions/checkout@v4` | Clones repo so `fabric-cicd` can read item definitions |
| `actions/setup-python@v5` | Installs Python on runner (stateless — must install every run) |

## Deployment Script Pattern

The deployment Python script should follow this structure. Guide the LLM to generate it with these components:

```python
import os
import sys
import json
import requests
from fabric_cicd import FabricWorkspace, publish_all_items, unpublish_all_orphan_items, change_log_level
from azure.identity import ClientSecretCredential

# Enable verbose logging for troubleshooting
change_log_level("DEBUG")

# Authenticate with SPN
credential = ClientSecretCredential(
    tenant_id=os.environ["AZURE_TENANT_ID"],
    client_id=os.environ["AZURE_CLIENT_ID"],
    client_secret=os.environ["AZURE_CLIENT_SECRET"],
)

# Resolve workspace ID by display name (do not hardcode GUIDs)
def get_workspace_id(workspace_name, credential):
    token = credential.get_token("https://api.fabric.microsoft.com/.default")
    response = requests.get(
        "https://api.fabric.microsoft.com/v1/workspaces",
        headers={"Authorization": f"Bearer {token.token}"},
    )
    response.raise_for_status()
    for ws in response.json()["value"]:
        if ws["displayName"] == workspace_name:
            return ws["id"]
    raise ValueError(f"Workspace '{workspace_name}' not found")

workspace_id = get_workspace_id(os.environ["WORKSPACE_NAME"], credential)

# Parse items in scope from environment variable
items_in_scope = json.loads(os.environ.get("ITEMS_IN_SCOPE", "[]"))

# Initialize and deploy
target = FabricWorkspace(
    workspace_id=workspace_id,
    environment=os.environ.get("TARGET_ENV", ""),
    repository_directory=os.environ.get("REPOSITORY_DIRECTORY", "."),
    item_type_in_scope=items_in_scope,
    token_credential=credential,
)

publish_all_items(target)
unpublish_all_orphan_items(target)  # Caution: removes items not in source
```

## GUID Replacement with parameter.yml

When items contain environment-specific GUIDs (workspace IDs, lakehouse IDs, SQL endpoint IDs), create a `parameter.yml` file in the repository root or `.deploy/` directory:

```yaml
find_replace:
  - find_value: "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"   # DEV workspace ID
    replace_value:
      test: "$workspace.$id"                               # Auto-resolves to test workspace ID
      prod: "$workspace.$id"                               # Auto-resolves to prod workspace ID

  - find_value: "11111111-2222-3333-4444-555555555555"     # DEV lakehouse GUID
    replace_value:
      test: "$items.Lakehouse.MyLakehouse.$id"             # Resolves to test lakehouse ID
      prod: "$items.Lakehouse.MyLakehouse.$id"             # Resolves to prod lakehouse ID

  - find_value: "66666666-7777-8888-9999-000000000000"     # DEV SQL endpoint GUID
    replace_value:
      test: "$items.Lakehouse.MyLakehouse.$sqlendpointid"  # Resolves to test SQL endpoint ID
      prod: "$items.Lakehouse.MyLakehouse.$sqlendpointid"  # Resolves to prod SQL endpoint ID
```

**Token syntax**: `$items.<ItemType>.<ItemName>.$id` dynamically resolves to the matching item's GUID in the target workspace. Use `$sqlendpointid` instead of `$id` to resolve a lakehouse's SQL endpoint GUID.

The `environment` parameter passed to `FabricWorkspace()` must match a key in `replace_value` (e.g., `test`, `prod`).

## Considerations

- GitHub Actions runners are stateless — install `fabric-cicd` in every run
- SPN credentials should be rotated before expiry. Consider OIDC federation (GitHub → Azure) for keyless auth
- GitHub has a 50 MB commit size limit for Fabric Git integration
- Path filters prevent unnecessary pipeline runs when non-Fabric files change
- For GitHub Enterprise with custom domains, verify compatibility with Fabric Git integration

> Ref: https://learn.microsoft.com/fabric/cicd/git-integration/intro-to-git-integration#github-limitations
