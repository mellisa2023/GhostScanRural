# GhostScanRural
Low cost monitoring demo system/prototype that helps farmers detect possible unauthorized activity on their farms using ambient sensing and AI driven signal analysis. This prototype simulates Wifi sensing (CSI), mimicking a primitive Receive Signal Strength Indication 
Workspace
Overview
pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.

Ghost Fence AI (GhostScan AI)
Artifact at artifacts/ghost-fence. A dark-mode  Wi-Fi sensing simulation dashboard.

Key Features
Real-time face detection via TensorFlow.js BlazeFace model (runs in hidden background canvas — no video ever shown)
Video and canvas elements are positioned off-screen with position: fixed; top: -9999px — completely invisible
Webcam permission requested on load; if denied, falls back to Synthetic Demo Mode
Live metrics: Faces Detected, Signal Strength, Variance, Noise, Classification, Confidence, Zone
Zone detection (A/B/C) based on face X-position in hidden frame
Animated radar sweep, live recharts telemetry, event log
Report generation saved via /api/ghostfence/reports
Backend Routes (artifacts/api-server/src/routes/ghostfence.ts)
GET /api/ghostfence/incidents — in-memory incident log (reverse chronological)
POST /api/ghostfence/analyze-frame — Path A: accepts frame (base64 JPEG) → calls Anthropic Claude claude-sonnet-4-20250514 for human detection → if person_detected, logs incident + triggers Vapi outbound call; Path B: falls back to pixel-variance heuristic
POST /api/ghostfence/simulate-rf — logs RF incident, triggers Vapi outbound call with detection_source: "RF sensor"
POST /api/ghostfence/webhook — Vapi tool call router: handles escalate_to_security, escalate_to_police, stand_down, log_incident, check_incident_log, update_contact, system_status_check
GET /api/ghostfence/reports — fetch last 5 detection reports
POST /api/ghostfence/reports — save a detection report
Frontend Integration (artifacts/ghost-fence/src/)
hooks/use-ghost-sensor.ts: detects face count → 0 transition, captures canvas JPEG, POSTs to /api/ghostfence/analyze-frame with 30-second cooldown; exports triggerRfAlert(zone, confidence) helper
pages/Dashboard.tsx: "TRIGGER RF ALERT" button in Command Center; Incident Log table polls /api/ghostfence/incidents every 3 seconds
Express body limit raised to 10mb to handle base64 image payloads
External Integrations
Anthropic API: POST https://api.anthropic.com/v1/messages — model claude-sonnet-4-20250514, vision analysis for human detection
Vapi: POST https://api.vapi.ai/call/phone — outbound alert calls to OWNER_PHONE with detection details; tool call webhooks returned via POST /api/ghostfence/webhook
All env vars read from process.env: ANTHROPIC_API_KEY, YUHCHAT_API_KEY, ASSISTANT_ID, PHONE_NUMBER_ID, OWNER_PHONE, OWNER_NAME
Stack
Monorepo tool: pnpm workspaces
Node.js version: 24
Package manager: pnpm
TypeScript version: 5.9
API framework: Express 5
Database: PostgreSQL + Drizzle ORM
Validation: Zod (zod/v4), drizzle-zod
API codegen: Orval (from OpenAPI spec)
Build: esbuild (CJS bundle)
Structure
artifacts-monorepo/
├── artifacts/              # Deployable applications
│   └── api-server/         # Express API server
├── lib/                    # Shared libraries
│   ├── api-spec/           # OpenAPI spec + Orval codegen config
│   ├── api-client-react/   # Generated React Query hooks
│   ├── api-zod/            # Generated Zod schemas from OpenAPI
│   └── db/                 # Drizzle ORM schema + DB connection
├── scripts/                # Utility scripts (single workspace package)
│   └── src/                # Individual .ts scripts, run via `pnpm --filter @workspace/scripts run <script>`
├── pnpm-workspace.yaml     # pnpm workspace (artifacts/*, lib/*, lib/integrations/*, scripts)
├── tsconfig.base.json      # Shared TS options (composite, bundler resolution, es2022)
├── tsconfig.json           # Root TS project references
└── package.json            # Root package with hoisted devDeps
TypeScript & Composite Projects
Every package extends tsconfig.base.json which sets composite: true. The root tsconfig.json lists all packages as project references. This means:

Always typecheck from the root — run pnpm run typecheck (which runs tsc --build --emitDeclarationOnly). This builds the full dependency graph so that cross-package imports resolve correctly. Running tsc inside a single package will fail if its dependencies haven't been built yet.
emitDeclarationOnly — we only emit .d.ts files during typecheck; actual JS bundling is handled by esbuild/tsx/vite...etc, not tsc.
Project references — when package A depends on package B, A's tsconfig.json must list B in its references array. tsc --build uses this to determine build order and skip up-to-date packages.
Root Scripts
pnpm run build — runs typecheck first, then recursively runs build in all packages that define it
pnpm run typecheck — runs tsc --build --emitDeclarationOnly using project references
Packages
artifacts/api-server (@workspace/api-server)
Express 5 API server. Routes live in src/routes/ and use @workspace/api-zod for request and response validation and @workspace/db for persistence.

Entry: src/index.ts — reads PORT, starts Express
App setup: src/app.ts — mounts CORS, JSON/urlencoded parsing, routes at /api
Routes: src/routes/index.ts mounts sub-routers; src/routes/health.ts exposes GET /health (full path: /api/health)
Depends on: @workspace/db, @workspace/api-zod
pnpm --filter @workspace/api-server run dev — run the dev server
pnpm --filter @workspace/api-server run build — production esbuild bundle (dist/index.cjs)
Build bundles an allowlist of deps (express, cors, pg, drizzle-orm, zod, etc.) and externalizes the rest
lib/db (@workspace/db)
Database layer using Drizzle ORM with PostgreSQL. Exports a Drizzle client instance and schema models.

src/index.ts — creates a Pool + Drizzle instance, exports schema
src/schema/index.ts — barrel re-export of all models
src/schema/<modelname>.ts — table definitions with drizzle-zod insert schemas (no models definitions exist right now)
drizzle.config.ts — Drizzle Kit config (requires DATABASE_URL, automatically provided by Replit)
Exports: . (pool, db, schema), ./schema (schema only)
Production migrations are handled by Replit when publishing. In development, we just use pnpm --filter @workspace/db run push, and we fallback to pnpm --filter @workspace/db run push-force.

lib/api-spec (@workspace/api-spec)
Owns the OpenAPI 3.1 spec (openapi.yaml) and the Orval config (orval.config.ts). Running codegen produces output into two sibling packages:

lib/api-client-react/src/generated/ — React Query hooks + fetch client
lib/api-zod/src/generated/ — Zod schemas
Run codegen: pnpm --filter @workspace/api-spec run codegen

lib/api-zod (@workspace/api-zod)
Generated Zod schemas from the OpenAPI spec (e.g. HealthCheckResponse). Used by api-server for response validation.

lib/api-client-react (@workspace/api-client-react)
Generated React Query hooks and fetch client from the OpenAPI spec (e.g. useHealthCheck, healthCheck).

scripts (@workspace/scripts)
Utility scripts package. Each script is a .ts file in src/ with a corresponding npm script in package.json. Run scripts via pnpm --filter @workspace/scripts run <script>. Scripts can import any workspace package (e.g., @workspace/db) by adding it as a dependency in scripts/package.json.
