# CineForge API Reference
Generated from OpenAPI `3.1.0` — **CineForge** v0.1.0
## GET /capabilities
**Summary:** Capabilities
### Responses
- **200** — Successful Response

## POST /capabilities/reload
**Summary:** Reload Capabilities
### Responses
- **200** — Successful Response

## GET /diagnostics
**Summary:** Run Diagnostics
Run full system diagnostics and return actionable report.
### Responses
- **200** — Successful Response

## GET /diagnostics/quick
**Summary:** Quick Diagnostics
Quick health check for onboarding wizard.
### Responses
- **200** — Successful Response

## GET /health
**Summary:** Health
### Responses
- **200** — Successful Response

## GET /media/{project_id}/{filename}
**Summary:** Serve Media
### Parameters
- `project_id` (path) — string **required**
- `filename` (path) — string **required**

### Responses
- **200** — Successful Response
- **422** — Validation Error

## GET /prefabs/grammars
**Summary:** List Grammars
### Responses
- **200** — Successful Response

## GET /prefabs/style-packs
**Summary:** List Style Packs
### Responses
- **200** — Successful Response

## GET /prefabs/transitions
**Summary:** List Transitions
### Responses
- **200** — Successful Response

## GET /projects
**Summary:** List Projects
### Responses
- **200** — Successful Response

## POST /projects
**Summary:** Create Project
### Request Body (`application/json`)
```json
{
  "$ref": "#/components/schemas/CreateProjectRequest"
}
```
### Responses
- **200** — Successful Response
- **422** — Validation Error

## POST /projects/import-bundle
**Summary:** Import Bundle
Import a project from a .cineforge bundle.
### Request Body (`multipart/form-data`)
```json
{
  "$ref": "#/components/schemas/Body_import_bundle_projects_import_bundle_post"
}
```
### Responses
- **200** — Successful Response
- **422** — Validation Error

## DELETE /projects/{project_id}
**Summary:** Delete Project
### Parameters
- `project_id` (path) — string **required**

### Responses
- **200** — Successful Response
- **422** — Validation Error

## GET /projects/{project_id}
**Summary:** Get Project
### Parameters
- `project_id` (path) — string **required**

### Responses
- **200** — Successful Response
- **422** — Validation Error

## PATCH /projects/{project_id}
**Summary:** Update Project
### Parameters
- `project_id` (path) — string **required**

### Request Body (`application/json`)
```json
{
  "type": "object",
  "additionalProperties": true,
  "title": "Body"
}
```
### Responses
- **200** — Successful Response
- **422** — Validation Error

## POST /projects/{project_id}/export-bundle
**Summary:** Export Bundle
Export a project as a .cineforge bundle.
### Parameters
- `project_id` (path) — string **required**

### Responses
- **200** — Successful Response
- **422** — Validation Error

## POST /projects/{project_id}/prompts/forge
**Summary:** Forge Prompt
### Parameters
- `project_id` (path) — string **required**

### Request Body (`application/json`)
```json
{
  "$ref": "#/components/schemas/ForgePromptRequest"
}
```
### Responses
- **200** — Successful Response
- **422** — Validation Error

## POST /projects/{project_id}/render
**Summary:** Render Project
### Parameters
- `project_id` (path) — string **required**

### Request Body (`application/json`)
```json
{
  "$ref": "#/components/schemas/RenderShotRequest"
}
```
### Responses
- **200** — Successful Response
- **422** — Validation Error

## POST /projects/{project_id}/sources
**Summary:** Upload Source
### Parameters
- `project_id` (path) — string **required**

### Request Body (`multipart/form-data`)
```json
{
  "$ref": "#/components/schemas/Body_upload_source_projects__project_id__sources_post"
}
```
### Responses
- **200** — Successful Response
- **422** — Validation Error

## POST /projects/{project_id}/stitch
**Summary:** Stitch Project
### Parameters
- `project_id` (path) — string **required**

### Request Body (`application/json`)
```json
{
  "$ref": "#/components/schemas/StitchRequest"
}
```
### Responses
- **200** — Successful Response
- **422** — Validation Error

## POST /projects/{project_id}/storyboard
**Summary:** Create Storyboard
### Parameters
- `project_id` (path) — string **required**

### Request Body (`application/json`)
```json
{
  "$ref": "#/components/schemas/GenerateStoryboardRequest"
}
```
### Responses
- **200** — Successful Response
- **422** — Validation Error

## POST /projects/{project_id}/treatment
**Summary:** Create Treatment
### Parameters
- `project_id` (path) — string **required**

### Request Body (`application/json`)
```json
{
  "$ref": "#/components/schemas/GenerateTreatmentRequest"
}
```
### Responses
- **200** — Successful Response
- **422** — Validation Error

## GET /routing
**Summary:** Get Routing
### Responses
- **200** — Successful Response

## PUT /routing
**Summary:** Update Routing
### Request Body (`application/json`)
```json
{
  "additionalProperties": true,
  "type": "object",
  "title": "Body"
}
```
### Responses
- **200** — Successful Response
- **422** — Validation Error

## GET /routing/profiles
**Summary:** List Profiles
### Responses
- **200** — Successful Response

## GET /stackbuilder/profiles/{profile_name}
**Summary:** Stackbuilder Profile Detail
Get detailed tradeoff data for a specific profile.
### Parameters
- `profile_name` (path) — string **required**

### Responses
- **200** — Successful Response
- **422** — Validation Error

## POST /stackbuilder/recommend
**Summary:** Stackbuilder Recommend
Get ranked profile recommendations for project constraints.
### Request Body (`application/json`)
```json
{
  "additionalProperties": true,
  "type": "object",
  "title": "Body"
}
```
### Responses
- **200** — Successful Response
- **422** — Validation Error

## GET /stackbuilder/topics
**Summary:** Stackbuilder Topics
List available topics and their default configurations.
### Responses
- **200** — Successful Response

## GET /telemetry
**Summary:** Get Telemetry
Return current session telemetry stats.
### Responses
- **200** — Successful Response

