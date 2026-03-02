# API Reference: registration.py

**Language**: Python

**Source**: `src/openrouter/_hooks/registration.py`

---

## Functions

### init_hooks(hooks: Hooks)

Add hooks by calling hooks.register{sdk_init/before_request/after_success/after_error}Hook
with an instance of a hook that implements that specific Hook interface
Hooks are registered per SDK instance, and are valid for the lifetime of the SDK instance

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| hooks | Hooks | - | - |

**Returns**: (none)


