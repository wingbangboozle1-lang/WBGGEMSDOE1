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
    for (const file of ["index.html", "executive-summary.html", "research.html", "evidence.html", "how-to-submit.html"]) {
      const response = await page.goto(new URL(file, base).href, { waitUntil: "networkidle" });
      assert.equal(response.status(), 200);
      const text = await page.locator("main").innerText();
      assert.match(text, /Download: YES, for research\. Submit: NO\./);
      assert.match(text, /No final dots were placed/);
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
    assert.equal(download.suggestedFilename(), path.basename(wbg2.artifacts.tif));
    const downloaded = fs.readFileSync(await download.path());
    assert.equal(crypto.createHash("sha256").update(downloaded).digest("hex"), wbg2.raster_sha256);
    await page.goto(new URL("index.html", base).href, { waitUntil: "networkidle" });
    await page.screenshot({ path: path.join(artifacts, "desktop.png"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    for (const file of ["index.html", "executive-summary.html", "research.html", "evidence.html", "how-to-submit.html"]) {
      await page.goto(new URL(file, base).href, { waitUntil: "networkidle" });
      const overflow = await page.evaluate(() => document.body.scrollWidth > window.innerWidth);
      assert.equal(overflow, false, `mobile body overflow: ${file}`);
      checked.find(row => row.file === file).mobile = "passed";
    }
    await page.goto(new URL("index.html", base).href, { waitUntil: "networkidle" });
    await page.screenshot({ path: path.join(artifacts, "mobile.png"), fullPage: true });
    for (const file of ["portfolio-review.html", "release-review.html", "wbg-h1-dpgf1/index.html", "wbg-h1-dpgf1/executive-summary.html", "wbg2.html"]) {
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
    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.goto(new URL("wbg2.html", base).href, { waitUntil: "networkidle" });
    assert.equal(await page.locator("table tbody tr").count(), 9);
    assert.match(await page.locator("main").innerText(), /99\.8972%/);
    assert.doesNotMatch(await page.locator("main").innerText(), /0\.2824/);
    await page.screenshot({ path: path.join(artifacts, "wbg2-desktop.png"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: path.join(artifacts, "wbg2-mobile.png"), fullPage: true });
    const portfolio = JSON.parse(fs.readFileSync(path.join(root, "docs/data/portfolio-review.json")));
    for (const row of portfolio.rows) {
      const response = await page.request.get(new URL(row.artifact.replace(/^docs\//, ""), base).href);
      assert.equal(response.status(), 200);
      assert.equal(crypto.createHash("sha256").update(await response.body()).digest("hex"), row.expected_sha256);
    }
    assert.deepEqual(errors, []);
    const report = { generated_utc: new Date().toISOString(), browser: browser.version(), checked,
      desktop_viewport: [1440, 1100], mobile_viewport: [390, 844],
      javascript_page_errors: errors, site_filter: "passed", wbg2_nine_site_table: "passed", primary_download_sha256: wbg2.raster_sha256,
      primary_download_identity: "passed", body_overflow: false, all_passed: true,
      no_model_training_or_slot_use: true };
    fs.writeFileSync(path.join(root, "evidence/browser_checks.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
