"""Run with Playwright installed. This check is separate from backend pytest."""

import argparse
from pathlib import Path
import subprocess
import re
import sys
from tempfile import TemporaryDirectory

from playwright.sync_api import expect, sync_playwright


def check_print_studio(playwright, browser_name: str, report: Path, shots: Path | None, before: Path | None) -> None:
    browser = getattr(playwright, browser_name).launch()
    page = browser.new_page(offline=True, viewport={"width": 1280, "height": 960})
    errors = []
    external = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: external.append(request.url)
            if request.url.startswith(("https://", "http://")) else None)

    def screenshot(name: str, locator=None) -> None:
        if shots:
            shots.mkdir(parents=True, exist_ok=True)
            (locator or page).screenshot(path=shots / f"{name}.png")

    if before:
        page.goto(before.resolve().as_uri())
        expect(page.get_by_role("heading", name="Too much at once?")).to_be_visible()
        screenshot("before")
    page.goto(report.resolve().as_uri())
    expect(page.get_by_role("heading", name="p-limit Too much at once?")).to_be_visible()
    screenshot("after")
    page.get_by_role("button", name="Replay ticket arrival").click()
    comparison = page.locator("#studio-problem")
    comparison.get_by_role("button", name="Limit to two at once").click()
    expect(comparison.locator("figcaption")).to_contain_text("2 running · 4 waiting")
    screenshot("comparison", comparison)
    decision = page.locator("#studio-rule")
    decision.get_by_role("button", name="2 active · limit 2", exact=True).click()
    expect(decision.locator(".queue-feedback")).to_contain_text("Ticket 01 waits")
    screenshot("algorithm", decision)
    decision.get_by_role("button", name="Let a task settle").click()
    expect(decision.locator(".queue-feedback")).to_contain_text("freed a slot")
    page.get_by_role("link", name="Behind the Scenes", exact=True).click()
    expect(page).to_have_url(f"{report.resolve().as_uri()}#studio-source")
    page.get_by_role("link", name="Architecture / Import Map").click()
    expect(page.get_by_text("Static import tour.", exact=False)).to_be_visible()
    explorer = page.locator(".import-explorer")
    expect(explorer.get_by_role("button", name="Inspect file index.js", exact=True)).to_be_visible()
    explorer.get_by_role("button", name="Inspect file index.js", exact=True).click()
    expect(page.locator(".inspector-path")).to_have_text("index.js")
    edge = explorer.locator(".explorer-hit").first
    edge.focus()
    edge.press("Enter")
    expect(page.locator(".current-connection")).to_contain_text("Static import")
    expect(page.locator(".current-connection").get_by_role("link", name="View on GitHub")).to_be_visible()
    explorer.get_by_role("button", name="Zoom in").click()
    explorer.get_by_role("button", name="Focus file").click()
    explorer.get_by_role("button", name="Fit", exact=True).click()
    explorer.get_by_role("searchbox", name="Find a file").fill("no-match.zzz")
    expect(explorer.get_by_text("No files match these filters.")).to_be_visible()
    explorer.get_by_role("button", name="Reset view").click()
    screenshot("import-explorer", page.locator("#map"))
    page.go_back()
    expect(page).to_have_url(f"{report.resolve().as_uri()}#studio-source")
    page.get_by_role("link", name="Try It", exact=True).click()
    playground = page.locator("#studio-play")
    page.set_viewport_size({"width": 1366, "height": 768})
    page.get_by_role("link", name="Try It", exact=True).click()
    expect(page.get_by_role("heading", name="How it works", exact=True)).to_be_attached()
    for selector in (".production-line", ".workshop-counts", ".play-buttons", ".studio-speed", ".studio-caption-toggle"):
        expect(playground.locator(selector)).to_be_in_viewport(ratio=1)
    scene = playground.locator("svg")
    counts = playground.locator(".workshop-counts")
    ticket = scene.locator('[data-ticket="1"]')

    def check_counts() -> None:
        for state, label in (("waiting", "Waiting"), ("running", "Running"), ("done", "Completed")):
            count = scene.locator(f'[data-state="{state}"]').count()
            expect(counts).to_contain_text(f"{count} {label}")
        assert scene.locator("[data-ticket]").count() == 8
        assert scene.evaluate("""svg => [...svg.querySelectorAll('[data-ticket]')].every(ticket => {
            const b = ticket.getBoundingClientRect(), s = svg.getBoundingClientRect();
            return b.left >= s.left && b.top >= s.top && b.right <= s.right && b.bottom <= s.bottom;
        })""")

    speed = playground.get_by_label("Playback speed")
    guide = playground.get_by_role("checkbox", name="Guided captions")
    expect(speed).to_have_value("0.5")
    screenshot("initial", scene)
    check_counts()
    expect(scene.locator('[data-station="closed"]')).to_have_count(2)
    playground.get_by_role("button", name="Replay").click()
    page.get_by_role("link", name="Visual Story", exact=True).click()
    expect(playground).to_have_attribute("data-in-view", "false")
    offscreen_ticket = ticket.get_attribute("transform")
    page.wait_for_timeout(200)
    assert ticket.get_attribute("transform") == offscreen_ticket
    page.get_by_role("link", name="Try It", exact=True).click()
    expect(playground).to_have_attribute("data-in-view", "true")
    playground.get_by_role("button", name="Reset").click()
    initial_width = ticket.bounding_box()["width"]
    playground.get_by_role("button", name="Replay").click()
    screenshot("mid-animation", scene)
    playground.get_by_role("button", name="Pause").click()
    frozen = ticket.get_attribute("transform")
    page.wait_for_timeout(150)
    assert ticket.get_attribute("transform") == frozen
    assert abs(ticket.bounding_box()["width"] - initial_width) < 1
    screenshot("paused", scene)
    guide.uncheck()
    expect(playground.locator(".studio-bubble")).to_have_count(0)
    guide.check()
    expect(playground.locator(".studio-bubble")).to_contain_text("batch arrives")
    speed.select_option("2")
    playground.get_by_role("button", name="Play", exact=True).click()
    expect(counts).to_contain_text("1 Completed")
    screenshot("job-finishing", scene)
    expect(playground.locator(".studio-bubble")).to_contain_text("next waiting task")
    playground.get_by_role("button", name="Pause").click()
    playground.get_by_role("button", name="Reset").click()
    playground.get_by_role("button", name="Step", exact=True).click()
    expect(counts).to_contain_text("1 Completed")
    screenshot("job-finishing", scene)
    check_counts()
    page.wait_for_timeout(560)
    screenshot("next-job-started", scene)
    slider = playground.get_by_role("slider", name="Jobs allowed at once")
    slider.press("End")
    expect(counts).to_contain_text("4 Running")
    slider.press("Home")
    expect(counts).to_contain_text("4 Running")
    screenshot("changed-concurrency", scene)
    button = playground.get_by_role("button", name="Step", exact=True)
    for completed in range(2, 9):
        expect(button).to_be_enabled()
        button.click()
        expect(counts).to_contain_text(f"{completed} Completed")
    expect(counts).to_contain_text("8 Completed")
    check_counts()
    page.wait_for_timeout(560)
    screenshot("completed", scene)
    expect(playground.locator(".studio-complete")).to_contain_text("All 8 tasks settled")
    expect(playground.locator(".studio-complete")).to_contain_text("Peak active this run: 4")
    for _ in range(3):
        playground.get_by_role("button", name="Reset").click()
    expect(counts).to_contain_text("2 Running")
    screenshot("reset", scene)
    check_counts()

    page.emulate_media(reduced_motion="reduce")
    page.set_viewport_size({"width": 390, "height": 844})
    expect(page.get_by_role("link", name="Behind the Scenes", exact=True)).to_be_visible()
    screenshot("mobile-playground", playground)
    playground.get_by_role("button", name="Replay").click()
    expect(counts).to_contain_text("1 Completed", timeout=4000)
    check_counts()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    usage = page.locator("#studio-usage")
    usage.get_by_role("button", name="Show JavaScript example").click()
    usage.get_by_role("button", name="2. Hand over three jobs").click()
    expect(usage.locator(".story-ticket-stop").nth(1)).to_contain_text("Pending")
    expect(usage.locator("#studio-code [data-highlight=true]").first).to_contain_text("const input")
    screenshot("usage", usage)
    capability = page.locator("#studio-capabilities")
    capability.get_by_role("button", name="Clear waiting jobs").click()
    capability.get_by_role("button", name="See an example").click()
    expect(capability.locator(".story-ticket-stop").last).to_contain_text("Discarded")
    screenshot("capabilities", capability)
    applications = page.locator("#studio-applications")
    applications.get_by_role("button", name="Process a folder of files").click()
    applications.get_by_role("button", name="Show the workflow").click()
    expect(applications.locator(".recipe-flow")).to_contain_text("uploads folder")
    screenshot("applications", applications)
    setup = page.locator("#studio-setup")
    setup.get_by_role("button", name="Install", exact=True).click()
    expect(setup.locator(".setup-stage code")).to_have_text("npm install p-limit")
    screenshot("setup", setup)
    assert not errors, errors
    assert not external, external
    browser.close()


def check_story(playwright, browser_name, report):
    browser = getattr(playwright, browser_name).launch()
    page = browser.new_page(offline=True, reduced_motion="reduce", viewport={"width": 390, "height": 844})
    errors, requests = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: requests.append(request.url) if request.url.startswith(("http:", "https:")) else None)
    page.goto(report.resolve().as_uri())
    expect(page.get_by_role("heading", name="record-filter", exact=True)).to_be_visible()
    scene = page.locator('[data-kind="walkthrough"]')
    expect(scene.get_by_role("heading", name="Check records")).to_be_visible()
    next_button = scene.get_by_role("button", name="Next")
    next_button.focus()
    page.keyboard.press("ArrowRight")
    expect(scene.get_by_role("heading", name="Keep named records")).to_be_visible()
    scene.get_by_role("button", name="Replay").click()
    expect(scene.get_by_role("heading", name="Check records")).to_be_visible()
    expect(scene.get_by_role("button", name="Play", exact=True)).to_have_count(0)
    scene.locator("summary").click()
    expect(scene.get_by_role("link", name="README.md", exact=False)).to_have_attribute(
        "href", re.compile(r"https://github\.com/example/record-filter/blob/[a-f0-9]{40}/README"))
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert not errors, errors
    assert not requests, requests
    browser.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("chromium", "firefox", "webkit"), default="chromium")
    parser.add_argument("--studio-report", type=Path)
    parser.add_argument("--screenshots", type=Path)
    parser.add_argument("--before", type=Path)
    parser.add_argument("--story-report", type=Path, help="Offline synthetic explanation report")
    args = parser.parse_args()
    if args.story_report:
        with sync_playwright() as playwright:
            check_story(playwright, args.browser, args.story_report)
        return
    if args.studio_report:
        with sync_playwright() as playwright:
            check_print_studio(playwright, args.browser, args.studio_report, args.screenshots, args.before)
        return
    with TemporaryDirectory() as directory, sync_playwright() as playwright:
        root = Path(directory)
        project = root / "example"
        project.mkdir()
        (project / "__main__.py").write_text("import helper\n", encoding="utf-8")
        (project / "helper.py").write_text("def run():\n    return 1\n", encoding="utf-8")
        (project / "README.md").write_text(
            "# Example\n\nExample is a Python package for building websites.\n"
            "\n## Install\n\n```sh\npip install example\n```\n",
            encoding="utf-8",
        )
        output = root / "report.html"
        subprocess.run([sys.executable, "-m", "repolens", "build", str(project), "--no-ai",
                        "--out", str(output)], check=True)

        browser = getattr(playwright, args.browser).launch()
        page = browser.new_page(offline=True, reduced_motion="reduce")
        errors = []
        external = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: external.append(request.url)
                if request.url.startswith(("https://", "http://")) else None)
        page.goto(output.as_uri())
        expect(page.get_by_role("heading", name="example", exact=True)).to_be_visible()
        expect(page.locator(".lead")).to_have_text("Example is a Python package for building websites.")
        install = page.locator("#setup .citation > pre > code").filter(has_text=re.compile(r"^pip install example$"))
        expect(install).to_be_visible()
        expect(page.get_by_text("Static import tour.", exact=False)).to_be_visible()
        page.get_by_role("button", name="Play path").click()
        expect(page.get_by_role("button", name="Replay")).to_be_visible()
        page.get_by_role("button", name="Inspect import from __main__.py to helper.py").click()
        evidence = page.get_by_role("complementary", name="Source evidence")
        expect(evidence.get_by_text("import helper", exact=True)).to_be_visible()
        page.get_by_role("button", name="Connected files").click()
        expect(page.get_by_role("button", name="Connected files")).to_have_attribute("aria-pressed", "true")
        assert not errors, errors
        assert not external, external
        browser.close()


if __name__ == "__main__":
    main()
