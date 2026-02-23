# Architecture Violations Demo

This directory contains examples demonstrating architecture violations and their fixes.

## Structure

- `bad/` - Example project with architecture violations
- `good/` - Same project with violations fixed

## Violations in `bad/`

### 1. Layer Violation

**File:** `myproject/types/models.py`

**Violation:** Types layer (index 0) imports from Service layer (index 3).

```python
# VIOLATION: Importing from higher layer
from myproject.service.utils import format_name
```

**Fix:** Move the formatting logic to the types layer or have the service layer use the types directly.

### 2. Provider Violation

**File:** `myproject/providers/bad_provider.py`

**Violation:** Provider imports from Service layer (business logic).

```python
# VIOLATION: Provider importing from business logic layer
from myproject.service.utils import format_name
```

**Fix:** Providers should only import from types/config layers, not business logic.

## Running the Linter

```bash
# Check the bad example (should find violations)
cd bad
python -m harness_linter.cli -v

# Check the good example (should pass)
cd good
python -m harness_linter.cli -v
```

## Expected Output

### Bad Example

```
Checking layer dependencies...
  Layer Dependency Contract: FAILED
    - myproject.types.models imports myproject.service.utils - Layer 'types' (index 0) cannot import from layer 'service' (index 3)

Checking provider usage...
  Provider Usage Contract: FAILED
    - myproject.providers.bad_provider imports myproject.service.utils - Provider 'myproject.providers.bad_provider' imports from business logic layer 'service'

Violations found!
```

### Good Example

```
Checking layer dependencies...
  Layer Dependency Contract: OK

Checking provider usage...
  Provider Usage Contract: OK

No violations found.
```
