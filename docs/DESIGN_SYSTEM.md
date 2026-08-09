# SharpStack Design System

## Philosophy

SharpStack is a dense, trustworthy analytics workstation. Shared presentation
should be restrained, readable, and consistent; prediction logic and UI remain
separate.

## Token Source

`dashboard/design/tokens.py` is the source of truth for shared CSS custom
properties. New shared components should consume these variables rather than
introducing equivalent local values. Existing page-specific styling is migrated
only in an explicitly scoped follow-up.

## Color Roles

- App background: dark slate.
- Panel and muted panel: progressively lighter dark-slate surfaces.
- Primary and secondary text: soft white and cool gray.
- Accent: electric cyan for active controls, selected controls, links, and
  focus states.
- Success: green; warning and pending: amber; negative and loss: red; neutral
  and pass: gray.

## Spacing

Use only `4px`, `8px`, `12px`, `16px`, `24px`, `32px`, and `48px` through the
`--ss-space-*` tokens for new shared layout work.

## Radius

Use `4px`, `6px`, and `8px` through `--ss-radius-sm`, `--ss-radius-md`, and
`--ss-radius-lg` for new shared controls and panels.

## Shadows

Use `--ss-shadow-panel` for a restrained elevated panel when a new shared
component requires depth.

## Typography

The approved roles are page title, section title, body, label, caption, and
metric value. Use the `--ss-font-*` tokens for new shared components.

## Sizing

Shell and shared-component sizing uses tokens for sidebar width, top-bar height,
compact/default controls, table rows, and metric-card minimum height.

## Guardrails

- Do not place page-specific visual fixes in the shared token layer.
- Do not hard-code a new shared color, spacing, radius, or component size when
  an approved token applies.
- Do not alter model, analytics, persistence, grading, or service behavior from
  presentation work.
