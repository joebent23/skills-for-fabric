# Fabric Deployment Pipelines

This resource covers using Microsoft Fabric's built-in deployment pipelines for stage-to-stage content promotion.

> Ref: https://learn.microsoft.com/fabric/cicd/deployment-pipelines/intro-to-deployment-pipelines

## When to Use

- Stage-to-stage promotion within Fabric (dev → test → prod)
- Teams preferring Fabric-native tooling over external CI/CD
- Scenarios where deployment rules and autobinding handle config differences between stages
- When you want built-in change comparison, deployment history, and visual pipeline UI
- Combining with Git integration where Git is used for development and pipelines for release

## Prerequisites

- Microsoft Fabric subscription with capacity
- Workspace admin permissions
- Separate workspaces for each pipeline stage (dev, test, prod)
- Items in the development workspace to deploy

## Core Concepts

### Pipeline Structure

- Deployment pipelines have 2–10 stages (default: Development, Test, Production)
- Each stage maps to a Fabric workspace
- Content flows from earlier stages to later stages
- Items are **paired** between stages — paired items overwrite on deployment; unpaired items create copies

### Item Pairing

Pairing determines what happens during deployment:

- Items deployed from one stage to the next are automatically paired
- Paired items remain paired even if renamed
- Items added after workspace assignment are NOT automatically paired
- Unpaired items with the same name can coexist — they won't overwrite each other

### Deployment Rules

Use deployment rules to change configuration between stages:

- **Data source rules**: Point semantic models to different databases per stage
- **Parameter rules**: Set different parameter values per stage
- **Connection rules**: Change connection targets between environments

> Ref: https://learn.microsoft.com/fabric/cicd/deployment-pipelines/create-rules

### Autobinding

Fabric automatically adjusts internal references when deploying between stages. For example, a report pointing to a semantic model in the source stage will be rebound to the paired semantic model in the target stage.

## Automation via REST APIs

Deployment pipelines can be fully automated using the Fabric REST APIs:

| Operation | API Endpoint |
|---|---|
| Create pipeline | `POST /v1/deploymentPipelines` |
| List pipelines | `GET /v1/deploymentPipelines` |
| Get pipeline | `GET /v1/deploymentPipelines/{pipelineId}` |
| Get pipeline stages | `GET /v1/deploymentPipelines/{pipelineId}/stages` |
| Assign workspace | `POST /v1/deploymentPipelines/{pipelineId}/stages/{stageId}/assignWorkspace` |
| Unassign workspace | `POST /v1/deploymentPipelines/{pipelineId}/stages/{stageId}/unassignWorkspace` |
| Deploy | `POST /v1/deploymentPipelines/{pipelineId}/deploy` |
| Get deploy operation | `GET /v1/operations/{operationId}` |

> Ref: https://learn.microsoft.com/fabric/cicd/deployment-pipelines/pipeline-automation-fabric

### Deploy Request Body

The deploy request requires source and target stage IDs and optionally specific items:

```json
{
  "sourceStageId": "<source-stage-guid>",
  "targetStageId": "<target-stage-guid>",
  "items": [
    {
      "sourceItemId": "<item-guid>",
      "itemType": "Notebook"
    }
  ],
  "note": "Deploy sprint 42 changes"
}
```

Omit `items` to deploy all changed items. The deployment is an LRO — poll with `GET /v1/operations/{operationId}`.

## Combining with Git Integration

The recommended hybrid approach:

1. **Development**: Workspace connected to Git for source control and collaboration
2. **Promotion**: Use deployment pipelines to move content from dev → test → prod
3. **Changes flow**: Developers commit to Git → sync to dev workspace → deploy via pipeline to test/prod

This gives you Git-based collaboration plus Fabric-native promotion with change comparison.

## Considerations

- Deployment pipelines have a **linear structure** — content flows in one direction
- App content and settings are NOT automatically updated — use APIs separately
- Deployment rules must be configured per stage — they are not deployed with the pipeline
- Some items are preview and may have limited deployment support
- Deployment pipelines do NOT support workspaces with network access protection (inbound/outbound)
- Power BI semantic models must use Enhanced Metadata format (support for non-enhanced is retired)
- Folders are preserved during deployment — item hierarchy is maintained
- Data is NOT deployed — only item definitions (metadata, queries, configurations)

> Ref: https://learn.microsoft.com/fabric/cicd/deployment-pipelines/understand-the-deployment-process
