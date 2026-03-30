# Local Deployment with fabric-cicd

This resource covers deploying Fabric items from a local development environment using the `fabric-cicd` Python library.

> Ref: https://learn.microsoft.com/fabric/cicd/tutorial-fabric-cicd-local

## When to Use

- Developer testing items locally before pushing to shared environments
- Quick iteration on notebooks, pipelines, or semantic models
- Validating item definitions work correctly in a Fabric workspace
- Learning and prototyping CI/CD patterns before formalizing in a pipeline

## Prerequisites

- Python 3.9–3.13
- Azure CLI for authentication (`az login`)
- A Fabric workspace with capacity assigned
- Admin or Member permissions on the target workspace
- Item definitions in a local directory following the Fabric Git source format

## Workflow Principles

### Repository Structure

Fabric items in the local repo must follow the Git source code format. Each item lives in its own folder with definition files:

```text
fabric_items/
├── MyNotebook.Notebook/
│   ├── .platform
│   └── notebook-content.py
├── MyLakehouse.Lakehouse/
│   └── .platform
└── parameter.yml           # Optional: GUID replacement
```

> Ref: https://learn.microsoft.com/fabric/cicd/git-integration/source-code-format

The `.platform` file contains item metadata (type, display name, logical ID). The remaining files contain the item definition.

### Authentication

For local development, use interactive authentication:

```bash
az login
# If no Azure subscriptions:
az login --allow-no-subscriptions
```

`fabric-cicd` uses `DefaultAzureCredential` from the Azure Identity SDK, which picks up the `az login` session automatically.

### Deployment Script Pattern

Guide the LLM to generate a deployment script following these principles:

1. **Import** `FabricWorkspace` and `publish_all_items` from `fabric_cicd`
2. **Set** `repository_directory` to the local path containing item folders
3. **Set** `workspace_id` — resolve by name if needed via REST API
4. **Optionally set** `environment` for parameter replacement (must match `parameter.yml` keys)
5. **Optionally set** `item_type_in_scope` to limit which item types are deployed
6. **Call** `publish_all_items()` to deploy

### Debugging

Enable debug logging to see all API calls:

```python
from fabric_cicd import change_log_level
change_log_level("DEBUG")
```

Logs are also written to `fabric_cicd.error.log` in the working directory.

> Ref: https://microsoft.github.io/fabric-cicd/latest/

## Considerations

- Local deployment uses the identity from `az login` — ensure that identity has workspace permissions
- `publish_all_items()` performs a full deployment every time — it does not diff against previous deployments
- Use `unpublish_all_orphan_items()` cautiously in local workflows — it will remove items not in your local directory
- The `environment` parameter is only needed if you are using `parameter.yml` for GUID replacement
- Item types not listed in `item_type_in_scope` are ignored — if omitted, all supported types are deployed
