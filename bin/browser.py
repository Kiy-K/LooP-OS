# bin/browser.py
import json
import sys
from playwright.sync_api import sync_playwright

def main(args, syscalls):
    """
    Browser App using Playwright.
    Usage:
      run browser navigate <url>
      run browser click <id>
      run browser type <id> <text>

    Returns: JSON DOM
    """
    if not args:
        return json.dumps({"error": "No command provided."})

    cmd = args[0]

    # We need a persistent browser session?
    # The 'run' command in our shell currently is one-off.
    # To support persistence, we'd need to keep the process alive or store state.
    # For this v1, we will launch a new browser each time? That's slow.
    # Or maybe we assume the Agent calls are stateful in a sequence?
    # But 'main' exits.

    # Solution: Store browser state (context) on disk or in memory?
    # Since we are in the "Kernel" process (simulated), we can use a global or singleton?
    # No, let's keep it simple:
    # For "navigate", we fetch and return.
    # But "click" requires existing page.

    # Ideally, we should have a "BrowserService" in the Kernel.
    # But for now, let's implement a stateless "fetcher" or accept that 'navigate' is the only fully supported one
    # unless we serialize the page? Playwright doesn't work that way easily.

    # Hack: We only implement 'navigate' which returns the DOM.
    # 'click' would need to re-navigate or we need a daemon.
    # Given the constraints, let's assume 'navigate' is the primary action
    # and if the user wants to click, they might need a more complex interaction pattern
    # or we just re-load the page (stateless web).

    # Re-reading requirements: "interact with"
    # So we need state.
    # We can use a module-level variable in this file, BUT this file is imported dynamically each time?
    # No, 'import_module' caches. So global variables HERE persist across 'run' calls!

    global _browser, _page, _playwright

    try:
        if '_playwright' not in globals():
            _playwright = sync_playwright().start()
            _browser = _playwright.chromium.launch(headless=True)
            _page = _browser.new_page()

        if cmd == "navigate":
            url = args[1]
            try:
                _page.goto(url)
                return json.dumps(get_dom_tree(_page))
            except Exception as e:
                return json.dumps({"error": f"Navigation failed: {e}"})

        elif cmd == "click":
            selector = args[1] # ID or selector
            try:
                # We assume ID passed is a selector like "#id" or just "id"
                if not selector.startswith("#") and not selector.startswith("."):
                    selector = f"#{selector}"

                _page.click(selector)
                # Return new state
                return json.dumps(get_dom_tree(_page))
            except Exception as e:
                return json.dumps({"error": f"Click failed: {e}"})

        elif cmd == "type":
            selector, text = args[1], " ".join(args[2:])
            try:
                 if not selector.startswith("#") and not selector.startswith("."):
                    selector = f"#{selector}"
                 _page.fill(selector, text)
                 return json.dumps(get_dom_tree(_page))
            except Exception as e:
                return json.dumps({"error": f"Type failed: {e}"})

        elif cmd == "close":
            _browser.close()
            _playwright.stop()
            # Clean globals
            del globals()['_playwright']
            return json.dumps({"status": "closed"})

    except Exception as e:
        return json.dumps({"error": str(e)})

    return json.dumps({"error": "Unknown command"})

def get_dom_tree(page):
    """
    Extracts a simplified DOM tree from the page.
    """
    # Evaluate JS to traverse DOM and return JSON
    # We focus on interactive elements: a, button, input, textarea, form
    # and key structure: div, p, h1-h6

    js_script = """
    () => {
        function traverse(node) {
            if (node.nodeType !== Node.ELEMENT_NODE && node.nodeType !== Node.TEXT_NODE) return null;

            // Text nodes
            if (node.nodeType === Node.TEXT_NODE) {
                const text = node.textContent.trim();
                return text ? { type: "text", content: text } : null;
            }

            const tag = node.tagName.toLowerCase();
            const relevantTags = ["a", "button", "input", "textarea", "form", "div", "p", "h1", "h2", "h3", "span", "ul", "li"];

            // Filter out non-relevant tags to save space, unless they have ID?
            // Let's keep structure but maybe skip scripts/styles
            if (["script", "style", "meta", "link", "noscript"].includes(tag)) return null;

            const obj = {
                tag: tag,
                id: node.id || "",
                children: []
            };

            // Attributes for interaction
            if (tag === "a") obj.href = node.href;
            if (tag === "input") {
                obj.type = node.type;
                obj.name = node.name;
                obj.value = node.value;
            }
            if (node.className) obj.class = node.className;

            // Children
            node.childNodes.forEach(child => {
                const childObj = traverse(child);
                if (childObj) obj.children.push(childObj);
            });

            // Simplify: if element has no useful attributes and no children, drop it?
            // If it's a div with no ID and empty children, drop.
            if (tag === "div" && !obj.id && obj.children.length === 0) return null;

            return obj;
        }
        return traverse(document.body);
    }
    """
    try:
        return {"url": page.url, "title": page.title(), "dom": page.evaluate(js_script)}
    except Exception as e:
        return {"error": f"DOM Extraction failed: {e}"}
