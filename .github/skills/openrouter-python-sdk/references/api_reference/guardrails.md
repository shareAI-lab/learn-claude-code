# API Reference: guardrails.py

**Language**: Python

**Source**: `src/openrouter/guardrails.py`

---

## Classes

### Guardrails

Guardrails endpoints

**Inherits from**: BaseSDK

#### Methods

##### list(self) → operations.ListGuardrailsResponse

List guardrails

List all guardrails for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param offset: Number of records to skip for pagination
:param limit: Maximum number of records to return (max 100)
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.ListGuardrailsResponse`


##### list_async(self) → operations.ListGuardrailsResponse

List guardrails

List all guardrails for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param offset: Number of records to skip for pagination
:param limit: Maximum number of records to return (max 100)
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.ListGuardrailsResponse`


##### create(self) → operations.CreateGuardrailResponse

Create a guardrail

Create a new guardrail for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param name: Name for the new guardrail
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param description: Description of the guardrail
:param limit_usd: Spending limit in USD
:param reset_interval: Interval at which the limit resets (daily, weekly, monthly)
:param allowed_providers: List of allowed provider IDs
:param allowed_models: Array of model identifiers (slug or canonical_slug accepted)
:param enforce_zdr: Whether to enforce zero data retention
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.CreateGuardrailResponse`


##### create_async(self) → operations.CreateGuardrailResponse

Create a guardrail

Create a new guardrail for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param name: Name for the new guardrail
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param description: Description of the guardrail
:param limit_usd: Spending limit in USD
:param reset_interval: Interval at which the limit resets (daily, weekly, monthly)
:param allowed_providers: List of allowed provider IDs
:param allowed_models: Array of model identifiers (slug or canonical_slug accepted)
:param enforce_zdr: Whether to enforce zero data retention
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.CreateGuardrailResponse`


##### get(self) → operations.GetGuardrailResponse

Get a guardrail

Get a single guardrail by ID. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail to retrieve
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.GetGuardrailResponse`


##### get_async(self) → operations.GetGuardrailResponse

Get a guardrail

Get a single guardrail by ID. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail to retrieve
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.GetGuardrailResponse`


##### update(self) → operations.UpdateGuardrailResponse

Update a guardrail

Update an existing guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail to update
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param name: New name for the guardrail
:param description: New description for the guardrail
:param limit_usd: New spending limit in USD
:param reset_interval: Interval at which the limit resets (daily, weekly, monthly)
:param allowed_providers: New list of allowed provider IDs
:param allowed_models: Array of model identifiers (slug or canonical_slug accepted)
:param enforce_zdr: Whether to enforce zero data retention
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.UpdateGuardrailResponse`


##### update_async(self) → operations.UpdateGuardrailResponse

Update a guardrail

Update an existing guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail to update
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param name: New name for the guardrail
:param description: New description for the guardrail
:param limit_usd: New spending limit in USD
:param reset_interval: Interval at which the limit resets (daily, weekly, monthly)
:param allowed_providers: New list of allowed provider IDs
:param allowed_models: Array of model identifiers (slug or canonical_slug accepted)
:param enforce_zdr: Whether to enforce zero data retention
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.UpdateGuardrailResponse`


##### delete(self) → operations.DeleteGuardrailResponse

Delete a guardrail

Delete an existing guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail to delete
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.DeleteGuardrailResponse`


##### delete_async(self) → operations.DeleteGuardrailResponse

Delete a guardrail

Delete an existing guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail to delete
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.DeleteGuardrailResponse`


##### list_key_assignments(self) → operations.ListKeyAssignmentsResponse

List all key assignments

List all API key guardrail assignments for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param offset: Number of records to skip for pagination
:param limit: Maximum number of records to return (max 100)
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.ListKeyAssignmentsResponse`


##### list_key_assignments_async(self) → operations.ListKeyAssignmentsResponse

List all key assignments

List all API key guardrail assignments for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param offset: Number of records to skip for pagination
:param limit: Maximum number of records to return (max 100)
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.ListKeyAssignmentsResponse`


##### list_member_assignments(self) → operations.ListMemberAssignmentsResponse

List all member assignments

List all organization member guardrail assignments for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param offset: Number of records to skip for pagination
:param limit: Maximum number of records to return (max 100)
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.ListMemberAssignmentsResponse`


##### list_member_assignments_async(self) → operations.ListMemberAssignmentsResponse

List all member assignments

List all organization member guardrail assignments for the authenticated user. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param offset: Number of records to skip for pagination
:param limit: Maximum number of records to return (max 100)
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.ListMemberAssignmentsResponse`


##### list_guardrail_key_assignments(self) → operations.ListGuardrailKeyAssignmentsResponse

List key assignments for a guardrail

List all API key assignments for a specific guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param offset: Number of records to skip for pagination
:param limit: Maximum number of records to return (max 100)
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.ListGuardrailKeyAssignmentsResponse`


##### list_guardrail_key_assignments_async(self) → operations.ListGuardrailKeyAssignmentsResponse

List key assignments for a guardrail

List all API key assignments for a specific guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param offset: Number of records to skip for pagination
:param limit: Maximum number of records to return (max 100)
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.ListGuardrailKeyAssignmentsResponse`


##### bulk_assign_keys(self) → operations.BulkAssignKeysToGuardrailResponse

Bulk assign keys to a guardrail

Assign multiple API keys to a specific guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail
:param key_hashes: Array of API key hashes to assign to the guardrail
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.BulkAssignKeysToGuardrailResponse`


##### bulk_assign_keys_async(self) → operations.BulkAssignKeysToGuardrailResponse

Bulk assign keys to a guardrail

Assign multiple API keys to a specific guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail
:param key_hashes: Array of API key hashes to assign to the guardrail
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.BulkAssignKeysToGuardrailResponse`


##### list_guardrail_member_assignments(self) → operations.ListGuardrailMemberAssignmentsResponse

List member assignments for a guardrail

List all organization member assignments for a specific guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param offset: Number of records to skip for pagination
:param limit: Maximum number of records to return (max 100)
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.ListGuardrailMemberAssignmentsResponse`


##### list_guardrail_member_assignments_async(self) → operations.ListGuardrailMemberAssignmentsResponse

List member assignments for a guardrail

List all organization member assignments for a specific guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param offset: Number of records to skip for pagination
:param limit: Maximum number of records to return (max 100)
:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.ListGuardrailMemberAssignmentsResponse`


##### bulk_assign_members(self) → operations.BulkAssignMembersToGuardrailResponse

Bulk assign members to a guardrail

Assign multiple organization members to a specific guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail
:param member_user_ids: Array of member user IDs to assign to the guardrail
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.BulkAssignMembersToGuardrailResponse`


##### bulk_assign_members_async(self) → operations.BulkAssignMembersToGuardrailResponse

Bulk assign members to a guardrail

Assign multiple organization members to a specific guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail
:param member_user_ids: Array of member user IDs to assign to the guardrail
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.BulkAssignMembersToGuardrailResponse`


##### bulk_unassign_keys(self) → operations.BulkUnassignKeysFromGuardrailResponse

Bulk unassign keys from a guardrail

Unassign multiple API keys from a specific guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail
:param key_hashes: Array of API key hashes to unassign from the guardrail
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.BulkUnassignKeysFromGuardrailResponse`


##### bulk_unassign_keys_async(self) → operations.BulkUnassignKeysFromGuardrailResponse

Bulk unassign keys from a guardrail

Unassign multiple API keys from a specific guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail
:param key_hashes: Array of API key hashes to unassign from the guardrail
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.BulkUnassignKeysFromGuardrailResponse`


##### bulk_unassign_members(self) → operations.BulkUnassignMembersFromGuardrailResponse

Bulk unassign members from a guardrail

Unassign multiple organization members from a specific guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail
:param member_user_ids: Array of member user IDs to unassign from the guardrail
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.BulkUnassignMembersFromGuardrailResponse`


##### bulk_unassign_members_async(self) → operations.BulkUnassignMembersFromGuardrailResponse

Bulk unassign members from a guardrail

Unassign multiple organization members from a specific guardrail. [Management key](/docs/guides/overview/auth/management-api-keys) required.

:param id: The unique identifier of the guardrail
:param member_user_ids: Array of member user IDs to unassign from the guardrail
:param http_referer: The app identifier should be your app's URL and is used as the primary identifier for rankings.
    This is used to track API usage per application.

:param x_title: The app display name allows you to customize how your app appears in OpenRouter's dashboard.

:param retries: Override the default retry configuration for this method
:param server_url: Override the default server URL for this method
:param timeout_ms: Override the default request timeout configuration for this method in milliseconds
:param http_headers: Additional headers to set or replace on requests.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| self | None | - | - |

**Returns**: `operations.BulkUnassignMembersFromGuardrailResponse`



