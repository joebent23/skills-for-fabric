# skills-for-fabric Tests

This folder contains tests for validating skills-for-fabric.

## Test Categories

| Marker | Description | External Deps |
|--------|-------------|---------------|
| `semantic` | Validates skill semantics (triggers, descriptions, naming) | None |
| `integration` | Tests against real Fabric endpoints | Azure + Fabric |
| `sqlcmd` | Tests requiring sqlcmd CLI | sqlcmd (Go) |

## Setup

### Install Dependencies

```bash
pip install -r tests/requirements-dev.txt
```

### For Integration Tests

1. **Authenticate to Azure:**
   ```bash
   az login
   ```

2. **Install sqlcmd (Go version):**
   - Windows: `winget install sqlcmd`
   - macOS: `brew install sqlcmd`
   - Linux: `apt-get install sqlcmd`

3. **Set environment variables:**
   ```bash
   # Required for all integration tests
   export FABRIC_TEST_WORKSPACE_ID="<your-workspace-guid>"
   
   # For SQL endpoint tests
   export FABRIC_TEST_WAREHOUSE_ID="<your-warehouse-guid>"
   export FABRIC_TEST_ENDPOINT="<endpoint>.datawarehouse.fabric.microsoft.com"
   export FABRIC_TEST_DATABASE="<WarehouseName>"
   
   # For Spark/Livy tests
   export FABRIC_TEST_LAKEHOUSE_ID="<your-lakehouse-guid>"
   ```

   **PowerShell:**
   ```powershell
   $env:FABRIC_TEST_WORKSPACE_ID = "<your-workspace-guid>"
   $env:FABRIC_TEST_WAREHOUSE_ID = "<your-warehouse-guid>"
   $env:FABRIC_TEST_ENDPOINT = "<endpoint>.datawarehouse.fabric.microsoft.com"
   $env:FABRIC_TEST_DATABASE = "<WarehouseName>"
   $env:FABRIC_TEST_LAKEHOUSE_ID = "<your-lakehouse-guid>"
   ```

## Running Tests

### All Tests
```bash
npm test
# or
python -m pytest
```

### Semantic Tests Only (No External Deps)
```bash
npm run test:semantic
# or
python -m pytest -m semantic
```

### Integration Tests Only
```bash
npm run test:integration
# or
python -m pytest -m integration
```

### Full Eval Runner
```powershell
cd tests
.\run-full-tests.ps1
```

Optional custom working folder:
```powershell
.\run-full-tests.ps1 -TestFolder C:\temp\eval-run-01
```

### Specific Test File
```bash
python -m pytest tests/test_sqldw_consumption.py -v
```

### Skip Slow Tests
```bash
python -m pytest -m "not integration"
```

## Test Structure

```
tests/
├── conftest.py                  # Shared fixtures, helpers
├── requirements-dev.txt         # Test dependencies
├── test_semantic.py             # Skill semantic validation
├── test_sqldw_consumption.py    # SQL endpoint read tests
├── test_sqldw_authoring.py      # SQL endpoint write tests
├── test_spark_consumption.py    # Livy session tests
└── test_spark_authoring.py      # Lakehouse/notebook tests
```

## Writing New Tests

### Semantic Test Example
```python
@pytest.mark.semantic
def test_my_semantic_check(all_skills):
    for skill_name, skill_data in all_skills.items():
        assert "something" in skill_data["description"]
```

### Integration Test Example
```python
@pytest.mark.integration
@pytest.mark.sqlcmd
def test_my_sql_query(fabric_config, sqlcmd_available, az_authenticated):
    if not sqlcmd_available:
        pytest.skip("sqlcmd not available")
    
    endpoint = fabric_config.get("endpoint")
    database = fabric_config.get("database")
    
    returncode, stdout, stderr = run_sqlcmd(endpoint, database, "SELECT 1")
    assert returncode == 0
```

## Notes

- Semantic tests run without any external dependencies
- Integration tests require Azure authentication and Fabric access
- Integration tests that create resources (tables, lakehouses) clean up after themselves
- Use a **dedicated test workspace** for integration tests
- Tests are idempotent and can be run multiple times

