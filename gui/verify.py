from playwright.sync_api import sync_playwright

def verify_monochrome(page):
    page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
    page.on("pageerror", lambda err: print(f"Browser Error: {err}"))

    try:
        page.goto("http://localhost:1420")

        # Wait a bit to let things load
        page.wait_for_timeout(2000)

        # Take screenshot regardless of selector success
        page.screenshot(path="/home/jules/verification/monochrome_verify.png")

        # Check for specific text
        if page.get_by_text("LooP").count() > 0:
            print("Found 'LooP' text.")
        else:
            print("'LooP' text NOT found.")

    except Exception as e:
        print(f"Script Error: {e}")
        page.screenshot(path="/home/jules/verification/error_verify.png")

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_monochrome(page)
        finally:
            browser.close()
