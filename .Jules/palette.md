## 2024-05-23 - Terminal Accessibility

**Learning:** Terminal outputs in web interfaces are often inaccessible to screen readers because they lack `role="log"` and `aria-live` regions. Adding `tabIndex={0}` allows keyboard users to scroll the output history, which is critical when the content overflows.
**Action:** Always ensure terminal-like components use `role="log"` and have focusable scroll areas.
