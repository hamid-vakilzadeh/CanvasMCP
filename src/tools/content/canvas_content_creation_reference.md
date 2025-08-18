Looking through the document carefully, I found some formatting issues and missing elements. Here's the corrected version:

# Canvas HTML Editor Allowlist

This document lists the HTML codes that are permissible in Canvas.

## Allowed HTML Tags

a, acronym, address, area, article, aside, audio, b, bdo, big, blockquote, br, caption, cite, code, col, colgroup, dd, del, details, dfn, div, dl, dt, em, embed, footer, h2, h3, h4, h5, h6, header, hr, i, img, ins, iframe, kbd, legend, li, map, nav, object, ol, p, param, picture, pre, q, ruby, rp, rt, samp, section, small, span, strike, strong, sub, summary, sup, table, tbody, td, tfoot, th, thead, time, tr, track, tt, u, ul, var, video

## MathML tags

annotation, annotation-xml, maction, maligngroup, malignmark, math, menclose, merror, mfenced, mfrac, mglyph, mi, mlabeledtr, mlongdiv, mmultiscripts, mn, mo, mover, mpadded, mphantom, mprescripts, mroot, mrow, ms, mscarries, mscarry, msgroup, msline, mspace, msqrt, msrow, mstack, mstyle, msub, msubsup, msup, mtable, mtd, mtext, mtr, munder, munderover, none, semantics, mark

## Allowed Attributes on HTML Elements

*all elements allow style, class, id, title, role, lang, dir*

| Element | Allowed Attribute(s) |
|---------|---------------------|
| **a** | href, target, name |
| **abbr** | title |
| **area** | alt, coords, href, shape, target |
| **aria** | labelledby, atomic, busy, controls, describedby, disabled, dropeffect, flowto, grabbed, haspopup, hidden, invalid, label, labelledby, live, owns, relevant, autocomplete, checked, disabled, expanded, haspopup, hidden, invalid, label, level, multiline, multiselectable, orientation, pressed, readonly, required, selected, sort, valuemax, valuemin, valuenow, valuetext |
| **audio** | name, src, muted, controls |
| **blockquote** | cite |
| **col** | span, width |
| **colgroup** | span, width |
| **embed** | name, src, type, allowfullscreen, pluginspage, wmode, allowscriptaccess, width, height |
| **font** | face, color, size |
| **img** | align, alt, height, src, title, usemap, width |
| **iframe** | src, width, height, name, align, allowfullscreen |
| **map** | name |
| **object** | width, height, style, data, type, classid, codebase |
| **ol** | start, type |
| **param** | name, value |
| **q** | cite |
| **source** | Height, media, sizes, src, srcset, type, width |
| **table** | summary, width, border, cellpadding, cellspacing, center, frame, rules |
| **tr** | align, valign, dir |
| **td** | abbr, axis, colspan, rowspan, width, align, valign, dir |
| **th** | abbr, axis, colspan, rowspan, width, align, valign, dir, scope |
| **ul** | type |
| **video** | name, src, allowfullscreen, muted, poster, width, height, controls, playsinline |

## Allowed protocols for some elements

**ftp, http, https, mailto**
- a href

**http, https**
- blockquote cite
- img src
- q cite
- object data
- embed src
- iframe src
- style any

**skype**
- href

## Allowed style properties

background, border, border-radius, clear, color, cursor, direction, display, flex, float, font, grid, height, left, line-height, list-style, margin, max-height, max-width, min-height, min-width, overflow, overflow-x, overflow-y, padding, position, right, text-align, table-layout, text-decoration, text-indent, top, vertical-align, visibility, white-space, width, z-index, zoom

---
