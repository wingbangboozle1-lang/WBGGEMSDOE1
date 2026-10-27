/* Optional rendered-site regression check. npm ci; BASE_URL=<running preview> npm run test:browser
 * Browser drivers run inside the test machine; the application itself uses only relative URLs.
 */
const path = require("node:path");
const fs = require("node:fs");
const crypto = require("node:crypto");
const assert = require("node:assert/strict");
const { createRequire } = require("node:module");
const root = path.resolve(__dirname, "..");
const localRequire = process.env.BROWSER_MODULES
  ? createRequire(path.join(path.resolve(process.env.BROWSER_MODULES), "package.json"))
  : require;
const { chromium: playwright } = localRequire("playwright-core");
const importedChromium = localRequire("@sparticuz/chromium");
const chromium = importedChromium.default || importedChromium;

(async () => {
  const base = process.env.BASE_URL;
  if (!base) throw new Error("BASE_URL must identify the running static site preview");
  const artifacts = path.join(root, ".cache/browser-review");
  fs.mkdirSync(artifacts, { recursive: true });
  const card = JSON.parse(fs.readFileSync(path.join(root, "registry/run_card.json")));
  const wbg2 = JSON.parse(fs.readFileSync(path.join(root, "evidence/wbg2/run_card.json")));
  if (process.env.BROWSER_COMPAT_LIBS === "1") {
    // Minimal Linux containers may lack NSS/NSPR. Use the dependency's own
    // bundled compatibility libraries instead of downloading system packages.
    const bin = path.join(path.dirname(localRequire.resolve("@sparticuz/chromium")), "../bin");
    await importedChromium.inflate(path.join(bin, "al2023.tar.br"));
    importedChromium.setupLambdaEnvironment(path.join(require("node:os").tmpdir(), "al2023/lib"));
  }
  const browser = await playwright.launch({
    args: chromium.args,
    executablePath: await chromium.executablePath(),
    headless: true,
  });
  const errors = [];
  const checked = [];
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1100 }, acceptDownloads: true });
    const page = await context.newPage();
    page.on("pageerror", error => errors.push(String(error)));
    const corePages = ["index.html", "wbg2.html", "executive-summary.html", "research.html", "evidence.html", "how-to-submit.html"];
    for (const file of corePages) {
      const response = await page.goto(new URL(file, base).href, { waitUntil: "networkidle" });
      assert.equal(response.status(), 200);
      const text = await page.locator("main").innerText();
      assert.ok(text.includes("SUBMIT: NO"));
      if (file === "wbg2.html") {
        assert.ok(text.includes("DOWNLOAD: YES (RESEARCH ONLY)"));
        assert.ok(text.includes("HOLDOUT-DTI") && text.includes("NOT MEASURED"));
        assert.ok(text.toLowerCase().includes("literal final-dot overlap"));
        assert.ok(!text.toLowerCase().includes("download the submission tiff"));
      } else {
        assert.ok(text.includes("Download: YES, for research. Submit: NO."));
        assert.ok(text.includes("No final dots were placed"));
      }
      const overflow = await page.evaluate(() => document.body.scrollWidth > window.innerWidth);
      assert.equal(overflow, false, `desktop body overflow: ${file}`);
      checked.push({ file, desktop: "passed" });
    }
    await page.goto(new URL("executive-summary.html", base).href, { waitUntil: "networkidle" });
    assert.equal(await page.locator("#site-table tbody tr:visible").count(), 9);
    await page.locator("#site-filter").fill("GEMSDOE32");
    assert.equal(await page.locator("#site-table tbody tr:visible").count(), 1);
    await page.locator("#site-filter").fill("");
    const downloadPromise = page.waitForEvent("download");
    await page.locator("a[download]").first().click();
    const download = await downloadPromise;
    assert.equal(download.suggestedFilename(), path.basename(card.artifact));
    const downloaded = fs.readFileSync(await download.path());
    assert.equal(crypto.createHash("sha256").update(downloaded).digest("hex"), card.raster_sha256);
    await page.goto(new URL("wbg2.html", base).href, { waitUntil: "networkidle" });
    const wbg2DownloadPromise = page.waitForEvent("download");
    await page.getByRole("link", { name: /Download research TIFF/ }).first().click();
    const wbg2Download = await wbg2DownloadPromise;
    assert.equal(wbg2Download.suggestedFilename(), path.basename(wbg2.artifacts.tif));
    const wbg2Bytes = fs.readFileSync(await wbg2Download.path());
    assert.equal(crypto.createHash("sha256").update(wbg2Bytes).digest("hex"), wbg2.raster_sha256);
    await page.goto(new URL("index.html", base).href, { waitUntil: "networkidle" });
    await page.screenshot({ path: path.join(artifacts, "desktop.png"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    for (const file of corePages) {
      await page.goto(new URL(file, base).href, { waitUntil: "networkidle" });
      if (file === "wbg2.html") {
        const text = await page.locator("main").innerText();
        assert.ok(text.includes("DOWNLOAD: YES (RESEARCH ONLY)") && text.includes("SUBMIT: NO"));
      }
      const overflow = await page.evaluate(() => document.body.scrollWidth > window.innerWidth);
      assert.equal(overflow, false, `mobile body overflow: ${file}`);
      checked.find(row => row.file === file).mobile = "passed";
    }
    await page.goto(new URL("index.html", base).href, { waitUntil: "networkidle" });
    await page.screenshot({ path: path.join(artifacts, "mobile.png"), fullPage: true });
    for (const file of ["portfolio-review.html", "release-review.html", "wbg-h1-dpgf1/index.html", "wbg-h1-dpgf1/executive-summary.html"]) {
      const result = { file };
      for (const [label, width, height] of [["desktop", 1440, 1100], ["mobile", 390, 844]]) {
        await page.setViewportSize({ width, height });
        const response = await page.goto(new URL(file, base).href, { waitUntil: "networkidle" });
        assert.equal(response.status(), 200);
        assert.match(await page.locator("main").innerText(), /SUBMIT: NO/);
        assert.equal(await page.evaluate(() => document.body.scrollWidth > window.innerWidth), false, `${label} overflow: ${file}`);
        result[label] = "passed";
      }
      checked.push(result);
    }
    const portfolio = JSON.parse(fs.readFileSync(path.join(root, "docs/data/portfolio-review.json")));
    for (const row of portfolio.rows) {
      const response = await page.request.get(new URL(row.artifact.replace(/^docs\//, ""), base).href);
      assert.equal(response.status(), 200);
      assert.equal(crypto.createHash("sha256").update(await response.body()).digest("hex"), row.expected_sha256);
    }
    assert.deepEqual(errors, []);
    const report = { generated_utc: new Date().toISOString(), browser: browser.version(), checked,
      desktop_viewport: [1440, 1100], mobile_viewport: [390, 844],
      javascript_page_errors: errors, site_filter: "passed", primary_download_sha256: card.raster_sha256,
      primary_download_identity: "passed", wbg2_research_download_sha256: wbg2.raster_sha256,
      wbg2_research_download_identity: "passed; clearly marked SUBMIT: NO", body_overflow: false, all_passed: true,
      no_model_training_or_slot_use: true };
    fs.writeFileSync(path.join(root, "evidence/browser_checks.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
