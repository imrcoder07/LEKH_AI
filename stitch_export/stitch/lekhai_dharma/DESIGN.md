# Design System Strategy: The Digital Ledger

## 1. Overview & Creative North Star
**Creative North Star: "The Modern Archivist"**

This design system moves away from the sterile, "template-driven" look of traditional government portals. Instead, it adopts the persona of a high-end editorial archive. We are moving beyond "blue boxes" to create a sense of **Immutable Authority.**

The visual language is rooted in "Organic Structuralism." We use the stability of Deep Navy to ground the experience, but we break the rigid digital grid through intentional asymmetry—such as oversized typography headers paired with compact, bilingual data clusters. By using layered surfaces and wide-open gutters, we create an environment that feels lightweight yet impossible to breach.

## 2. Colors: Tonal Depth over Line-Work
Our palette is anchored by `primary` (#1A237E) and `surface` (#F9F9F9), but its sophistication comes from how we nest these tones.

### The "No-Line" Rule
**Strict Mandate:** Designers are prohibited from using 1px solid borders to section content. Boundaries must be defined solely through background shifts.
*   **Surface Hierarchy:** To define a card or a section, place a `surface-container-lowest` (#FFFFFF) element on top of a `surface` (#F9F9F9) background.
*   **The Glass & Gradient Rule:** For floating navigation or bilingual toggle bars, use a semi-transparent `surface` color with a 12px `backdrop-blur`. Main CTAs should utilize a subtle linear gradient from `primary` (#000666) to `primary-container` (#1A237E) at a 135-degree angle to provide a "forged" metallic depth.

### Key Tokens
*   **Primary (Authority):** `#000666` (On-Primary: `#FFFFFF`)
*   **Surface (Ash Grey):** `#F9F9F9`
*   **Tertiary (The Emerald Pulse):** `#002103` (Used for "Record Valid" states)
*   **Error (The Alert):** `#BA1A1A` (Used for "Hash Mismatch")

## 3. Typography: Editorial Authority
We utilize **Inter** for English and **Noto Sans** for Hindi. The hierarchy is designed to handle the visual density difference between the two scripts.

*   **Display-LG (3.5rem):** Used for primary landing headlines. Tight letter-spacing (-0.02em).
*   **Headline-MD (1.75rem):** The standard for bilingual section headers. Hindi text should be scaled to 110% of the English font size to maintain optical weight balance.
*   **Body-LG (1rem):** The "Workhorse." Used for deed summaries and legal text.
*   **Label-MD (0.75rem):** All-caps (English only) or Bold (Hindi) for metadata like "HASH ID" or "TIMESTAMP."

## 4. Elevation & Depth: Tonal Layering
Traditional shadows are too "dirty" for a clean GovTech interface. We use light to imply security.

*   **The Layering Principle:** Depth is achieved by stacking `surface-container` tiers. 
    *   *Level 0:* `surface` (Background)
    *   *Level 1:* `surface-container-low` (Secondary content blocks)
    *   *Level 2:* `surface-container-lowest` (Active cards/modals)
*   **Ambient Shadows:** For floating elements like `btn_generate_65b`, use a "Navy Glow" shadow: `0px 20px 40px rgba(26, 35, 126, 0.08)`. This mimics light passing through deep glass.
*   **The "Ghost Border":** If accessibility requires a container edge (e.g., in high-contrast mode), use `outline-variant` at 15% opacity. Never use 100% black or grey lines.

## 5. Signature Components

### Specialized Buttons
*   **btn_upload_deed (Primary Hero):** Large scale, `primary` gradient background. Includes a "Glassmorphic" icon slot on the left.
*   **btn_verify_title (Secondary Tonal):** Uses `secondary-container` (#CFE6F2) with `on-secondary-container` (#526772) text. No border.
*   **btn_generate_65b (High-Action):** `tertiary-fixed` (#A3F69C) background. This signals a "Success/Output" action that is distinct from navigation.

### Status Indicators
*   **Hash Mismatch (Red Alert):** A `surface-container-highest` card with a 4px left-accent bar of `error` (#BA1A1A). The background should have a subtle 2% red tint.
*   **Record Valid (Green Pulse):** A `tertiary-container` chip with a soft, 2-second infinite scale animation (1.0 to 1.05) to simulate a "heartbeat" of data integrity.

### Input Fields & Bilingual Cards
*   **Bilingual Inputs:** Labels must stack (English over Hindi). The input container uses `surface-container-highest` (#E2E2E2) with no border. On focus, a 2px `surface-tint` (#4C56AF) bottom-bar appears.
*   **Cards:** Forbid divider lines. Use 32px or 48px of vertical whitespace to separate legal clauses or deed sections.

## 6. Do's and Don'ts

### Do
*   **DO** use whitespace as a functional tool. A "Clean" interface requires a 24px minimum gutter between unrelated data clusters.
*   **DO** ensure Hindi and English text are optically aligned. Hindi "Shirorekha" (top line) often makes the text look lower than English; adjust baseline offsets accordingly.
*   **DO** use `surface-bright` (#F9F9F9) to highlight the active area in a complex dashboard.

### Don't
*   **DON'T** use pure black (#000000) for text. Use `on-surface` (#1A1C1C) for a softer, more premium reading experience.
*   **DON'T** use standard "drop shadows." If a card needs to pop, increase its brightness (`surface-container-lowest`) relative to the background.
*   **DON'T** use icons without bilingual labels. Authority requires clarity; icons are secondary to the written word in legal Tech.