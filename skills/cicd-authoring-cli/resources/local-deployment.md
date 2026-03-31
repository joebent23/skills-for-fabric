# Local Deployment with fabric-cicd

This resource covers deploying Fabric items from a local development environment using the `fabric-cicd` Python library.

> Ref: https://learn.microsoft.com/fabric/cicd/tutorial-fabric-cicd-local

## When to Use

- Developer testing items locally before pushing to shared environments
- Quick iteration on notebooks, pipelines, or semantic models
- Validating item definitions work correctly in a Fabric workspace
- Learning and prototyping CI/CD patterns before formalizing in a pipeline
- Deploying to a personal dev workspace during active development

## Prerequisites

- Python 3.9–3.13
- Azure CLI for authentication (`az login`)
- A Fabric workspace with capacity assigned
- Admin or Member permissions on the target workspace
- Item definitions in a local directory following the Fabric Git source format

> **Python version warning**: `fabric-cicd` does not yet support Python 3.14+. If you see `No matching distribution found` when running `pip install fabric-cicd`, check your Python version. Use `py -3.13` (Windows) or `pyenv` (Linux/macOS) to select a compatible version.

## Step-by-Step Workflow

### Step 1: Install fabric-cicd

```bash
pip install fabric-cicd
```

### Step 2: Set Up Repository Structure

Fabric items in the local repo must follow the Git source code format. Each item lives in its own folder named `<DisplayName>.<ItemType>/`:

```text
fabric_items/
├── MyNotebook.Notebook/
│   ├── .platform
│   └── notebook-content.py
├── MyLakehouse.Lakehouse/
│   └── .platform
├── MyPipeline.DataPipeline/
│   ├── .platform
│   └── pipeline-content.json
├── MyModel.SemanticModel/
│   ├── .platform
│   ├── definition.pbism
│   ├── model.bim
│   └── diagramLayout.json
└── parameter.yml                    # Optional: GUID replacement
```

> Ref: https://learn.microsoft.com/fabric/cicd/git-integration/source-code-format

**Item definition formats are strict.** Each item type has specific required files and format rules. Before creating item definitions manually, always check:

1. **[ITEM-DEFINITIONS-CORE.md](../../common/ITEM-DEFINITIONS-CORE.md)** — Required parts, formats, and decoded content structure for each item type
2. **[fabric-cicd sample repo](https://github.com/microsoft/fabric-cicd/tree/main/sample/workspace)** — Verified working item definitions that `fabric-cicd` is tested against. Use these as the reference format for any item type you need to deploy
3. **Export from an existing workspace** — Connect a workspace to Git, commit items, and clone the repo to get Fabric-produced definitions in the correct format

> ⚠️ **Notebook gotcha — silent blank deployment**: The FabricGitSource `.py` format (used by `notebook-content.py`) is whitespace-sensitive. Incorrect formatting causes notebooks to deploy successfully but appear **blank** in Fabric — no error is returned. Key rules: (1) blank line after `# Fabric notebook source` header, (2) blank line after every `# METADATA ********************` and `# CELL ********************` marker, (3) JSON in `# META` blocks must be multi-line (one key per `# META` line, not compact single-line). When in doubt, use `ipynb` format instead — it is more forgiving.

### The .platform File

Every item folder must contain a `.platform` file with item metadata:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  "metadata": {
    "type": "Notebook",
    "displayName": "MyNotebook",
    "description": "Data ingestion notebook"
  },
  "config": {
    "version": "2.0",
    "logicalId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
  }
}
```

- `type`: Must match the folder suffix (e.g., `.Notebook` → `"Notebook"`)
- `displayName`: The item name shown in the Fabric workspace
- `logicalId`: A stable GUID used for matching items across deployments. Generate a new GUID for new items. Do NOT change for existing items.

### Step 3: Authenticate

For local development, use interactive authentication via Azure CLI:

```bash
az login
```

If you have no Azure subscriptions associated with your account:

```bash
az login --allow-no-subscriptions
```

`fabric-cicd` uses `DefaultAzureCredential` from the Azure Identity SDK, which picks up the `az login` session automatically. No additional token configuration is needed.

### Step 4: Create the Deployment Script

Create a `deploy.py` file:

```python
from pathlib import Path
from fabric_cicd import FabricWorkspace, publish_all_items

repo_dir = Path(__file__).resolve().parent / "fabric_items"

workspace = FabricWorkspace(
    workspace_id="<YOUR_WORKSPACE_ID>",
    repository_directory=str(repo_dir),
    # environment="DEV",                                      # Required only if using parameter.yml
    # item_type_in_scope=["Notebook", "Lakehouse"],           # Optional: limit to specific types
)

publish_all_items(workspace)
```

### Step 5: Find Your Workspace ID

To find the workspace ID, either:

**Option A — From the Fabric portal**: Open the workspace → the URL contains the workspace GUID.

**Option B — Via CLI**:

```bash
az rest --method get \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces" \
  --query "value[?displayName=='MyWorkspace'].{name:displayName, id:id}" -o table
```

### Step 6: Run the Deployment

```bash
python deploy.py
```

If successful, the items appear in your Fabric workspace. Check the workspace in the Fabric portal to verify.

### Step 7: Debug if Needed

Enable verbose logging to see all REST API calls made by `fabric-cicd`:

```python
from fabric_cicd import change_log_level
change_log_level("DEBUG")
```

Logs are also written to `fabric_cicd.error.log` in the working directory.

## Using parameter.yml for GUID Replacement

When deploying the same items to multiple environments, item definitions may contain hardcoded GUIDs (workspace IDs, lakehouse IDs, SQL endpoint IDs). Use `parameter.yml` to replace them:

```yaml
find_replace:
  - find_value: "dev-workspace-guid-here"
    replace_value:
      test: "$workspace.$id"
      prod: "$workspace.$id"

  - find_value: "dev-lakehouse-guid-here"
    replace_value:
      test: "$items.Lakehouse.MyLakehouse.$id"
      prod: "$items.Lakehouse.MyLakehouse.$id"
```

Place `parameter.yml` in the repository root or the same directory as item definitions. Then set the `environment` parameter:

```python
workspace = FabricWorkspace(
    workspace_id="<test-workspace-id>",
    repository_directory=str(repo_dir),
    environment="test",                       # Must match a key in replace_value
    item_type_in_scope=["Notebook", "Lakehouse"],
)
```

## Orphan Cleanup

To remove items from the workspace that no longer exist in your local repository:

```python
from fabric_cicd import unpublish_all_orphan_items

unpublish_all_orphan_items(workspace)
```

**Caution**: This deletes items of the types in `item_type_in_scope` from the workspace that are NOT in your local repo. Only use when your local directory represents the complete desired state for those item types.

To exclude specific items from cleanup (preserve them even if not in the repo):

```python
unpublish_all_orphan_items(workspace, item_name_exclude_regex=".*KeepThis.*")
```

## Bootstrapping from an Existing Workspace

If you already have items in a Fabric workspace and want to start managing them locally:

1. **Connect workspace to Git** (see [SKILL.md § Git Integration APIs](../SKILL.md#git-integration-apis))
2. **Commit items to Git** from the workspace via the source control panel
3. **Clone the repo** locally — your items are now in the Git source format
4. **Disconnect from Git** (optional) if you want to use `fabric-cicd` for deployments instead

Alternatively, use the **Get Item Definition** REST API to export individual items:

```bash
az rest --method post \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<wsId>/items/<itemId>/getDefinition"
```

This returns `202 Accepted` (LRO). Poll the operation, then call `GET /v1/operations/<opId>/result` to get the Base64-encoded definition parts.

## Considerations

- `publish_all_items()` performs a **full deployment** every time — it does not diff against previous deployments
- Local deployment uses the identity from `az login` — ensure that identity has workspace permissions
- The `environment` parameter is only needed if using `parameter.yml` for GUID replacement
- Item types not listed in `item_type_in_scope` are ignored — if omitted, all supported types are deployed
- The `logicalId` in `.platform` files is used to match items across deployments — changing it creates a new item instead of updating
- Item dependencies are resolved automatically by `fabric-cicd` (e.g., semantic models deploy before reports)

### Power BI Items (SemanticModel + Report)

Deploying Power BI items requires extra care. For comprehensive guidance on TMDL format, definition structure, and authoring patterns, see the [powerbi-authoring-cli skill](../../../skills/powerbi-authoring-cli/SKILL.md).

Key gotchas for CI/CD deployment:
- **`definition.pbism` must be minimal**: Use `{"version":"1.0","settings":{}}` only. Additional properties cause `Workload_FailedToParseFile` errors
- **Report creation uses PBIR format**: Author reports in Power BI Desktop, commit to Git, then deploy — the PBIR format is complex and best generated by the tool
- **Semantic model definitions**: Prefer TMDL format over TMSL. See [ITEM-DEFINITIONS-CORE.md § SemanticModel](../../common/ITEM-DEFINITIONS-CORE.md#semanticmodel) for required parts
- **`fabric-cicd` handles dependency ordering**: Semantic models deploy before reports automatically

### PowerShell Users

All `az rest --body` examples in this skill use bash JSON escaping. On Windows/PowerShell, inline JSON may fail. Use the file-reference pattern:

```powershell
# Write JSON to temp file, then reference with @
'{"displayName":"MyWorkspace","capacityId":"<capacity-id>"}' | Set-Content "$env:TEMP\body.json" -Encoding utf8NoBOM
az rest --method post --resource https://api.fabric.microsoft.com --url "https://api.fabric.microsoft.com/v1/workspaces" --body "@$env:TEMP\body.json"
```

> Ref: https://microsoft.github.io/fabric-cicd/latest/
