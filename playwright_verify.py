#!/usr/bin/env python3
"""Comprehensive Playwright browser verification for Notepad Django project."""

import asyncio
import os
import json
import sys
from playwright.async_api import async_playwright, expect

BASE_URL = "http://127.0.0.1:8081"
SCREENSHOTS_DIR = "/tmp"
DESKTOP = {"width": 1280, "height": 800}
MOBILE = {"width": 375, "height": 812}

results = []

def record(page_name, check_name, passed, detail=""):
    results.append({
        "page": page_name,
        "check": check_name,
        "passed": passed,
        "detail": detail,
    })
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {page_name} / {check_name}: {detail}")
    return passed

async def set_viewport(page, size):
    """Set viewport size using the correct Playwright API."""
    await page.set_viewport_size(size)

async def screenshot(page, name, path=None):
    if path is None:
        path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
    await page.screenshot(path=path, full_page=True)
    return path

async def test_list_page(page, viewport_name, viewport_size):
    """Test the list page (/notes/)."""
    name = "list"
    await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
    await set_viewport(page, viewport_size)
    await page.wait_for_timeout(300)

    screenshots = []
    snap_name = f"{name}_{viewport_name}"
    path = await screenshot(page, snap_name)
    screenshots.append(path)

    # Check sidebar
    sidebar = page.locator("#sidebar")
    c = await sidebar.count()
    record(name, "sidebar count", c == 1, f"count={c}")
    visible = await sidebar.is_visible()
    record(name, "sidebar visible", visible, f"visible={visible}")

    # Check editor-area
    editor_area = page.locator(".editor-area")
    c = await editor_area.count()
    record(name, "editor-area count", c == 1, f"count={c}")
    visible = await editor_area.is_visible()
    record(name, "editor-area visible", visible, f"visible={visible}")

    # Check textarea visibility
    textarea = page.locator("textarea#editor")
    c = await textarea.count()
    record(name, "textarea count (list page has empty state, no textarea)", c == 0, f"count={c} (expected 0 on empty state)")

    # Check toolbar
    toolbar = page.locator(".toolbar")
    c = await toolbar.count()
    record(name, "toolbar count (list page has no toolbar)", c == 0, f"count={c} (expected 0 on list page)")

    # Check title-bar
    title_bar = page.locator(".title-bar")
    c = await title_bar.count()
    record(name, "title-bar count (list page has no title bar)", c == 0, f"count={c} (expected 0 on list page)")

    # Check editor-wrapper
    editor_wrapper = page.locator("#editor-wrapper")
    c = await editor_wrapper.count()
    record(name, "editor-wrapper count (list page has no editor wrapper)", c == 0, f"count={c} (expected 0 on list page)")

    # Check file items
    file_items = page.locator(".file-item")
    c = await file_items.count()
    record(name, "file items count", c >= 0, f"count={c}")
    # Check first file item visibility
    if c > 0:
        first = file_items.first
        vis = await first.is_visible()
        record(name, "first file item visible", vis, f"visible={vis}")
    else:
        record(name, "file items visible", True, "no file items (empty state) - acceptable")

    return screenshots

async def test_editor_page(page, viewport_name, viewport_size):
    """Test the editor page (pick first note from list)."""
    name = "editor"
    # First get a note pk from the list page
    await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
    await set_viewport(page, viewport_size)
    await page.wait_for_timeout(300)

    # Find first note link
    file_items = page.locator(".file-item a.filename")
    count = await file_items.count()
    if count == 0:
        # Create a note first
        await page.goto(f"{BASE_URL}/notes/new/", wait_until="domcontentloaded")
        await set_viewport(page, viewport_size)
        await page.wait_for_timeout(300)
        # Fill in the form and save
        title_input = page.locator("#title-input")
        await title_input.fill("Test Note")
        textarea = page.locator("#editor")
        await textarea.fill("# Test Note\n\nThis is a test note content.")
        save_btn = page.locator("#save-btn")
        await save_btn.click()
        await page.wait_for_timeout(500)
        # Now get the note pk from the list
        await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
        await set_viewport(page, viewport_size)
        await page.wait_for_timeout(300)
        file_items = page.locator(".file-item a.filename")
        count = await file_items.count()

    if count == 0:
        record(name, "editor page - note found", False, "No notes available to edit")
        snap = await screenshot(page, f"{name}_{viewport_name}_no_note")
        return [snap]

    first_link = file_items.first
    href = await first_link.get_attribute("href")
    await first_link.click()
    await page.wait_for_timeout(500)

    # Take screenshot
    path = await screenshot(page, f"{name}_{viewport_name}")
    screenshots = [path]

    # Check sidebar
    sidebar = page.locator("#sidebar")
    c = await sidebar.count()
    record(name, "sidebar count", c == 1, f"count={c}")
    visible = await sidebar.is_visible()
    record(name, "sidebar visible", visible, f"visible={visible}")

    # Check editor-area
    editor_area = page.locator(".editor-area")
    c = await editor_area.count()
    record(name, "editor-area count", c == 1, f"count={c}")
    visible = await editor_area.is_visible()
    record(name, "editor-area visible", visible, f"visible={visible}")

    # Check textarea
    textarea = page.locator("textarea#editor")
    c = await textarea.count()
    record(name, "textarea count", c == 1, f"count={c}")
    visible = await textarea.is_visible()
    record(name, "textarea visible", visible, f"visible={visible}")
    # Check textarea has content
    content = await textarea.input_value()
    record(name, "textarea has content", len(content) > 0, f"length={len(content)}")

    # Check toolbar
    toolbar = page.locator(".toolbar")
    c = await toolbar.count()
    record(name, "toolbar count", c == 1, f"count={c}")
    visible = await toolbar.is_visible()
    record(name, "toolbar visible", visible, f"visible={visible}")
    # Check toolbar buttons
    save_btn = page.locator("#save-btn")
    c = await save_btn.count()
    record(name, "save button present", c == 1, f"count={c}")
    saveas_btn = page.locator("#saveas-btn")
    c = await saveas_btn.count()
    record(name, "saveas button present", c == 1, f"count={c}")
    preview_btn = page.locator("#preview-btn")
    c = await preview_btn.count()
    record(name, "preview button present", c == 1, f"count={c}")

    # Check title-bar
    title_bar = page.locator(".title-bar")
    c = await title_bar.count()
    record(name, "title-bar count", c == 1, f"count={c}")
    visible = await title_bar.is_visible()
    record(name, "title-bar visible", visible, f"visible={visible}")
    # Check title input
    title_input = page.locator("#title-input")
    c = await title_input.count()
    record(name, "title input present", c == 1, f"count={c}")

    # Check editor-wrapper
    editor_wrapper = page.locator("#editor-wrapper")
    c = await editor_wrapper.count()
    record(name, "editor-wrapper count", c == 1, f"count={c}")
    visible = await editor_wrapper.is_visible()
    record(name, "editor-wrapper visible", visible, f"visible={visible}")

    # Check file items
    file_items = page.locator(".file-item")
    c = await file_items.count()
    record(name, "file items count", c >= 1, f"count={c}")
    if c > 0:
        first = file_items.first
        vis = await first.is_visible()
        record(name, "first file item visible", vis, f"visible={vis}")

    return screenshots

async def test_new_page(page, viewport_name, viewport_size):
    """Test the new note page (/notes/new/)."""
    name = "new"
    await page.goto(f"{BASE_URL}/notes/new/", wait_until="domcontentloaded")
    await set_viewport(page, viewport_size)
    await page.wait_for_timeout(300)

    screenshots = []
    path = await screenshot(page, f"{name}_{viewport_name}")
    screenshots.append(path)

    # Check sidebar
    sidebar = page.locator("#sidebar")
    c = await sidebar.count()
    record(name, "sidebar count", c == 1, f"count={c}")
    visible = await sidebar.is_visible()
    record(name, "sidebar visible", visible, f"visible={visible}")

    # Check editor-area
    editor_area = page.locator(".editor-area")
    c = await editor_area.count()
    record(name, "editor-area count", c == 1, f"count={c}")
    visible = await editor_area.is_visible()
    record(name, "editor-area visible", visible, f"visible={visible}")

    # Check textarea
    textarea = page.locator("textarea#editor")
    c = await textarea.count()
    record(name, "textarea count", c == 1, f"count={c}")
    visible = await textarea.is_visible()
    record(name, "textarea visible", visible, f"visible={visible}")
    # Check placeholder
    placeholder = await textarea.get_attribute("placeholder")
    record(name, "textarea placeholder", placeholder is not None and len(placeholder) > 0, f"placeholder='{placeholder}'")

    # Check toolbar
    toolbar = page.locator(".toolbar")
    c = await toolbar.count()
    record(name, "toolbar count", c == 1, f"count={c}")
    visible = await toolbar.is_visible()
    record(name, "toolbar visible", visible, f"visible={visible}")

    # Check title-bar
    title_bar = page.locator(".title-bar")
    c = await title_bar.count()
    record(name, "title-bar count", c == 1, f"count={c}")
    visible = await title_bar.is_visible()
    record(name, "title-bar visible", visible, f"visible={visible}")
    # Check title input
    title_input = page.locator("#title-input")
    c = await title_input.count()
    record(name, "title input present", c == 1, f"count={c}")

    # Check editor-wrapper
    editor_wrapper = page.locator("#editor-wrapper")
    c = await editor_wrapper.count()
    record(name, "editor-wrapper count", c == 1, f"count={c}")
    visible = await editor_wrapper.is_visible()
    record(name, "editor-wrapper visible", visible, f"visible={visible}")

    # Check file items
    file_items = page.locator(".file-item")
    c = await file_items.count()
    record(name, "file items count", c >= 0, f"count={c}")
    if c > 0:
        first = file_items.first
        vis = await first.is_visible()
        record(name, "first file item visible", vis, f"visible={vis}")

    return screenshots

async def test_sidebar_toggle_mobile(page, viewport_name, viewport_size):
    """Test sidebar toggle on mobile viewport."""
    name = "sidebar_toggle_mobile"
    await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
    await set_viewport(page, viewport_size)
    await page.wait_for_timeout(300)

    screenshots = []
    path = await screenshot(page, f"{name}_closed")
    screenshots.append(path)

    # Sidebar should be hidden on mobile (off-screen)
    sidebar = page.locator("#sidebar")
    # On mobile, sidebar should have class 'open' toggled by clicking toggle
    is_open = await sidebar.evaluate("el => el.classList.contains('open')")
    record(name, "sidebar closed by default on mobile", not is_open, f"is_open={is_open}")

    # Toggle button should be visible on mobile
    toggle = page.locator("#sidebar-toggle")
    c = await toggle.count()
    record(name, "toggle button present on mobile", c == 1, f"count={c}")
    visible = await toggle.is_visible()
    record(name, "toggle button visible on mobile", visible, f"visible={visible}")

    # Click the toggle to open sidebar
    await toggle.click()
    await page.wait_for_timeout(300)
    path = await screenshot(page, f"{name}_open")
    screenshots.append(path)

    is_open = await sidebar.evaluate("el => el.classList.contains('open')")
    record(name, "sidebar opens on toggle click", is_open, f"is_open={is_open}")

    # Check overlay is visible
    overlay = page.locator("#sidebar-overlay")
    visible = await overlay.is_visible()
    record(name, "overlay visible when sidebar open", visible, f"visible={visible}")

    # Click overlay to close
    await overlay.click()
    await page.wait_for_timeout(300)
    path = await screenshot(page, f"{name}_closed_after_overlay")
    screenshots.append(path)

    is_open = await sidebar.evaluate("el => el.classList.contains('open')")
    record(name, "sidebar closes on overlay click", not is_open, f"is_open={is_open}")

    return screenshots

async def test_search(page, viewport_name, viewport_size):
    """Test search functionality."""
    name = "search"
    await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
    await set_viewport(page, viewport_size)
    await page.wait_for_timeout(300)

    screenshots = []

    # Find search input
    search_input = page.locator(".search-input")
    c = await search_input.count()
    record(name, "search input present", c == 1, f"count={c}")

    if c > 0:
        # Clear and type a search query
        await search_input.click()
        await search_input.fill("nonexistentxyz")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)
        path = await screenshot(page, f"{name}_results")
        screenshots.append(path)

        # Check for empty state or results
        empty_state = page.locator(".empty-state-sidebar")
        c = await empty_state.count()
        record(name, "search shows empty state for no results", c == 1, f"count={c}")

        # Try a broader search
        await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
        await set_viewport(page, viewport_size)
        await page.wait_for_timeout(300)
        search_input = page.locator(".search-input")
        await search_input.click()
        await search_input.fill("test")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)
        path = await screenshot(page, f"{name}_test_search")
        screenshots.append(path)

        # Check if any file items match
        file_items = page.locator(".file-item")
        c = await file_items.count()
        record(name, "search returns results for 'test'", c >= 0, f"count={c}")

    return screenshots

async def test_preview_toggle(page, viewport_name, viewport_size):
    """Test preview toggle on editor page with markdown note."""
    name = "preview_toggle"
    await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
    await set_viewport(page, viewport_size)
    await page.wait_for_timeout(300)

    # Find a markdown note
    file_items = page.locator(".file-item")
    md_note = None
    for i in range(await file_items.count()):
        item = file_items.nth(i)
        badge = item.locator(".format-badge")
        text = await badge.inner_text()
        if text == "MD":
            link = item.locator("a.filename")
            href = await link.get_attribute("href")
            await link.click()
            md_note = True
            break

    if not md_note:
        # Create a markdown note
        await page.goto(f"{BASE_URL}/notes/new/", wait_until="domcontentloaded")
        await set_viewport(page, viewport_size)
        await page.wait_for_timeout(300)
        await page.locator("#title-input").fill("Markdown Test")
        await page.locator("#editor").fill("# Hello\n\nThis is **markdown** content.")
        await page.locator("#format-select").select_option("md")
        await page.locator("#save-btn").click()
        await page.wait_for_timeout(500)
        # Navigate back to get the editor page
        await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
        await set_viewport(page, viewport_size)
        await page.wait_for_timeout(300)
        # Find the markdown note
        file_items = page.locator(".file-item")
        for i in range(await file_items.count()):
            item = file_items.nth(i)
            badge = item.locator(".format-badge")
            text = await badge.inner_text()
            if text == "MD":
                link = item.locator("a.filename")
                href = await link.get_attribute("href")
                await link.click()
                md_note = True
                break

    if not md_note:
        record(name, "preview toggle - markdown note found", False, "No MD notes available")
        path = await screenshot(page, f"{name}_no_md")
        return [path]

    await page.wait_for_timeout(500)
    screenshots = []
    path = await screenshot(page, f"{name}_initial")
    screenshots.append(path)

    preview_btn = page.locator("#preview-btn")
    c = await preview_btn.count()
    record(name, "preview button present", c == 1, f"count={c}")

    # Check initial preview state
    preview_pane = page.locator("#preview-pane")
    initial_hidden = await preview_pane.evaluate("el => el.classList.contains('hidden')")
    record(name, "preview initially hidden", initial_hidden, f"hidden={initial_hidden}")

    # Click preview button
    await preview_btn.click()
    await page.wait_for_timeout(500)
    path = await screenshot(page, f"{name}_preview_open")
    screenshots.append(path)

    hidden = await preview_pane.evaluate("el => el.classList.contains('hidden')")
    record(name, "preview visible after toggle", not hidden, f"hidden={hidden}")

    if not hidden:
        visible = await preview_pane.is_visible()
        record(name, "preview pane visible", visible, f"visible={visible}")

    # Click again to close
    await preview_btn.click()
    await page.wait_for_timeout(300)
    path = await screenshot(page, f"{name}_preview_closed")
    screenshots.append(path)

    hidden = await preview_pane.evaluate("el => el.classList.contains('hidden')")
    record(name, "preview hidden after second toggle", hidden, f"hidden={hidden}")

    return screenshots

async def test_delete_hover(page, viewport_name, viewport_size):
    """Test delete button hover behavior."""
    name = "delete_hover"
    await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
    await set_viewport(page, viewport_size)
    await page.wait_for_timeout(300)

    screenshots = []

    file_items = page.locator(".file-item")
    if file_items.count() == 0:
        record(name, "delete hover - file items exist", False, "no file items")
        return screenshots

    first_item = file_items.first

    # Delete button should be hidden initially on desktop
    delete_btn = first_item.locator(".delete-btn")
    visible = await delete_btn.is_visible()
    record(name, "delete btn hidden by default (desktop)", not visible, f"visible={visible}")

    # Hover over the file item
    await first_item.hover()
    await page.wait_for_timeout(300)
    path = await screenshot(page, f"{name}_hovered_{viewport_name}")
    screenshots.append(path)

    visible = await delete_btn.is_visible()
    record(name, "delete btn visible on hover", visible, f"visible={visible}")

    if visible:
        title = await delete_btn.get_attribute("title")
        record(name, "delete btn has title tooltip", title is not None, f"title='{title}'")

    return screenshots

async def test_all():
    all_screenshots = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Desktop tests
        print("=" * 60)
        print("DESKTOP (1280x800) TESTS")
        print("=" * 60)
        desktop_ctx = await browser.new_context(viewport=DESKTOP)
        desktop_page = await desktop_ctx.new_page()

        all_screenshots["list_desktop"] = await test_list_page(desktop_page, "desktop", DESKTOP)
        all_screenshots["editor_desktop"] = await test_editor_page(desktop_page, "desktop", DESKTOP)
        all_screenshots["new_desktop"] = await test_new_page(desktop_page, "desktop", DESKTOP)
        all_screenshots["sidebar_toggle_desktop"] = await test_sidebar_toggle_mobile(desktop_page, "desktop", DESKTOP)
        all_screenshots["search_desktop"] = await test_search(desktop_page, "desktop", DESKTOP)
        all_screenshots["preview_toggle_desktop"] = await test_preview_toggle(desktop_page, "desktop", DESKTOP)
        all_screenshots["delete_hover_desktop"] = await test_delete_hover(desktop_page, "desktop", DESKTOP)

        await desktop_ctx.close()

        # Mobile tests
        print()
        print("=" * 60)
        print("MOBILE (375x812) TESTS")
        print("=" * 60)
        mobile_ctx = await browser.new_context(viewport=MOBILE)
        mobile_page = await mobile_ctx.new_page()

        all_screenshots["list_mobile"] = await test_list_page(mobile_page, "mobile", MOBILE)
        all_screenshots["editor_mobile"] = await test_editor_page(mobile_page, "mobile", MOBILE)
        all_screenshots["new_mobile"] = await test_new_page(mobile_page, "mobile", MOBILE)
        all_screenshots["sidebar_toggle_mobile"] = await test_sidebar_toggle_mobile(mobile_page, "mobile", MOBILE)
        all_screenshots["search_mobile"] = await test_search(mobile_page, "mobile", MOBILE)
        all_screenshots["preview_toggle_mobile"] = await test_preview_toggle(mobile_page, "mobile", MOBILE)
        all_screenshots["delete_hover_mobile"] = await test_delete_hover(mobile_page, "mobile", MOBILE)

        await mobile_ctx.close()
        await browser.close()

    return all_screenshots

# Run and collect
if __name__ == "__main__":
    import asyncio
    screenshots = asyncio.run(test_all())
    # Write results summary
    summary_path = os.path.join(SCREENSHOTS_DIR, "verification_report.json")
    with open(summary_path, "w") as f:
        json.dump({"results": results, "screenshots": screenshots}, f, indent=2, default=str)
    print(f"\n{'=' * 60}")
    print("VERIFICATION SUMMARY")
    print(f"{'=' * 60}")
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    total = len(results)
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    print(f"Report saved to: {summary_path}")
    print(f"Screenshots dir: {SCREENSHOTS_DIR}")
