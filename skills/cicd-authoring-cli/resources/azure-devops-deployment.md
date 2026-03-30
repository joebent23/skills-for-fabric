# Azure DevOps Deployment for Fabric

This resource covers automating Microsoft Fabric deployments using Azure DevOps Pipelines with the `fabric-cicd` Python library.

> Ref: https://learn.microsoft.com/fabric/cicd/tutorial-fabric-cicd-azure-devops

## When to Use

- Teams using Azure DevOps for source control and CI/CD
- Organizations with existing ADO infrastructure (Variable Groups, Key Vault integration, Environments)
- Enterprises requiring centralized approval gates and audit trails
- Teams using Azure DevOps Repos for Fabric Git integration

## Prerequisites

- Azure DevOps organization and project with Repos and Pipelines enabled
- Service principal (SPN) with Fabric API access enabled
- SPN added as Member or Admin on target Fabric workspaces
- Azure Key Vault with SPN credentials stored as secrets
- ADO Variable Group linked to Key Vault
- Dev workspace connected to a branch in the ADO repo via Fabric Git integration
- Python 3.9+ available on pipeline agent

## Workflow Principles

### Secret Management with Key Vault

Store SPN credentials in Azure Key Vault and link them to an ADO Variable Group:

| Key Vault Secret | Purpose |
|---|---|
| `aztenantid` | Entra ID tenant identifier |
| `azclientid` | SPN application (client) ID |
| `azspnsecret` | SPN client secret value |

Create a Variable Group named `fabric_cicd_group_sensitive` linked to the Key Vault. The pipeline fetches secrets at runtime without exposing them in the ADO UI.

### Non-Sensitive Variable Group

Create a second Variable Group `fabric_cicd_group` for workspace names and configuration:

| Variable | Example Value | Purpose |
|---|---|---|
| `devWorkspaceName` | `sales-analytics-dev` | Dev workspace display name |
| `testWorkspaceName` | `sales-analytics-test` | Test workspace display name |
| `prodWorkspaceName` | `sales-analytics-prod` | Prod workspace display name |
| `items_in_scope` | `["Notebook","Lakehouse","DataPipeline"]` | Item types to deploy |

### Pipeline Structure Principles

An ADO pipeline for Fabric CI/CD should follow this pattern:

1. **Trigger**: On merge to target branch (dev/test/prod) with path filter
2. **Variable Groups**: Reference both sensitive and non-sensitive groups
3. **Stage per environment**: Separate stages for dev, test, prod
4. **Environment gates**: ADO Environments with approval checks on test/prod
5. **Python setup**: Use `UsePythonVersion@0` task for Python 3.12+
6. **Install**: `pip install fabric-cicd`
7. **Execute**: Run deployment script with parameters from variable groups
8. **Post-deploy**: Trigger refreshes or validation as needed

### Approval Gates

Use ADO Environments with approval and check gates:

- Create environments named `dev`, `test`, `prod` in ADO project settings
- Add approval checks to `test` and `prod` environments
- Reference the environment in the pipeline YAML `environment: $(target_env)`
- The pipeline pauses and notifies approvers before deploying to gated environments

### Deployment Script Principles

Guide the LLM to generate a Python deployment script that:

1. **Parses arguments**: Accept SPN credentials, target environment, workspace name, and items in scope
2. **Authenticates**: Create `ClientSecretCredential` from SPN arguments
3. **Resolves workspace ID**: Call Fabric REST API `GET /v1/workspaces` and match by `displayName`
4. **Initializes FabricWorkspace**: Set workspace ID, repository directory, environment, items in scope, and token credential
5. **Deploys**: Call `publish_all_items()` then optionally `unpublish_all_orphan_items()`

### Branch Strategy

The recommended pattern from the Microsoft tutorial:

- **Dev branch** → Connected to dev workspace via Fabric Git integration
- **Test branch** → PR from dev triggers deployment to test workspace
- **Main/Prod branch** → PR from test triggers deployment to prod workspace
- Pipeline triggers on merge to each branch, deploying to the corresponding workspace

### Feature Flags

`fabric-cicd` supports feature flags for opt-in capabilities:

```python
from fabric_cicd import append_feature_flag
append_feature_flag("enable_shortcut_publish")  # Enables Lakehouse shortcut deployment
```

## Considerations

- ADO Repos Git integration supports SPN-based connections for automated workflows
- The ADO pipeline agent needs network access to both Azure Key Vault and Fabric REST APIs
- Workspace ID lookup by name is more resilient than hardcoding GUIDs — workspaces can be recreated
- Use `change_log_level("DEBUG")` during initial pipeline setup for troubleshooting
- Commit size limit for ADO connector: 25 MB (SPN), 125 MB (SSO)

> Ref: https://learn.microsoft.com/fabric/cicd/git-integration/intro-to-git-integration#azure-devops-limitations
