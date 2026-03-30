# Fabric Deployment Pipelines

This resource covers using Microsoft Fabric's built-in deployment pipelines for stage-to-stage content promotion, automated via REST APIs.

> Ref: https://learn.microsoft.com/fabric/cicd/deployment-pipelines/intro-to-deployment-pipelines

## When to Use

- Stage-to-stage promotion within Fabric (dev → test → prod)
- Teams preferring Fabric-native tooling over external CI/CD
- Scenarios where deployment rules and autobinding handle config differences between stages
- When you want built-in change comparison, deployment history, and visual pipeline UI
- Combining with Git integration where Git is used for development and pipelines for release

## Prerequisites

- Microsoft Fabric subscription with capacity
- Workspace admin permissions on at least the dev stage
- Separate workspaces for each pipeline stage (dev, test, prod)
- Items in the development workspace to deploy
- For API automation: service principal with pipeline admin permissions

## Core Concepts

### Pipeline Structure

- Deployment pipelines have 2–10 stages (default: Development, Test, Production)
- Each stage maps to a Fabric workspace
- Content flows from earlier stages to later stages
- Stages can be customized (renamed, added, removed)

### Item Pairing

Pairing determines what happens during deployment — this is critical to understand:

- Items deployed from one stage to the next are automatically **paired**
- Paired items **overwrite** on subsequent deployments
- Paired items remain paired even if renamed in one stage
- Items added to a stage **after** workspace assignment are NOT paired
- Unpaired items with the same name coexist — they do NOT overwrite each other

### Deployment Rules

Deployment rules change configuration between stages. Configure these per target stage:

| Rule Type | What It Does | Example |
|---|---|---|
| **Data source** | Changes semantic model data source connection | Dev SQL → Prod SQL server |
| **Parameter** | Sets different parameter values per stage | `env=dev` → `env=prod` |
| **Default lakehouse** | Sets the default lakehouse for notebooks | Dev lakehouse → Prod lakehouse |

> Ref: https://learn.microsoft.com/fabric/cicd/deployment-pipelines/create-rules

### Autobinding

Fabric automatically adjusts internal references when deploying between stages. For example, a report pointing to a semantic model in the dev stage will be rebound to the paired semantic model in the test stage. This is automatic — no configuration needed for paired items.

## End-to-End Automation via REST APIs

### Step 1: Create a Deployment Pipeline

```bash
az rest --method post \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/deploymentPipelines" \
  --body '{
    "displayName": "MyProject Pipeline",
    "description": "Dev to Test to Prod promotion",
    "stages": [
      { "displayName": "Development", "order": 0 },
      { "displayName": "Test", "order": 1 },
      { "displayName": "Production", "order": 2 }
    ]
  }'
```

The response contains the `id` of the created pipeline.

### Step 2: Get Pipeline Stages

```bash
az rest --method get \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/deploymentPipelines/<pipelineId>/stages"
```

Returns the stage IDs. Default stages are ordered: Development (0), Test (1), Production (2).

### Step 3: Assign Workspaces to Stages

```bash
# Assign dev workspace to the Development stage
az rest --method post \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/deploymentPipelines/<pipelineId>/stages/<devStageId>/assignWorkspace" \
  --body '{ "workspaceId": "<devWorkspaceId>" }'

# Assign test workspace to the Test stage
az rest --method post \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/deploymentPipelines/<pipelineId>/stages/<testStageId>/assignWorkspace" \
  --body '{ "workspaceId": "<testWorkspaceId>" }'

# Assign prod workspace to the Production stage
az rest --method post \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/deploymentPipelines/<pipelineId>/stages/<prodStageId>/assignWorkspace" \
  --body '{ "workspaceId": "<prodWorkspaceId>" }'
```

### Step 4: Deploy Between Stages

Deploy all changed items from dev to test:

```bash
az rest --method post \
  --resource https://api.fabric.microsoft.com \
  --url "https://api.fabric.microsoft.com/v1/deploymentPipelines/<pipelineId>/deploy" \
  --body '{
    "sourceStageId": "<devStageId>",
    "targetStageId": "<testStageId>",
    "note": "Sprint 42 release to test"
  }'
```

To deploy specific items only:

```json
{
  "sourceStageId": "<devStageId>",
  "targetStageId": "<testStageId>",
  "items": [
    { "sourceItemId": "<notebookId>", "itemType": "Notebook" },
    { "sourceItemId": "<reportId>", "itemType": "Report" }
  ],
  "note": "Deploy updated notebook and report"
}
```

### Step 5: Poll for Completion

The deploy call returns `202 Accepted` with `Location` and `x-ms-operation-id` headers. Extract the operation ID and poll until complete.

**Bash polling pattern:**

```bash
# Extract operation ID from the deploy response headers
OPERATION_ID="<operation-id-from-response-header>"

# Poll loop with backoff
while true; do
  RESULT=$(az rest --method get \
    --resource https://api.fabric.microsoft.com \
    --url "https://api.fabric.microsoft.com/v1/operations/$OPERATION_ID" \
    -o json)

  STATUS=$(echo "$RESULT" | jq -r '.status')
  echo "Status: $STATUS"

  if [ "$STATUS" = "Succeeded" ]; then
    echo "Deployment complete"
    break
  elif [ "$STATUS" = "Failed" ]; then
    echo "Deployment failed:"
    echo "$RESULT" | jq '.error'
    exit 1
  fi

  # Wait before polling again (honour Retry-After if available, default 10s)
  sleep 10
done
```

**PowerShell polling pattern:**

```powershell
$operationId = "<operation-id-from-response-header>"

do {
    $result = az rest --method get `
        --resource https://api.fabric.microsoft.com `
        --url "https://api.fabric.microsoft.com/v1/operations/$operationId" `
        -o json | ConvertFrom-Json
    Write-Host "Status: $($result.status)"

    if ($result.status -eq "Failed") {
        throw "Deployment failed: $($result.error | ConvertTo-Json)"
    }
    if ($result.status -ne "Succeeded") { Start-Sleep -Seconds 10 }
} while ($result.status -ne "Succeeded")
Write-Host "Deployment complete"
```

> **Concurrency constraint**: Only one deployment pipeline operation can run at a time per pipeline. If you get `WorkspaceMigrationOperationInProgress` (HTTP 400), wait for the current operation to finish before retrying. Always poll the previous operation to completion before starting the next stage promotion.

### Complete API Reference

| Operation | Method | Endpoint |
|---|---|---|
| Create pipeline | POST | `/v1/deploymentPipelines` |
| List pipelines | GET | `/v1/deploymentPipelines` |
| Get pipeline | GET | `/v1/deploymentPipelines/{pipelineId}` |
| Delete pipeline | DELETE | `/v1/deploymentPipelines/{pipelineId}` |
| Get stages | GET | `/v1/deploymentPipelines/{pipelineId}/stages` |
| Get stage items | GET | `/v1/deploymentPipelines/{pipelineId}/stages/{stageId}/items` |
| Assign workspace | POST | `/v1/deploymentPipelines/{pipelineId}/stages/{stageId}/assignWorkspace` |
| Unassign workspace | POST | `/v1/deploymentPipelines/{pipelineId}/stages/{stageId}/unassignWorkspace` |
| Deploy | POST | `/v1/deploymentPipelines/{pipelineId}/deploy` |
| Get operation | GET | `/v1/operations/{operationId}` |

> Ref: https://learn.microsoft.com/fabric/cicd/deployment-pipelines/pipeline-automation-fabric

## Combining with Git Integration

The recommended hybrid approach:

```text
Git repo (dev branch) ◄──► Dev Workspace ──[pipeline]──► Test Workspace ──[pipeline]──► Prod Workspace
```

1. **Development**: Dev workspace connected to Git for source control and collaboration
2. **Promotion**: Deployment pipelines move content from dev → test → prod
3. **Flow**: Developers commit to Git → sync to dev workspace → compare stages → deploy via pipeline

This gives Git-based collaboration plus Fabric-native promotion with:
- Visual change comparison between stages
- Deployment history and audit trail
- Deployment rules for stage-specific configuration
- Autobinding for internal references

## Considerations

- Deployment pipelines have a **linear structure** — content flows in one direction (earlier → later stages)
- **App content and settings are NOT automatically updated** — call Power BI app update API separately
- **Deployment rules must be configured per stage** — they are not part of the deployed content
- Deployment pipelines do **NOT** support workspaces with network access protection (inbound/outbound)
- **Data is NOT deployed** — only item definitions (metadata, queries, configurations). Trigger data refreshes post-deploy
- **Folders are preserved** during deployment — item hierarchy is maintained
- Power BI semantic models must use **Enhanced Metadata** format (non-enhanced support is retired)
- Some items are in preview and may have limited deployment support

> Ref: https://learn.microsoft.com/fabric/cicd/deployment-pipelines/understand-the-deployment-process
