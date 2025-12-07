# bin/browser.py
"""
Headless Browser Application.

This module provides a command-line interface to a headless Chromium browser
via Playwright. It allows navigating to URLs, clicking elements, and typing text.
The state (browser instance) is persisted in global variables to allow
sequential commands.
"""

import json
import sys
from playwright.sync_api import sync_playwright

def main(args, syscalls):
    """
    Browser App entry point.

    Supported Commands:
      - navigate <url>
      - click <id>
      - type <id> <text>
      - close

    Args:
        args (list): Command line arguments.
        syscalls (SyscallHandler): System call interface (checked for network permissions).

    Returns:
        str: JSON representation of the current DOM or an error message.
    """
    if not args:
        return json.dumps({"error": "No command provided."})

    cmd = args[0]

    # We use global variables to persist state across syscalls because import_module caches the module.
    global _browser, _page, _playwright

    # Network Check (if syscalls support it)
    if hasattr(syscalls, 'sys_net_check_access') and not syscalls.sys_net_check_access():
        return json.dumps({"error": "Network Access Denied"})

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
    Extracts a simplified DOM tree from the current page.

    Executes JavaScript in the browser context to traverse the DOM and
    generate a JSON-serializable structure suitable for LLM consumption.

    Args:
        page (playwright.sync_api.Page): The Playwright page object.

    Returns:
        dict: A dictionary containing the URL, title, and DOM tree.
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
