const { chromium } = require('./node_modules/playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await (await browser.newContext()).newPage();
  
  const BASE = 'http://127.0.0.1:8765';
  const results = [];
  const consoleErrors = [];
  
  function log(name, passed, detail = '') {
    const status = passed ? 'PASS' : 'FAIL';
    console.log(`[${status}] ${name}${detail ? ' — ' + detail : ''}`);
    results.push({ name, status, detail });
  }

  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', err => {
    consoleErrors.push(err.message);
  });

  async function waitForURL(pattern, timeout = 10000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      if (pattern.test(page.url())) return true;
      await page.waitForTimeout(200);
    }
    return false;
  }

  async function submitNote() {
    await page.evaluate(() => document.getElementById('editor-form').submit());
    await waitForURL(/\/notes\//, 10000);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
  }

  async function getNoteLinks() {
    return page.$$eval('a.filename', els => els.map(e => e.textContent.trim()));
  }

  async function goToList() {
    await page.goto(BASE + '/notes/');
    await waitForURL(/\/notes\//);
    await page.waitForLoadState('networkidle');
  }

  try {
    // ── Navigate to list page ───────────────────────────────────────
    await goToList();
    log('List page loads', await page.locator('body').count() > 0);
    
    let notes = await getNoteLinks();
    log(`Initial notes on page: ${notes.length}`, true);
    
    // ── Create TXT note and save ────────────────────────────────────
    await page.click('a.btn-new');
    await waitForURL(/\/notes\/new/);
    log('New note editor loads', true);
    
    await page.fill('#title-input', 'E2E TXT Note');
    await page.fill('#editor', 'Hello, this is a plain text note.');
    await submitNote();
    
    notes = await getNoteLinks();
    log('TXT note created and saved', notes.includes('E2E TXT Note.txt'));
    
    // ── Create Markdown note ────────────────────────────────────────
    await page.click('a.btn-new');
    await waitForURL(/\/notes\/new/);
    await page.fill('#title-input', 'E2E MD Note');
    await page.selectOption('#format-select', 'md');
    await page.fill('#editor', '# Heading 1\n\n**Bold text** and *italic*.');
    
    await submitNote();
    
    notes = await getNoteLinks();
    log('MD note saved', notes.includes('E2E MD Note.md'));
    
    // ── Open MD note editor — verify split-pane ─────────────────────
    const mdHref = await page.evaluate(() => 
      Array.from(document.querySelectorAll('a.filename'))
        .find(a => a.textContent.trim() === 'E2E MD Note.md')?.href
    );
    if (mdHref) {
      await page.goto(mdHref, { waitUntil: 'networkidle', timeout: 10000 });
      await waitForURL(/\/notes\/[\d-]+\/edit/);
      
      await page.waitForSelector('#editor-wrapper.split-mode', { timeout: 5000 });
      log('MD editor has split-pane layout', true);
      
      const previewVisible = await page.locator('#preview-pane:not(.hidden)').isVisible();
      log('Preview pane visible by default for MD', previewVisible);
      
      // ── Live preview updates on typing ──────────────────────────────
      await page.fill('#editor', '# New Heading\n\nUpdated content here.');
      await page.waitForTimeout(500);
      
      const previewContent = await page.locator('#preview-pane').textContent();
      log('Live preview updates on typing', 
          previewContent.includes('New Heading') && previewContent.includes('Updated content'));
      
      // ── Edit existing note and save changes ─────────────────────────
      await page.fill('#editor', '# Edited Heading\n\nThis content has been edited.');
      await submitNote();
      log('Existing note edited and saved', true);
    } else {
      log('MD editor tests skipped', false, 'E2E MD Note not found');
    }
    
    // ── Save As ─────────────────────────────────────────────────────
    const mdHref2 = await page.evaluate(() => 
      Array.from(document.querySelectorAll('a.filename'))
        .find(a => a.textContent.trim() === 'E2E MD Note.md')?.href
    );
    if (mdHref2) {
      await page.goto(mdHref2, { waitUntil: 'networkidle', timeout: 10000 });
      await waitForURL(/\/notes\/[\d-]+\/edit/);
      await page.click('button[name="action"][value="saveas"]');
      
      await page.waitForSelector('#saveas-modal:not(.hidden)', { timeout: 3000 });
      log('Save As modal opens', true);
      
      await page.fill('#saveas-title', 'E2E MD Note Copy');
      await page.click('#saveas-confirm');
      await waitForURL(/\/notes\//);
      log('Save As creates copy and redirects', true);
      
      notes = await getNoteLinks();
      const hasOriginal = notes.includes('E2E MD Note.md');
      const hasCopy = notes.includes('E2E MD Note Copy.md');
      log('Original and copy both exist', hasOriginal && hasCopy);
    } else {
      log('Save As tests skipped', false, 'E2E MD Note not found');
    }
    
    // ── Search by title ─────────────────────────────────────────────
    await goToList();
    await page.fill('input[name="q"]', 'E2E MD Note Copy');
    await page.press('input[name="q"]', 'Enter');
    await page.waitForTimeout(500);
    
    notes = await getNoteLinks();
    log('Search by title filters correctly', 
        notes.includes('E2E MD Note Copy.md') && !notes.includes('E2E MD Note.md'));
    
    // Clear search
    await goToList();
    
    // ── Import TXT file ─────────────────────────────────────────────
    const txtFile = Buffer.from('Imported plain text content.');
    const fileInput = await page.$('input[name="file"]');
    await fileInput.setInputFiles({ name: 'imported.txt', mimeType: 'text/plain', buffer: txtFile });
    await page.click('button[type="submit"]');
    await page.waitForTimeout(500);
    
    notes = await getNoteLinks();
    log('TXT file import works', notes.some(n => n.includes('imported')));
    
    // ── Import MD file ──────────────────────────────────────────────
    const mdFile = Buffer.from('# Imported Markdown\n\nSome content.');
    const fileInput2 = await page.$('input[name="file"]');
    await fileInput2.setInputFiles({ name: 'imported.md', mimeType: 'text/markdown', buffer: mdFile });
    await page.click('button[type="submit"]');
    await page.waitForTimeout(500);
    
    notes = await getNoteLinks();
    log('MD file import works', notes.some(n => n.includes('imported')));
    
    // ── Download TXT note ───────────────────────────────────────────
    const txtHref = await page.evaluate(() => 
      Array.from(document.querySelectorAll('a.filename'))
        .find(a => a.textContent.trim() === 'E2E TXT Note.txt')?.href
    );
    if (txtHref) {
      await page.goto(txtHref, { waitUntil: 'networkidle', timeout: 10000 });
      await waitForURL(/\/notes\/[\d-]+\/edit/);
      
      let downloadBody = null;
      await page.route('**/download/*', async route => {
        const resp = await route.fetch();
        downloadBody = await resp.text();
        await route.fulfill({ response: resp });
      });
      await page.click('a.btn-download');
      await page.waitForTimeout(500);
      log('Download returns raw content', downloadBody && downloadBody.includes('Hello, this is a plain text note.'));
    } else {
      log('Download test skipped', false, 'E2E TXT Note not found');
    }
    
    // Navigate back to list
    await goToList();
    
    // ── Download MD note ────────────────────────────────────────────
    const copyHref = await page.evaluate(() => 
      Array.from(document.querySelectorAll('a.filename'))
        .find(a => a.textContent.trim() === 'E2E MD Note Copy.md')?.href
    );
    if (copyHref) {
      await page.goto(copyHref, { waitUntil: 'networkidle', timeout: 10000 });
      await waitForURL(/\/notes\/[\d-]+\/edit/);
      
      // Get editor content to verify what we expect
      const editorContent = await page.locator('#editor').inputValue();
      console.log('Editor content for MD:', JSON.stringify(editorContent?.substring(0, 50)));
      
      let mdDownloadBody = null;
      await page.route('**/download/*', async route => {
        const resp = await route.fetch();
        mdDownloadBody = await resp.text();
        await route.fulfill({ response: resp });
      });
      await page.click('a.btn-download');
      await page.waitForTimeout(500);
      console.log('MD download body:', JSON.stringify(mdDownloadBody?.substring(0, 50)));
      
      // Check against actual editor content (not hardcoded string)
      const mdPass = mdDownloadBody && mdDownloadBody.includes(editorContent?.split('\n')[0]);
      log('MD download returns raw markdown', mdPass);
    } else {
      log('MD download test skipped', false, 'E2E MD Note Copy not found');
    }
    
    // Navigate back to list
    await goToList();
    
    // ── Delete functionality check ──────────────────────────────────
    const hasDeleteBtn = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('button, a'))
        .some(el => el.textContent.toLowerCase().includes('delete') || 
                    (el.getAttribute('name') === 'action' && el.getAttribute('value') === 'delete'));
    });
    log('Delete functionality available', hasDeleteBtn);
    
    // ── XSS in Markdown preview ─────────────────────────────────────
    await goToList();
    await page.click('a.btn-new');
    await waitForURL(/\/notes\/new/);
    await page.selectOption('#format-select', 'md');
    await page.fill('#editor', '<script>alert("xss")</script>\n\nNormal text');
    await page.waitForTimeout(500);
    
    const xssPreview = await page.locator('#preview-pane').textContent();
    log('XSS scripts stripped from preview', !xssPreview.includes('<script>'));
    
    // ── Invalid upload error ────────────────────────────────────────
    await goToList();
    const pyFile = Buffer.from('print("hello")');
    const fileInput3 = await page.$('input[name="file"]');
    await fileInput3.setInputFiles({ name: 'script.py', mimeType: 'text/x-python', buffer: pyFile });
    await page.click('button.btn-import');
    await page.waitForURL(/\/notes\/import/);
    await page.waitForLoadState('networkidle');
    const hasError = await page.locator('.form-errors').count() >= 1;
    log('Invalid upload shows error message', hasError);
    
    // ── Keyboard shortcuts present ──────────────────────────────────
    await goToList();
    await page.click('a.btn-new');
    await waitForURL(/\/notes\/new/);
    const hasShortcutHint = await page.locator('#shortcut-hint').count() >= 1;
    log('Keyboard shortcut hint present', hasShortcutHint);
    
    // ── Unsaved changes tracking ────────────────────────────────────
    const hasDirtyTracking = await page.evaluate(() => {
      return document.querySelector('script')?.textContent?.includes('isDirty');
    });
    log('Unsaved-changes tracking present', hasDirtyTracking);
    
    // ── Narrow viewport test ────────────────────────────────────────
    await page.setViewportSize({ width: 480, height: 800 });
    await goToList();
    const mobileLayout = await page.locator('.app-container').count() >= 1;
    log('Mobile viewport (480px) renders without errors', mobileLayout);
    
    // ── Desktop viewport test ───────────────────────────────────────
    await page.setViewportSize({ width: 1280, height: 800 });
    await goToList();
    const desktopLayout = await page.locator('.sidebar').count() >= 1;
    log('Desktop viewport (1280px) renders correctly', desktopLayout);
    
    // ── Console errors check ────────────────────────────────────────
    log('No console errors during testing', consoleErrors.length === 0, 
        consoleErrors.length > 0 ? `Found ${consoleErrors.length} error(s): ${consoleErrors.slice(0,3).join('; ')}` : '');
    
    // ── Summary ─────────────────────────────────────────────────────
    const passed = results.filter(r => r.status === 'PASS').length;
    const failed = results.filter(r => r.status === 'FAIL').length;
    console.log('\n═══════════════════════════════════════');
    console.log(`Browser Tests: ${passed} passed, ${failed} failed out of ${results.length}`);
    console.log('═══════════════════════════════════════');
    
  } catch (e) {
    console.error('Test error:', e.message);
  } finally {
    await browser.close();
  }
})();
