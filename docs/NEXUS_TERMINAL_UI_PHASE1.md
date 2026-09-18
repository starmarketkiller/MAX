# NEXUS Terminal UI Phase 1

## Scope

Phase UI-1 introduces the professional workspace shell and the four-domain Overview. It changes presentation and navigation only: no trading logic, research calculation, backend contract, authentication or MQL5 code is changed.

## Workspace navigation

The primary desktop rail contains exactly five workspaces:

| Workspace | Primary route | Existing subviews |
|---|---|---|
| Overview | `/` | Home operating summary |
| Market | `/market` | `/chart`, `/calendar` |
| Research | `/research` | `/backtest`, `/whatif`, `/strategy-analytics` |
| Execution | `/execution` | `/strategies`, `/optimizer`, `/risk`, `/local-bridge`, `/chain`, `/analytics` |
| Library | `/library` | `/knowledge`, `/journal` |

Utilities are visually separated at the bottom of the rail: Calculator, Settings, Licenses/Admin and System Status. AI Coach remains available through the workspace header and command palette. Every pre-existing route remains registered and directly addressable.

On mobile, the bottom navigation exposes Overview, Market, Research, Execution and More. More opens the complete rail, including Library, utilities and all workspace entry points.

## Workspace shell

The shared header now provides:

- current workspace title and context summary;
- source/state provenance;
- scrollable subview tabs;
- system-state shortcut;
- command palette;
- contextual-AI placeholder linking to the existing Coach;
- theme, notification, export and help controls already present.

The visual system uses opaque surfaces, thin borders and restrained active states. Ambient grids, decorative background glows, glass card blur, hover elevation and non-informative pulse rings are disabled. Dark remains the default and all colors continue to use the existing light/dark tokens.

## Overview information hierarchy

The default view starts with four equal domains:

1. **Market** — symbol, operational regime/session and honest LIVE/CACHED/DEMO/UNAVAILABLE provenance.
2. **Research** — canonical H006 identity, BORDERLINE status, E2 grade, no E3 promotion and explicit grade cap from `/api/research/hypotheses/{id}`.
3. **Execution** — EA, bridge, positions and balance/equity without missing-to-zero fallbacks.
4. **Risk** — drawdown, configured limit and reported protection state.

One `Needs Attention` list appears only when supported exceptions exist: canonical grade cap, Research API failure, non-live bridge, drawdown at 80% or more of the configured limit, active protection, DEMO source, or unavailable backend state.

Open positions remain directly visible because they include operational actions. Existing status strips, research funnel, market detail, observability, telemetry health, charts, command controls and diagnostics remain intact under the expandable `Operational detail and controls` section.

## Data behavior

- The Overview reads H006 only through the canonical Research API.
- Markdown is never read by the frontend.
- Missing values render as `—` or UNAVAILABLE.
- A Research API failure produces an explicit unavailable state and attention item; the remaining domains continue rendering.
- No synthetic live activity, Galaxy visualization or AI-thinking animation is introduced.

## Responsive behavior

- Desktop: compact 224 px workspace rail, sticky header and four-column domain grid at wide widths.
- Laptop/tablet: two-column domain grid and horizontally scrollable workspace tabs.
- Mobile: single-column domains, five-item bottom navigation, full navigation drawer through More and contained horizontal tab scrolling.
- The existing full-screen Live Chart remains a specialized legacy view; `/market` provides the shell entry and route-compatible handoff.

## Verification coverage

Automated frontend tests cover:

- exactly five primary workspaces;
- legacy-route registration and workspace mapping;
- mobile bottom navigation and active state;
- H006 BORDERLINE/E2/not-promoted rendering;
- explicit unavailable Research state;
- empty attention queue when no exception exists;
- dark default and light-mode toggle.

The production build continues to target `/app/`.

## Known limitations

- Market still uses current operational EA telemetry; no new canonical Market State exists in this phase.
- Live Chart retains its purpose-built full-screen light chart surface and is not yet visually normalized into the workstation shell.
- AI is a contextual entry point only; selected-entity/page context is not yet passed to Coach.
- Strategy Analytics still combines research and execution concerns internally.
- Workspace landing pages are navigation surfaces; their final analytical layouts belong to later phases.
