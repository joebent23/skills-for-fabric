"""
Shared pytest fixtures for skills-for-fabric tests.
"""
import pytest
from pathlib import Path



# =============================================================================
# Path Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def skills_dir(repo_root) -> Path:
    """Return the skills directory."""
    return repo_root / "skills"


@pytest.fixture(scope="session")
def common_dir(repo_root) -> Path:
    """Return the common directory."""
    return repo_root / "common"


# =============================================================================
# Skill Loading Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def all_skills(skills_dir) -> dict:
    """Load all skills with their frontmatter and content."""
    import yaml
    
    skills = {}
    for skill_folder in skills_dir.iterdir():
        if not skill_folder.is_dir():
            continue
        skill_md = skill_folder / "SKILL.md"
        if not skill_md.exists():
            continue
        
        content = skill_md.read_text(encoding="utf-8")
        
        # Parse YAML frontmatter
        frontmatter = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError:
                    pass
                content_body = parts[2]
            else:
                content_body = content
        else:
            content_body = content
        
        skills[skill_folder.name] = {
            "name": frontmatter.get("name", skill_folder.name),
            "description": frontmatter.get("description", ""),
            "content": content_body,
            "path": skill_md,
        }
    
    return skills


# =============================================================================
# Pytest Markers
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "semantic: tests that validate skill semantics (no external deps)")
    config.addinivalue_line("markers", "routing: tests that validate skill routing based on user prompts")
