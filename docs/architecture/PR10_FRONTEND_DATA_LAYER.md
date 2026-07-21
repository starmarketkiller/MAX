# PR10 — Frontend data layer

## Fault isolation

Dashboard resources settle independently. A failed analytics, health or settings
request preserves the last valid state of every other resource and produces a
visible partial-data warning instead of blanking the page.

## Visibility-aware polling

`useVisiblePolling` stops network intervals while `document.visibilityState` is
hidden and refreshes immediately when the tab becomes visible. It is used by the
dashboard, settings history, live chart, LocalBridge, notifications, licensing
and proactive coach alerts.

## EA command delivery state

Dashboard commands now expose a stable ID and `PENDING` state. When the EA polls
and receives the command, the backend records `DELIVERED` and a UTC timestamp.
The frontend polls `/api/command/{id}` and displays the transition. This is a
delivery acknowledgement, not proof that the broker-side action succeeded.

## Provenance and repaired contracts

The shell labels observed live, reconstructed, ledger-derived and simulated
research data. Live chart endpoints now return the field names consumed by the
frontend (`bars`, grouped marker arrays and provenance), while retaining legacy
aliases. License summary now includes severity, active/trial state, expired count
and time to expiry.
