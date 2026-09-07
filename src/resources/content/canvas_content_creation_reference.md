# Canvas HTML Editor Allowlist: practical authoring guidance

Verified 2026-09-04 against Instructure's
[Canvas HTML Editor Allowlist](https://community.instructure.com/en/kb/articles/387066-canvas-html-editor-allowlist).
Use that source for the complete current tag, attribute, protocol, CSS, and MathML
rules; this guide is a focused working reference, not an exhaustive copied list.

## HTML and context

Canvas sanitizes authored HTML. Pages remove `object` and `embed`; discussion
replies restrict `id` attributes except certain inline-media links. Notification
emails preserve only basic formatting. Rich content that works on a page may
therefore behave differently in a reply or notification.

## CSS properties and layout

Inline `style` supports selected properties, including flex/grid layouts. Canvas
filters individual values as well: `position: fixed` and `position: sticky` are
removed. Do not assume arbitrary CSS survives saving. Prefer simple layouts that
remain readable on narrow screens.

## iframe, media, and attributes

Allowed iframe attributes and sandbox tokens are filtered. Page support for an
iframe does not imply that every context or external provider permits embedding.
Check saved markup and the destination's actual behavior when embeds matter.

## Accessible content

Use descriptive headings in a coherent hierarchy; let the Canvas page title
provide the surrounding context. Use meaningful link text, image alternatives,
table headers with `scope`, and captions/transcripts for instructional media.
Avoid color-only instructions and wide layout tables.

```html
<h2>Practice reflection</h2>
<p>Explain one decision and the evidence supporting it.</p>
<details>
  <summary>Before submitting</summary>
  <p>Check that your explanation identifies the evidence.</p>
</details>
```

## Saving and verification

Use the appropriate content planner with only the intended fields. After an
authorized apply, use the returned URL/ID. Read back saved HTML when sanitization
could affect structure, links, or media. Preserve publication and notification
settings unless the task calls for changing them. API success alone does not
verify the visual result or student access.
