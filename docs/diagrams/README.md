# MeterDesk Diagrams

This directory keeps diagram assets used by the project docs.

## Current Workflow

- `.svg` files are the rendered assets shown in `README.md` and interview docs.
- `.mmd` files are Mermaid references for the same concepts.
- The SVG files are not required to be a literal Mermaid render. They can be reorganized for readability while the `.mmd` files preserve a compact, editable source of the diagram meaning.

## MeterDesk Diagram Tokens

Use a small token set instead of one-off SVG colors. The current SVGs are hand-authored, but they should still follow a consistent system inspired by common design-token approaches such as Tailwind theme variables, Primer primitives, Carbon color roles, and Open Props.

| Role | Value | Usage |
| --- | --- | --- |
| Background | `#f7f8fb` | Full SVG canvas |
| Surface | `#ffffff` | Neutral cards and participants |
| Surface muted | `#fbfcfe` | Secondary callouts |
| Text | `#18212f` | Titles and primary labels |
| Text muted | `#64748b` | Captions and helper labels |
| Runtime badge | `#18212f` | Small label strips for backend-owned boundaries |
| Text on dark | `#ffffff` | Labels inside dark badges |
| Border | `#d7dde7` | Neutral card strokes and lifelines |
| Primary | `#3167b1` | Main workflow arrows and trusted boundaries |
| Primary tint | `#e8f1fc` | Selected or primary surfaces |
| Success | `#1f9d7a` | Approved or persisted-safe states |
| Success tint | `#e8f8f3` | Approved state fills |
| Warning | `#b7791f` | Pending approval and mock-only boundaries |
| Warning tint | `#fff7e6` | Pending or cautionary fills |
| Danger | `#991b1b` | Blocked mutation paths |
| Danger tint | `#fef2f2` | Blocked state fills |

Default shape and line rules:

- Card radius: `6px` for nested modules, `8px` for cards and callouts.
- Normal stroke: `1.5px`; emphasized stroke: `1.8px` to `2px`.
- Primary arrows: solid `#3167b1`, `2px`.
- Secondary arrows: dashed `#64748b`, `1.6px`, `6 5` dash pattern.
- Danger arrows: solid `#991b1b`, `2px`.
- Connector labels should not sit directly on top of connector paths; prefer putting repeated meaning inside the connected node or offsetting the label with clear spacing.
- Titles: `28px` to `30px`, weight `700`.
- Labels: `13px` to `16px`, weight `700`.
- Body text: `12px` to `13px`, weight `400`.
- Font stack: `Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Arial, sans-serif`.

## Styling Options

Use one of these approaches when changing diagram style:

1. **Hand-authored SVG styling**
   - Edit the `<style>` block inside each SVG.
   - Best for portfolio-grade diagrams where layout and visual hierarchy matter.
   - Keep colors, font sizes, stroke widths, and rounded corners consistent across files.

2. **Mermaid-generated SVG**
   - Add Mermaid CLI (`mmdc`) and a theme config or CSS file.
   - Best when exact source-to-output reproducibility matters more than custom layout.
   - Regenerate SVGs from `.mmd` files after edits.

3. **Design-tool source**
   - Maintain diagrams in Figma, Excalidraw, or a similar tool and export SVGs.
   - Best for polished visual style.
   - Requires tracking the source file or documenting where it lives, otherwise the SVG becomes hard to maintain.

For this repo, the preferred default is hand-authored SVG plus Mermaid reference: it keeps README visuals readable while preserving the diagram logic in text.
