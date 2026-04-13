# Critical Gotchas for Fabric CI/CD

This resource documents **known deployment pitfalls** organized by item type. These are real issues discovered through extensive testing — deployments that return HTTP 200 (success) but produce broken or empty items. Read this before deploying any item type.

> **Why this matters**: A successful API response does NOT guarantee a correct deployment. Items can deploy "successfully" but be blank, misconfigured, or fail at runtime. Always validate deployments using the [Post-Deployment Validation](#post-deployment-validation-patterns) patterns at the bottom of this file.

---

## Universal Gotchas (All Item Types)

### MUST NEVER use raw REST APIs for deployment

**Never** use `updateDefinition` / `createItemWithDefinition` REST API calls to deploy items directly to workspaces. **Always** use the `fabric-cicd` Python library.

| Why | Detail |
|---|---|
| Breaks Git connections | Direct API writes to a Git-connected workspace corrupt the sync state |
| No dependency ordering | `fabric-cicd` handles deploy order (e.g., semantic models before reports); raw API calls don't |
| No GUID replacement | `parameter.yml` substitution only works through `fabric-cicd` |
| No orphan cleanup | Only `fabric-cicd` can detect and remove stale items |

### The `.platform` file `logicalId` is sacred

- The `logicalId` GUID in `.platform` is the **stable identifier** used to match items across deployments
- **Never change it** for existing items — changing it creates a duplicate instead of updating
- **Always generate a new GUID** for genuinely new items
- The `displayName` can change freely; `logicalId` must not

### Python version compatibility

`fabric-cicd` requires **Python 3.9–3.13**. Python 3.14+ is not yet supported. If `pip install fabric-cicd` fails with `No matching distribution found`, check your Python version.

---

## Notebook

### Silent blank deployment (CRITICAL)

**Symptom**: Notebook deploys successfully (HTTP 200), but when opened in Fabric it shows only `# Fabric notebook source` — all cells are missing.

**Root cause**: The FabricGitSource `.py` format is **whitespace-sensitive**. Incorrect formatting causes Fabric to silently truncate the notebook content.

**Rules for `.py` format**:

1. First line MUST be exactly `# Fabric notebook source` — no leading blank lines, no comments before it
2. A **blank line** is REQUIRED after `# Fabric notebook source`
3. A **blank line** is REQUIRED after every `# METADATA ********************` marker
4. A **blank line** is REQUIRED after every `# CELL ********************` marker
5. JSON in `# META` blocks MUST be **multi-line** (one key-value per `# META` line) — compact single-line JSON causes parsing failures

**Correct format**:

```python
# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "<lakehouse-guid>",
# META       "default_lakehouse_name": "MyLakehouse",
# META       "default_lakehouse_workspace_id": "<workspace-guid>",
# META       "known_lakehouses": [
# META         {
# META           "id": "<lakehouse-guid>"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

print("Hello from Fabric!")

# CELL ********************

# More cells...
```

**Prevention**: Use `.ipynb` format instead — it is more forgiving and doesn't have whitespace sensitivity issues. Only use `.py` format if your workflow specifically requires it.

**Detection**: After deployment, check the notebook content size. A blank notebook is ~26 bytes. Any notebook with real content should be significantly larger.

### Lakehouse binding for execution (CRITICAL)

**Symptom**: Notebook deploys correctly with full content, but `RunNotebook` job execution fails with "Job instance failed without detail error."

**Root cause**: The notebook metadata is missing `default_lakehouse` and/or `default_lakehouse_workspace_id` in the `dependencies.lakehouse` block. Having only `known_lakehouses[].id` is **not sufficient** for runtime execution.

**Required fields** (all three must be present):

| Field | Description | Example |
|---|---|---|
| `default_lakehouse` | Lakehouse item GUID | `"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"` |
| `default_lakehouse_name` | Display name of the lakehouse | `"MyLakehouse"` |
| `default_lakehouse_workspace_id` | Workspace GUID containing the lakehouse | `"11111111-2222-3333-4444-555555555555"` |

**Two approaches to handle across environments**:

| Approach | How it works | When to use |
|---|---|---|
| **A — `parameter.yml`** (deploy-time) | Hardcode dev GUIDs in notebook metadata, add all three to `parameter.yml` for replacement | When you want GUIDs baked into definitions per environment |
| **B — Variable library `%%configure`** (runtime, recommended) | Use `%%configure` in the first cell to resolve lakehouse from a variable library | When you want one notebook definition that works in all environments |

> See [variable-libraries.md § Notebooks via %%configure](variable-libraries.md#notebooks--via-configure) for the `%%configure` syntax.

---

## SemanticModel

### `definition.pbism` must be minimal

**Symptom**: Deployment fails with `Workload_FailedToParseFile` error.

**Root cause**: The `definition.pbism` file contains properties beyond the minimum required. Properties like `enablePowerBiDataSourceApp` are rejected by the Fabric parser.

**Fix**: Use exactly this content for `definition.pbism`:

```json
{"version":"1.0","settings":{}}
```

No additional properties. No extra whitespace required (compact JSON is fine for this file).

### TMDL vs TMSL format

- **Prefer TMDL** format over TMSL for semantic model definitions
- TMDL is a tree of files (`definition/*.tmdl`) that are human-readable and Git-friendly
- TMSL is a single `model.bim` JSON file — harder to diff and review
- `fabric-cicd` supports both, but TMDL is the modern standard

### Dependency ordering

`fabric-cicd` automatically deploys semantic models **before** reports. Do not attempt to control deployment order manually.

---

## Report

### Report creation is complex

- Reports use the PBIR definition format, which is complex and best generated by Power BI Desktop
- **Do not attempt to author report definitions manually** — create reports in Power BI Desktop, commit to Git, and deploy via `fabric-cicd`
- PBIR format requires `definition.pbir` with `byConnection` reference (not `byPath`)

### Autobinding handles cross-stage references

When deploying reports via **deployment pipelines**, reports automatically rebind to the paired semantic model in the target stage. When using **`fabric-cicd`**, use `parameter.yml` to replace the semantic model connection GUID.

---

## Lakehouse

### SQL endpoint is auto-created

When deploying a Lakehouse via deployment pipelines, an associated **SQLEndpoint** is automatically created in the target workspace. This means the target workspace may have one more item than the source.

### Shortcuts require feature flags

To deploy Lakehouse shortcuts:
1. Enable `enable_shortcut_publish` feature flag
2. The Lakehouse definition must include `shortcuts.metadata.json`
3. **Do not enable on first deployment** — shortcut targets may not exist yet in the target workspace
4. Use `continue_on_shortcut_failure` if shortcut targets are created in deployment order

### Tables API is unreliable for verification

Tables created by `saveAsTable()` in notebooks may not surface via `GET .../lakehouses/{id}/tables`. Use **notebook-based validation** to verify data exists, not the REST API.

---

## DataPipeline

### Activity references to other items

Pipelines that reference other items (notebooks, lakehouses, other pipelines) contain GUIDs that differ per environment. Use `parameter.yml` for deploy-time replacement or variable libraries with `@pipeline().libraryVariables.<VarName>` for runtime resolution.

---

## VariableLibrary

### Active value set is NOT part of the definition

- Deploying a variable library to a new workspace activates the **default** value set
- You must **set the active value set** via API after first deployment to each target workspace
- The active value set persists across subsequent deployments — set it once, it stays correct
- See [variable-libraries.md § Setting Active Value Set via API](variable-libraries.md#setting-active-value-set-via-api)

### `ReferencedEntityAccessDenied` on deploy

If a variable library contains **item reference** or **connection reference** variables, the deploying SPN must have **read access** to every referenced item and connection. Without this, deployment fails with `ReferencedEntityAccessDenied`.

---

## Environment

### Custom libraries and Spark compute

Environment items include `environment.yml` (custom library specs) and `Sparkcompute.yml` (compute configuration). These are specific to the Spark pool configuration and may need adjustment per environment.

---

## Warehouse

### Data is not deployed

Warehouse items deploy **structure only** (metadata, configurations). Data must be loaded separately post-deployment via pipelines, notebooks, or COPY INTO statements.

### Orphan cleanup requires feature flag

`unpublish_all_orphan_items()` will **not** delete orphan Warehouses unless `enable_warehouse_unpublish` feature flag is enabled. This prevents accidental data loss.

---

## Eventhouse / KQL Database

### Orphan cleanup requires feature flags

Similar to Warehouse:
- `enable_eventhouse_unpublish` — enables deletion of orphan Eventhouses
- `enable_kqldatabase_unpublish` — enables deletion of orphan KQL Databases

Without these flags, `unpublish_all_orphan_items()` warns but skips these item types.

---

## CopyJob

### Connection references

Copy jobs contain source and destination connection references that differ per environment. Use variable libraries with connection reference variables to manage these across stages.

---

## Deployment Pipeline-Specific Gotchas

### First deploy may fail with `WorkloadUnavailable`

**Symptom**: `Alm_InvalidRequest_WorkloadUnavailable` error on the first deployment after assigning workspaces to pipeline stages.

**Root cause**: Workload services (Lakehouse, Notebook) need 60–120 seconds to initialize after workspace assignment.

**Fix**: Wait 60–120 seconds after workspace assignment before the first deploy. Alternatively, deploy PBI items first (SemanticModel, Report), then Fabric-native items after a short delay. Subsequent deploys work reliably.

### Concurrency constraint

Only one deployment pipeline operation can run at a time per pipeline. If you get `WorkspaceMigrationOperationInProgress` (HTTP 400), wait for the current operation to complete before retrying.

### Operation ID extraction

The deploy call returns `202 Accepted` with the operation ID in the `x-ms-operation-id` response header. With `az rest`, this is in stderr when using `--verbose`. For reliable header capture in automation, use Python `requests` or `curl -i` instead.

### `note` field is write-only

The `note` field in deploy requests is accepted but **not retrievable** via REST API. Notes are visible only in the Fabric portal UI. For programmatic audit trails, log deployment metadata in CI/CD pipeline logs or Git commit messages.

---

## Post-Deployment Validation Patterns

Always validate deployments. A successful API response does not guarantee correctness.

### Tier 1 — Item Existence

Verify items exist in the target workspace:

```bash
az rest --method get \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<workspaceId>/items" \
  --query "value[].{name:displayName, type:type}" -o table
```

### Tier 2 — Content Verification (Notebooks)

For notebooks, verify the content is not blank by checking definition size:

```bash
# Get notebook definition — check payload size
az rest --method post \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<wsId>/items/<itemId>/getDefinition"
```

A blank notebook produces a payload of ~26 bytes (just `# Fabric notebook source`). Any notebook with real content should be significantly larger. Decode the Base64 payload and verify it contains actual cell content.

### Tier 3 — Execution Verification

Run key notebooks or pipelines programmatically to verify they execute correctly:

```bash
# Trigger notebook execution
az rest --method post \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/workspaces/<wsId>/items/<notebookId>/jobs/instances?jobType=RunNotebook"
```

Poll the job status until completion. A `Failed` status indicates configuration issues (missing lakehouse binding, missing connections, etc.).

### Tier 4 — Data Verification

For items that produce data (notebooks writing to lakehouses), verify data exists. **Do not rely on the Lakehouse Tables REST API** — it may return empty results for Spark-managed tables. Instead, run a validation notebook that:

1. Reads expected tables with `spark.read.table()`
2. Checks row counts are > 0
3. Validates expected columns exist
4. Prints a pass/fail summary

This is the most reliable verification method.
