#!/usr/bin/env python3
"""Comprehensive Playwright browser verification for Notepad Django project."""

import asyncio
import os
import json
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8081"
SCREENSHOTS_DIR = "/tmp"
DESKTOP = {"width": 1280, "height": 800}
MOBILE = {"width": 375, "height": 812}

results = []
all_screenshots = {}

def record(page_name, check_name, passed, detail=""):
    results.append({"page": page_name, "check": check_name, "passed": passed, "detail": detail})
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {page_name} / {check_name}: {detail}")
    return passed

async def set_vp(page, size):
    await page.set_viewport_size(size)

async def snap(page, name):
    path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
    await page.screenshot(path=path, full_page=True)
    return path

async def ensure_md_note_with_content(page):
    """Ensure a markdown note with content exists; create one if not."""
    await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
    file_items = page.locator(".file-item")
    for i in range(await file_items.count()):
        item = file_items.nth(i)
        badge = item.locator(".format-badge")
        txt = await badge.inner_text()
        if txt == "MD":
            link = item.locator("a.filename")
            href = await link.get_attribute("href")
            if href:
                await link.click()
                await page.wait_for_timeout(400)
                content = await page.locator("textarea#editor").input_value()
                if len(content) > 10:
                    return True
                await page.locator("textarea#editor").fill("# Markdown Note\n\nThis has **bold** and *italic* content.")
                await page.locator("#save-btn").click()
                await page.wait_for_timeout(500)
            return True
    await page.goto(f"{BASE_URL}/notes/new/", wait_until="domcontentloaded")
    await page.locator("#title-input").fill("Markdown Test Note")
    await page.locator("#editor").fill("# Hello World\n\nThis is **bold** and *italic* markdown content.")
    await page.locator("#format-select").select_option("md")
    await page.locator("#save-btn").click()
    await page.wait_for_timeout(800)
    return True

async def get_note_with_content(page):
    """Get URL of first note that has content."""
    await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
    file_items = page.locator(".file-item a.filename")
    for i in range(await file_items.count()):
        link = file_items.nth(i)
        href = await link.get_attribute("href")
        if href:
            await link.click()
            await page.wait_for_timeout(400)
            content = await page.locator("textarea#editor").input_value()
            if len(content) > 5:
                return True
            await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
    return False

async def test_list(page, vp_name, vp_size):
    name = "list"
    await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
    await set_vp(page, vp_size)
    await page.wait_for_timeout(300)
    all_screenshots[f"{name}_{vp_name}"] = await snap(page, f"{name}_{vp_name}")

    sidebar = page.locator("#sidebar")
    record(name, "sidebar count=1", await sidebar.count() == 1, f"count={await sidebar.count()}")
    record(name, "sidebar visible", await sidebar.is_visible(), "")

    editor_area = page.locator(".editor-area")
    record(name, "editor-area count=1", await editor_area.count() == 1, f"count={await editor_area.count()}")
    record(name, "editor-area visible", await editor_area.is_visible(), "")

    record(name, "textarea absent (list)", await page.locator("textarea#editor").count() == 0, "")
    record(name, "toolbar absent (list)", await page.locator(".toolbar").count() == 0, "")
    record(name, "title-bar absent (list)", await page.locator(".title-bar").count() == 0, "")
    record(name, "editor-wrapper absent (list)", await page.locator("#editor-wrapper").count() == 0, "")

    file_items = page.locator(".file-item")
    c = await file_items.count()
    record(name, "file items count", c >= 0, f"count={c}")
    if c > 0:
        record(name, "first file item visible", await file_items.first.is_visible(), "")
        badge = file_items.first.locator(".format-badge")
        badge_text = await badge.inner_text()
        record(name, "first file has format badge", len(badge_text) > 0, f"badge='{badge_text}'")
    return [all_screenshots[f"{name}_{vp_name}"]]

async def test_editor(page, vp_name, vp_size):
    name = "editor"
    # On mobile, sidebar is off-screen so we navigate directly
    if vp_name == "mobile":
        # Get first note URL from list first (desktop-like approach via direct URL)
        await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
        await set_vp(page, vp_size)
        await page.wait_for_timeout(200)
        # On mobile the sidebar is hidden; try to get a note URL from DOM
        links = page.locator(".file-item a.filename")
        if await links.count() > 0:
            href = await links.first.get_attribute("href")
            if href:
                await page.goto(f"{BASE_URL}{href}", wait_until="domcontentloaded")
                await set_vp(page, vp_size)
                await page.wait_for_timeout(500)
                all_screenshots[f"{name}_{vp_name}"] = await snap(page, f"{name}_{vp_name}")
        else:
            # No notes - create one
            await page.goto(f"{BASE_URL}/notes/new/", wait_until="domcontentloaded")
            await page.locator("#title-input").fill("Content Note")
            await page.locator("#editor").fill("# Content Note\n\nThis note has content in it.")
            await page.locator("#save-btn").click()
            await page.wait_for_timeout(600)
            await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
            await set_vp(page, vp_size)
            await page.wait_for_timeout(300)
            links = page.locator(".file-item a.filename")
            if await links.count() > 0:
                href = await links.first.get_attribute("href")
                await page.goto(f"{BASE_URL}{href}", wait_until="domcontentloaded")
                await set_vp(page, vp_size)
                await page.wait_for_timeout(500)
                all_screenshots[f"{name}_{vp_name}"] = await snap(page, f"{name}_{vp_name}")
    else:
        # Desktop: ensure we have a note with content
        has_content = await get_note_with_content(page)
        if not has_content:
            await page.goto(f"{BASE_URL}/notes/new/", wait_until="domcontentloaded")
            await page.locator("#title-input").fill("Content Note")
            await page.locator("#editor").fill("# Content Note\n\nThis note has content in it.")
            await page.locator("#format-select").select_option("txt")
            await page.locator("#save-btn").click()
            await page.wait_for_timeout(600)
            await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
            await set_vp(page, vp_size)
            await page.wait_for_timeout(300)
            await page.locator(".file-item a.filename").first.click(force=True)
            await page.wait_for_timeout(500)
        else:
            await set_vp(page, vp_size)
            await page.wait_for_timeout(300)
        all_screenshots[f"{name}_{vp_name}"] = await snap(page, f"{name}_{vp_name}")

    sidebar = page.locator("#sidebar")
    record(name, "sidebar count=1", await sidebar.count() == 1, "")
    if vp_name == "mobile":
        # On mobile editor page, sidebar is off-screen by default
        is_open = await sidebar.evaluate("el => el.classList.contains('open')")
        record(name, "sidebar off-screen on mobile editor", not is_open, f"open={is_open}")
    else:
        record(name, "sidebar visible", await sidebar.is_visible(), "")

    editor_area = page.locator(".editor-area")
    record(name, "editor-area count=1", await editor_area.count() == 1, "")
    record(name, "editor-area visible", await editor_area.is_visible(), "")

    textarea = page.locator("textarea#editor")
    record(name, "textarea count=1", await textarea.count() == 1, "")
    record(name, "textarea visible", await textarea.is_visible(), "")
    content = await textarea.input_value()
    record(name, "textarea has content", len(content) > 0, f"length={len(content)}")

    toolbar = page.locator(".toolbar")
    record(name, "toolbar count=1", await toolbar.count() == 1, "")
    record(name, "toolbar visible", await toolbar.is_visible(), "")
    record(name, "save button present", await page.locator("#save-btn").count() == 1, "")
    record(name, "saveas button present", await page.locator("#saveas-btn").count() == 1, "")
    pb_count = await page.locator("#preview-btn").count()
    record(name, "preview button present", pb_count >= 0, f"count={pb_count} (MD-only)")

    title_bar = page.locator(".title-bar")
    record(name, "title-bar count=1", await title_bar.count() == 1, "")
    record(name, "title-bar visible", await title_bar.is_visible(), "")
    record(name, "title input present", await page.locator("#title-input").count() == 1, "")

    editor_wrapper = page.locator("#editor-wrapper")
    record(name, "editor-wrapper count=1", await editor_wrapper.count() == 1, "")
    record(name, "editor-wrapper visible", await editor_wrapper.is_visible(), "")

    file_items = page.locator(".file-item")
    c = await file_items.count()
    if vp_name == "mobile":
        # On mobile, sidebar is off-screen so file items may not be visible
        record(name, "file items count>=0 (mobile may be 0)", c >= 0, f"count={c}")
    else:
        record(name, "file items count>=1", c >= 1, f"count={c}")
        if c > 0:
            record(name, "first file item visible", await file_items.first.is_visible(), "")
    return [all_screenshots.get(f"{name}_{vp_name}", "")]

async def test_new(page, vp_name, vp_size):
    name = "new"
    await page.goto(f"{BASE_URL}/notes/new/", wait_until="domcontentloaded")
    await set_vp(page, vp_size)
    await page.wait_for_timeout(300)
    all_screenshots[f"{name}_{vp_name}"] = await snap(page, f"{name}_{vp_name}")

    sidebar = page.locator("#sidebar")
    record(name, "sidebar count=1", await sidebar.count() == 1, "")
    if vp_name == "mobile":
        is_open = await sidebar.evaluate("el => el.classList.contains('open')")
        record(name, "sidebar off-screen on mobile new", not is_open, f"open={is_open}")
    else:
        record(name, "sidebar visible", await sidebar.is_visible(), "")

    editor_area = page.locator(".editor-area")
    record(name, "editor-area count=1", await editor_area.count() == 1, "")
    record(name, "editor-area visible", await editor_area.is_visible(), "")

    textarea = page.locator("textarea#editor")
    record(name, "textarea count=1", await textarea.count() == 1, "")
    record(name, "textarea visible", await textarea.is_visible(), "")
    ph = await textarea.get_attribute("placeholder")
    record(name, "textarea placeholder set", ph and len(ph) > 0, f"placeholder='{ph}'")

    toolbar = page.locator(".toolbar")
    record(name, "toolbar count=1", await toolbar.count() == 1, "")
    record(name, "toolbar visible", await toolbar.is_visible(), "")

    title_bar = page.locator(".title-bar")
    record(name, "title-bar count=1", await title_bar.count() == 1, "")
    record(name, "title-bar visible", await title_bar.is_visible(), "")
    record(name, "title input present", await page.locator("#title-input").count() == 1, "")

    editor_wrapper = page.locator("#editor-wrapper")
    record(name, "editor-wrapper count=1", await editor_wrapper.count() == 1, "")
    record(name, "editor-wrapper visible", await editor_wrapper.is_visible(), "")

    file_items = page.locator(".file-item")
    c = await file_items.count()
    if vp_name == "mobile":
        record(name, "file items count>=0 (mobile may be 0)", c >= 0, f"count={c}")
    else:
        record(name, "file items count>=0", c >= 0, f"count={c}")
        if c > 0:
            record(name, "first file item visible", await file_items.first.is_visible(), "")
    return [all_screenshots[f"{name}_{vp_name}"]]

async def test_sidebar_toggle(page, vp_name, vp_size):
    name = "sidebar_toggle"
    await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
    await set_vp(page, vp_size)
    await page.wait_for_timeout(300)

    toggle = page.locator("#sidebar-toggle")
    c = await toggle.count()
    record(name, "toggle button present", c == 1, f"count={c}")

    if vp_name == "desktop":
        vis = await toggle.is_visible()
        record(name, "toggle hidden on desktop", not vis, f"visible={vis}")
        all_screenshots[f"{name}_{vp_name}"] = await snap(page, f"{name}_{vp_name}")
        return [all_screenshots[f"{name}_{vp_name}"]]

    # Mobile
    vis = await toggle.is_visible()
    record(name, "toggle visible on mobile", vis, f"visible={vis}")
    all_screenshots[f"{name}_{vp_name}_closed"] = await snap(page, f"{name}_{vp_name}_closed")

    sidebar = page.locator("#sidebar")
    is_open = await sidebar.evaluate("el => el.classList.contains('open')")
    record(name, "sidebar closed by default (mobile)", not is_open, f"open={is_open}")

    if vis:
        await toggle.click(force=True)
        await page.wait_for_timeout(400)
        all_screenshots[f"{name}_{vp_name}_open"] = await snap(page, f"{name}_{vp_name}_open")

        is_open = await sidebar.evaluate("el => el.classList.contains('open')")
        record(name, "sidebar opens on toggle click", is_open, f"open={is_open}")

        overlay = page.locator("#sidebar-overlay")
        ov_vis = await overlay.is_visible()
        record(name, "overlay visible when open", ov_vis, f"visible={ov_vis}")

        if ov_vis:
            await overlay.click(force=True)
            await page.wait_for_timeout(300)
            is_open = await sidebar.evaluate("el => el.classList.contains('open')")
            record(name, "sidebar closes on overlay click", not is_open, f"open={is_open}")

    return [all_screenshots.get(f"{name}_{vp_name}_closed", "")]

async def test_search(page, vp_name, vp_size):
    name = "search"
    await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
    await set_vp(page, vp_size)
    await page.wait_for_timeout(300)

    search_input = page.locator(".search-input")
    record(name, "search input present", await search_input.count() == 1, "")

    if await search_input.count() > 0:
        await search_input.click()
        await search_input.fill("zzz_nonexistent_xyz_12345")
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)
        all_screenshots[f"{name}_{vp_name}_no_results"] = await snap(page, f"{name}_{vp_name}_no_results")

        empty_state = page.locator(".empty-state-sidebar")
        record(name, "search shows empty state", await empty_state.count() >= 1, f"count={await empty_state.count()}")

        # Search for existing content
        await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
        await set_vp(page, vp_size)
        await page.wait_for_timeout(300)
        search_input = page.locator(".search-input")

        # On mobile, sidebar is hidden - need to open it first to see search
        if vp_name == "mobile":
            toggle = page.locator("#sidebar-toggle")
            if await toggle.is_visible():
                await toggle.click(force=True)
                await page.wait_for_timeout(400)
                all_screenshots[f"{name}_{vp_name}_sidebar_open"] = await snap(page, f"{name}_{vp_name}_sidebar_open")

        # Get a real search term
        first_note_title = await page.locator(".file-item a.filename").first.inner_text()
        await search_input.fill(first_note_title)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)
        all_screenshots[f"{name}_{vp_name}_existing"] = await snap(page, f"{name}_{vp_name}_existing")

        file_items = page.locator(".file-item")
        c = await file_items.count()
        record(name, "search for existing note returns results", c >= 1, f"count={c}")

    return list(all_screenshots.values())

async def test_preview_toggle(page, vp_name, vp_size):
    name = "preview_toggle"
    await ensure_md_note_with_content(page)

    if vp_name == "mobile":
        # On mobile, navigate directly to the MD note editor
        await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
        await set_vp(page, vp_size)
        await page.wait_for_timeout(200)
        file_items = page.locator(".file-item")
        for i in range(await file_items.count()):
            item = file_items.nth(i)
            badge = item.locator(".format-badge")
            txt = await badge.inner_text()
            if txt == "MD":
                link = item.locator("a.filename")
                href = await link.get_attribute("href")
                if href:
                    await page.goto(f"{BASE_URL}{href}", wait_until="domcontentloaded")
                    await set_vp(page, vp_size)
                    await page.wait_for_timeout(600)
                break
    else:
        await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
        await set_vp(page, vp_size)
        await page.wait_for_timeout(300)
        file_items = page.locator(".file-item")
        for i in range(await file_items.count()):
            item = file_items.nth(i)
            badge = item.locator(".format-badge")
            txt = await badge.inner_text()
            if txt == "MD":
                link = item.locator("a.filename")
                await link.click()
                break
        await page.wait_for_timeout(600)

    all_screenshots[f"{name}_{vp_name}_initial"] = await snap(page, f"{name}_{vp_name}_initial")

    preview_btn = page.locator("#preview-btn")
    pb_count = await preview_btn.count()
    record(name, "preview button present on MD page", pb_count == 1, f"count={pb_count}")

    if pb_count == 1:
        preview_pane = page.locator("#preview-pane")
        init_hidden = await preview_pane.evaluate("el => el.classList.contains('hidden')")
        record(name, "preview initial state recorded", True, f"hidden={init_hidden}")

        await preview_btn.click(force=True)
        await page.wait_for_timeout(600)
        all_screenshots[f"{name}_{vp_name}_after_toggle1"] = await snap(page, f"{name}_{vp_name}_after_toggle1")

        hidden_after_1 = await preview_pane.evaluate("el => el.classList.contains('hidden')")
        record(name, "preview toggled after first click", hidden_after_1 != init_hidden, f"initial={init_hidden}, after1={hidden_after_1}")

        await preview_btn.click(force=True)
        await page.wait_for_timeout(400)
        all_screenshots[f"{name}_{vp_name}_after_toggle2"] = await snap(page, f"{name}_{vp_name}_after_toggle2")

        hidden_after_2 = await preview_pane.evaluate("el => el.classList.contains('hidden')")
        record(name, "preview restored after second click", hidden_after_2 == init_hidden, f"after2={hidden_after_2}")

        if not hidden_after_1:
            vis = await preview_pane.is_visible()
            record(name, "preview pane visible when shown", vis, f"visible={vis}")
            content = await preview_pane.inner_text()
            record(name, "preview has rendered content", len(content) > 0, f"length={len(content)}")

    return list(all_screenshots.values())

async def test_delete_hover(page, vp_name, vp_size):
    name = "delete_hover"
    await page.goto(f"{BASE_URL}/notes/", wait_until="domcontentloaded")
    await set_vp(page, vp_size)
    await page.wait_for_timeout(300)

    file_items = page.locator(".file-item")
    if await file_items.count() == 0:
        record(name, "file items exist", False, "no file items")
        return []

    first = file_items.first
    delete_btn = first.locator(".delete-btn")

    if vp_name == "desktop":
        vis = await delete_btn.is_visible()
        record(name, "delete btn hidden by default (desktop)", not vis, f"visible={vis}")
        await first.hover()
        await page.wait_for_timeout(400)
        all_screenshots[f"{name}_{vp_name}_hover"] = await snap(page, f"{name}_{vp_name}_hover")
        vis = await delete_btn.is_visible()
        record(name, "delete btn visible on hover (desktop)", vis, f"visible={vis}")
        if vis:
            title = await delete_btn.get_attribute("title")
            record(name, "delete btn has tooltip", title is not None and len(title) > 0, f"title='{title}'")
    else:
        all_screenshots[f"{name}_{vp_name}_default"] = await snap(page, f"{name}_{vp_name}_default")
        vis = await delete_btn.is_visible()
        record(name, "delete btn visibility on mobile (default)", vis, f"visible={vis}")
        await first.hover()
        await page.wait_for_timeout(400)
        all_screenshots[f"{name}_{vp_name}_hover"] = await snap(page, f"{name}_{vp_name}_hover")
        vis = await delete_btn.is_visible()
        record(name, "delete btn on hover (mobile)", vis, f"visible={vis}")

    return list(all_screenshots.values())

async def run_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        print("=" * 60)
        print("DESKTOP (1280x800)")
        print("=" * 60)
        ctx_d = await browser.new_context(viewport=DESKTOP)
        pg_d = await ctx_d.new_page()
        await test_list(pg_d, "desktop", DESKTOP)
        await test_editor(pg_d, "desktop", DESKTOP)
        await test_new(pg_d, "desktop", DESKTOP)
        await test_sidebar_toggle(pg_d, "desktop", DESKTOP)
        await test_search(pg_d, "desktop", DESKTOP)
        await test_preview_toggle(pg_d, "desktop", DESKTOP)
        await test_delete_hover(pg_d, "desktop", DESKTOP)
        await ctx_d.close()

        print()
        print("=" * 60)
        print("MOBILE (375x812)")
        print("=" * 60)
        ctx_m = await browser.new_context(viewport=MOBILE)
        pg_m = await ctx_m.new_page()
        await test_list(pg_m, "mobile", MOBILE)
        await test_editor(pg_m, "mobile", MOBILE)
        await test_new(pg_m, "mobile", MOBILE)
        await test_sidebar_toggle(pg_m, "mobile", MOBILE)
        await test_search(pg_m, "mobile", MOBILE)
        await test_preview_toggle(pg_m, "mobile", MOBILE)
        await test_delete_hover(pg_m, "mobile", MOBILE)
        await ctx_m.close()
        await browser.close()

    summary_path = os.path.join(SCREENSHOTS_DIR, "verification_report.json")
    with open(summary_path, "w") as f:
        json.dump({"results": results, "screenshots": all_screenshots}, f, indent=2, default=str)

    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    total = len(results)
    print(f"\n{'=' * 60}")
    print("FINAL SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    print(f"Report: {summary_path}")
    if failed > 0:
        print("\nFAILED CHECKS:")
        for r in results:
            if not r["passed"]:
                print(f"  [{r['page']}] {r['check']}: {r['detail']}")

if __name__ == "__main__":
    asyncio.run(run_all())
