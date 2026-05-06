# Fixes

The SoftwareONE Design System was originally built for the Marketplace Platform,
where components run inside a host application that provides certain global styles
and browser APIs. Extension UIs run in isolated iframes, so some of these
assumptions do not hold.

The fixes in this directory bridge that gap. They will be absorbed into future
versions of the SDK so that extensions work correctly out of the box. Until then
we keep them here explicitly rather than hiding them, so it is clear what is
being patched and why.

| File | What it fixes |
|------|---------------|
| `global-styling.scss` | Adds `box-sizing: border-box` and base typography that the platform provides globally but the iframe does not. |
| `wizard.scss` | Wizard step circles rely on `line-height` for sizing and `vertical-align` for icon centering, both of which break when the global `*` rule overrides inherited values. Switches to explicit `height` and flex centering. |
| `modal-layout.scss` | Reproduces the Modal component's internal layout (header with gradient border, content area, action footer) for Plugs rendered inside platform modals via iframe, where the Modal component itself is not used. |
| `safe-storage.ts` | Provides an in-memory fallback for `localStorage` and `sessionStorage`, which may be blocked by the browser's third-party storage policy inside cross-origin iframes. |
