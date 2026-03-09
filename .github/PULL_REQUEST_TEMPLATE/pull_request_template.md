---
name: Pull Request
about: Submit changes to skills-for-fabric
title: ''
labels: ''
assignees: ''
---

## Description

<!-- Provide a clear and concise description of your changes -->

## Type of Change

<!-- Check all that apply -->

- [ ] New skill
- [ ] Skill enhancement/update
- [ ] Bug fix
- [ ] Documentation update
- [ ] CI/CD improvement
- [ ] Security fix

## Checklist

### General
- [ ] I have read [CONTRIBUTING.md](../CONTRIBUTING.md)
- [ ] My code follows the project's coding standards
- [ ] I have updated relevant documentation
- [ ] I have added tests for my changes
- [ ] All tests pass locally
- [ ] I have updated CHANGELOG.md

### Security (Required)
- [ ] No hardcoded secrets, API keys, or credentials
- [ ] I have reviewed [docs/RAI_THREAT_MODEL.md](../docs/RAI_THREAT_MODEL.md)
- [ ] Input validation implemented for external data
- [ ] Output redaction for sensitive information
- [ ] No arbitrary code execution vulnerabilities
- [ ] Tool parameters validated and sanitized

### RAI/Prompt Security (If applicable)
- [ ] Skill uses clear delimiters for user content vs instructions
- [ ] No patterns that reveal system prompts
- [ ] No patterns that bypass security controls
- [ ] Added red-team test cases for prompt injection
- [ ] Tested against common injection attacks
- [ ] Tool calls require appropriate user confirmation

### Threat Model Impact

<!-- Assess impact on each threat category -->

| Threat Category | Impact | Mitigation |
|----------------|--------|------------|
| Prompt Injection | None / Low / Medium / High | <!-- Describe mitigation --> |
| Sensitive Info Disclosure | None / Low / Medium / High | <!-- Describe mitigation --> |
| Excessive Agency | None / Low / Medium / High | <!-- Describe mitigation --> |
| Supply Chain | None / Low / Medium / High | <!-- Describe mitigation --> |
| Data Exfiltration | None / Low / Medium / High | <!-- Describe mitigation --> |

## Testing

<!-- Describe testing performed -->

### Manual Testing
<!-- Describe manual testing steps and results -->

### Automated Testing
<!-- List new tests added -->

### Red-Team Testing (for skills)
<!-- Describe prompt injection attempts tested -->

## Dependencies

<!-- List any new dependencies added and why they're needed -->

## Breaking Changes

<!-- List any breaking changes and migration guide -->

## Screenshots/Examples

<!-- If applicable, add screenshots or example outputs -->

## Additional Context

<!-- Any additional information reviewers should know -->

---

By submitting this pull request, I confirm that:
- My contribution is made under the project's license
- I have the right to submit this contribution
- I understand maintainers will review for security and quality
