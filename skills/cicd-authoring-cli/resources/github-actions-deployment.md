# GitHub Actions Deployment for Fabric

This resource covers automating Microsoft Fabric deployments using GitHub Actions workflows with the `fabric-cicd` Python library.

> Ref: https://learn.microsoft.com/fabric/cicd/manage-deployment

## When to Use

- Teams using GitHub for source control and CI/CD
- Automating deployments on merge to specific branches
- Multi-environment promotion (dev → test → prod) with approval gates
- Organizations preferring GitHub-native CI/CD tooling

## Prerequisites

- GitHub repository with Fabric item definitions
- Service principal (SPN) with Fabric API access enabled
- SPN added as Member or Admin on target Fabric workspaces
- GitHub Secrets configured for SPN credentials
- Python 3.9+ available in GitHub Actions runner

## Workflow Principles

### Secret Management

Store SPN credentials as GitHub repository or environment secrets:

| Secret Name | Purpose |
|---|---|
| `AZURE_TENANT_ID` | Entra ID tenant identifier |
| `AZURE_CLIENT_ID` | SPN application (client) ID |
| `AZURE_CLIENT_SECRET` | SPN client secret value |

For production deployments, prefer **GitHub Environments** with protection rules (required reviewers, wait timer) over plain repository secrets.

### Branch Strategy

Guide the LLM to set up branch-based deployment triggers:

- **Trunk-based** (recommended with `fabric-cicd`): Single main branch, environment determined by pipeline parameter, `parameter.yml` handles GUID replacement
- **Branch-per-stage**: Separate branches (dev/test/prod), merge triggers deployment to the corresponding workspace
- Use **path filters** to trigger only when Fabric item files change (e.g., `fabric_items/**`)

### Workflow Structure Principles

A GitHub Actions workflow for Fabric CI/CD should follow this pattern:

1. **Trigger**: On push/merge to target branch (with path filter for item definition folders)
2. **Setup**: Install Python and `fabric-cicd` package
3. **Authenticate**: Create `ClientSecretCredential` from GitHub Secrets
4. **Resolve workspace**: Look up workspace ID by name via Fabric REST API
5. **Deploy**: Call `publish_all_items()` with the target workspace and environment
6. **Clean up** (optional): Call `unpublish_all_orphan_items()` to remove stale items
7. **Post-deploy** (optional): Trigger data refreshes, run validation tests

### Approval Gates

Use GitHub Environments with protection rules for production deployments:

- Create environments named `dev`, `test`, `prod` in repository settings
- Add required reviewers to `test` and `prod` environments
- Reference the environment in the workflow job to gate deployment

### Multi-Environment Pattern

For promoting across environments in a single workflow:

- Use a **matrix strategy** or **reusable workflows** to deploy to multiple workspaces
- Pass `environment` as an input parameter that maps to `parameter.yml` keys
- Use environment-specific workspace name variables

## Considerations

- GitHub Actions runners have no persistent state — install `fabric-cicd` in every run
- Use `pip install fabric-cicd` in the setup step
- SPN credentials must be rotated periodically — consider using Azure Key Vault with OIDC federation for keyless auth
- GitHub has a 50 MB commit size limit for Fabric Git integration — large items may need to be split across commits
- For GitHub Enterprise with custom domains, verify compatibility with Fabric Git integration

> Ref: https://learn.microsoft.com/fabric/cicd/git-integration/intro-to-git-integration#github-limitations
