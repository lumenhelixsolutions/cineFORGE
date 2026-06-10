# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: full_lifecycle.spec.ts >> CineForge UI - Full Project Lifecycle (Mocked) >> should create a new project and navigate to it
- Location: tests\e2e\full_lifecycle.spec.ts:17:3

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByRole('button', { name: /new project/i })
    - locator resolved to <button title="New project (N)" aria-label="Create new project" class="btn-primary text-xs px-2 py-1">New</button>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <div class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">…</div> intercepts pointer events
    - retrying click action
    - waiting 20ms
    2 × waiting for element to be visible, enabled and stable
      - element is visible, enabled and stable
      - scrolling into view if needed
      - done scrolling
      - <div class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">…</div> intercepts pointer events
    - retrying click action
      - waiting 100ms
    43 × waiting for element to be visible, enabled and stable
       - element is visible, enabled and stable
       - scrolling into view if needed
       - done scrolling
       - <div class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">…</div> intercepts pointer events
     - retrying click action
       - waiting 500ms

```

# Page snapshot

```yaml
- generic [ref=e2]:
  - generic [ref=e4]:
    - generic [ref=e6]:
      - generic [ref=e7]:
        - heading "CineForge Setup" [level=1] [ref=e8]
        - paragraph [ref=e9]: Running system diagnostics before first use...
      - generic [ref=e10]: blocked
    - generic [ref=e13] [cursor=pointer]:
      - generic [ref=e14]: ✗
      - generic [ref=e15]: Diagnostics Endpoint
      - generic [ref=e16]: error
    - generic [ref=e17]:
      - generic [ref=e18]:
        - generic [ref=e19]: 0 passed · 0 warnings · 1 errors
        - button "Re-run Diagnostics" [ref=e20] [cursor=pointer]
      - generic [ref=e21]:
        - generic [ref=e22]: "Required fixes:"
        - generic [ref=e24]: "Ensure backend is running: python -m backend.app"
      - button "Fix Errors Above to Continue" [disabled] [ref=e26]
  - generic [ref=e27]:
    - generic [ref=e29]:
      - heading "Projects" [level=2] [ref=e30]
      - button "Create new project" [ref=e31] [cursor=pointer]: New
    - generic [ref=e33]:
      - tablist "Main tabs" [ref=e34]:
        - tab "Sources" [ref=e35] [cursor=pointer]
        - tab "Storyboard" [selected] [ref=e36] [cursor=pointer]
        - tab "Timeline" [ref=e37] [cursor=pointer]
        - tab "Preview" [ref=e38] [cursor=pointer]
        - tab "Trailer" [ref=e39] [cursor=pointer]
        - tab "Export" [ref=e40] [cursor=pointer]
        - tab "StackBuilder" [ref=e41] [cursor=pointer]
        - button "Open settings" [ref=e42] [cursor=pointer]: ⚙ Settings
        - 'generic "Active project: None"'
      - main [ref=e44]:
        - status "No project selected" [ref=e46]: Select a project or create one to begin
        - generic: Press ? for shortcuts
    - generic [ref=e47]:
      - heading "Inspector" [level=2] [ref=e49]
      - generic [ref=e50]: No project selected
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('CineForge UI - Full Project Lifecycle (Mocked)', () => {
  4   |   test.beforeEach(async ({ page }) => {
  5   |     // Assuming the dev server is running and the backend is using mocks
  6   |     await page.goto('http://localhost:5173');
  7   | 
  8   |     // Handle Onboarding Wizard if it appears
  9   |     const continueBtn = page.getByRole('button', { name: /Continue to App/i });
  10  |     if (await continueBtn.isVisible()) {
  11  |         await continueBtn.click();
  12  |         // Wait for the wizard to disappear
  13  |         await expect(continueBtn).not.toBeVisible();
  14  |     }
  15  |   });
  16  | 
  17  |   test('should create a new project and navigate to it', async ({ page }) => {
  18  |     // 1. Trigger Project Creation
  19  |     // Note: This assumes a 'New Project' button or dialog exists in the UI
  20  |     const newProjectBtn = page.getByRole('button', { name: /new project/i });
  21  |     
  22  |     // If the button isn't directly visible, it might be in a menu
  23  |     if (!(await newProjectBtn.isVisible())) {
  24  |         // Fallback: Search for any button that looks like a creation trigger
  25  |         // or just try to find the project list area
  26  |         await expect(page.locator('main')).toBeVisible();
  27  |     } else {
> 28  |         await newProjectBtn.click();
      |                             ^ Error: locator.click: Test timeout of 30000ms exceeded.
  29  |     }
  30  | 
  31  |     // 2. Handle Dialog/Form (if applicable)
  32  |     // For this test, we assume the creation is immediate or we've filled a form
  33  |     const nameInput = page.getByLabel(/project name/i);
  34  |     if (await nameInput.isVisible()) {
  35  |         await nameInput.fill('E2E Test Project');
  36  |         await page.getByRole('button', { name: /create/i }).click();
  37  |     }
  38  | 
  39  |     // 3. Verify Navigation to Project View
  40  |     // After creation, the UI should navigate to /project/<id>
  41  |     await expect(page).toHaveURL(/.*project\/.*/);
  42  |     
  43  |     // 4. Verify Project Details are displayed
  44  |     await expect(page.locator('h1')).toContainText('E2E Test Project');
  45  |   });
  46  | 
  47  |   test('should allow uploading a source document', async ({ page }) => {
  48  |     // 1. Navigate to a project (using the created one or a default)
  49  |     // For simplicity, we assume we are already in a project view or navigate there
  50  |     const projectLink = page.getByRole('link', { name: /project/i });
  51  |     if (await projectLink.count() > 0) {
  52  |         await projectLink.first().click();
  53  |     } else {
  54  |         // If no projects, create one first
  55  |         const newProjectBtn = page.getByRole('button', { name: /new project/i });
  56  |         if (await newProjectBtn.isVisible()) {
  57  |             await newProjectBtn.click();
  58  |             const nameInput = page.getByLabel(/project name/i);
  59  |             if (await nameInput.isVisible()) {
  60  |                 await nameInput.fill('Upload Test Project');
  61  |                 await page.getByRole('button', { name: /create/i }).click();
  62  |             }
  63  |         }
  64  |         await page.getByRole('link', { name: /Upload Test Project/i }).click();
  65  |     }
  66  | 
  67  |     // 2. Upload a file
  68  |     // This assumes an upload component exists in the 'Sources' tab
  69  |     const fileChooserPromise = page.waitForEvent('filechooser');
  70  |     await page.getByRole('button', { name: /upload/i }).click();
  71  |     const fileChooser = await fileChooserPromise;
  72  |     
  73  |     // Create a temporary dummy file for upload
  74  |     const dummyFilePath = 'test_source.md';
  75  |     await import('fs').then(fs => fs.writeFileSync(dummyFilePath, '# Test Source Content'));
  76  |     
  77  |     await fileChooser.setFiles(dummyFilePath);
  78  | 
  79  |     // 3. Verify upload success (e.g., seeing the file in the list)
  80  |     await expect(page.getByText('test_source.md')).toBeVisible();
  81  |   });
  82  | 
  83  |   test('should simulate a render job and show progress', async ({ page }) => {
  84  |     // 1. Navigate to a project
  85  |     const projectLink = page.getByRole('link', { name: /project/i });
  86  |     if (await projectLink.count() > 0) {
  87  |         await projectLink.first().click();
  88  |     } else {
  89  |         // Navigate/Create logic as above...
  90  |     }
  91  | 
  92  |     // 2. Trigger Render
  93  |     // Assuming there is a 'Render' button in the UI
  94  |     const renderBtn = page.getByRole('button', { name: /render/i });
  95  |     if (await renderBtn.isVisible()) {
  96  |         await renderBtn.click();
  97  |         
  98  |         // 3. Verify progress indicator
  99  |         // Assuming a progress bar or status text appears
  100 |         await expect(page.locator('.progress-bar, .status-text')).toBeVisible();
  101 |         
  102 |         // 4. Wait for completion (simulated)
  103 |         // In a real E2E, we'd wait for the status to change to 'done'
  104 |         // Since we use mocks, it should happen relatively quickly
  105 |         await expect(page.getByText(/status: done/i), { timeout: 10000 }).toBeVisible();
  106 |     }
  107 |   });
  108 | });
  109 | 
```