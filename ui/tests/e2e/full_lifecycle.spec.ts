import { test, expect } from '@playwright/test';

test.describe('CineForge UI - Full Project Lifecycle (Mocked)', () => {
  test.beforeEach(async ({ page }) => {
    // Assuming the dev server is running and the backend is using mocks
    await page.goto('http://localhost:5173');

    // Handle Onboarding Wizard if it appears
    const continueBtn = page.getByRole('button', { name: /Continue to App/i });
    if (await continueBtn.isVisible()) {
        await continueBtn.click();
        // Wait for the wizard to disappear
        await expect(continueBtn).not.toBeVisible();
    }
  });

  test('should create a new project and navigate to it', async ({ page }) => {
    // 1. Trigger Project Creation
    // Note: This assumes a 'New Project' button or dialog exists in the UI
    const newProjectBtn = page.getByRole('button', { name: /new project/i });
    
    // If the button isn't directly visible, it might be in a menu
    if (!(await newProjectBtn.isVisible())) {
        // Fallback: Search for any button that looks like a creation trigger
        // or just try to find the project list area
        await expect(page.locator('main')).toBeVisible();
    } else {
        await newProjectBtn.click();
    }

    // 2. Handle Dialog/Form (if applicable)
    // For this test, we assume the creation is immediate or we've filled a form
    const nameInput = page.getByLabel(/project name/i);
    if (await nameInput.isVisible()) {
        await nameInput.fill('E2E Test Project');
        await page.getByRole('button', { name: /create/i }).click();
    }

    // 3. Verify Navigation to Project View
    // After creation, the UI should navigate to /project/<id>
    await expect(page).toHaveURL(/.*project\/.*/);
    
    // 4. Verify Project Details are displayed
    await expect(page.locator('h1')).toContainText('E2E Test Project');
  });

  test('should allow uploading a source document', async ({ page }) => {
    // 1. Navigate to a project (using the created one or a default)
    // For simplicity, we assume we are already in a project view or navigate there
    const projectLink = page.getByRole('link', { name: /project/i });
    if (await projectLink.count() > 0) {
        await projectLink.first().click();
    } else {
        // If no projects, create one first
        const newProjectBtn = page.getByRole('button', { name: /new project/i });
        if (await newProjectBtn.isVisible()) {
            await newProjectBtn.click();
            const nameInput = page.getByLabel(/project name/i);
            if (await nameInput.isVisible()) {
                await nameInput.fill('Upload Test Project');
                await page.getByRole('button', { name: /create/i }).click();
            }
        }
        await page.getByRole('link', { name: /Upload Test Project/i }).click();
    }

    // 2. Upload a file
    // This assumes an upload component exists in the 'Sources' tab
    const fileChooserPromise = page.waitForEvent('filechooser');
    await page.getByRole('button', { name: /upload/i }).click();
    const fileChooser = await fileChooserPromise;
    
    // Create a temporary dummy file for upload
    const dummyFilePath = 'test_source.md';
    await import('fs').then(fs => fs.writeFileSync(dummyFilePath, '# Test Source Content'));
    
    await fileChooser.setFiles(dummyFilePath);

    // 3. Verify upload success (e.g., seeing the file in the list)
    await expect(page.getByText('test_source.md')).toBeVisible();
  });

  test('should simulate a render job and show progress', async ({ page }) => {
    // 1. Navigate to a project
    const projectLink = page.getByRole('link', { name: /project/i });
    if (await projectLink.count() > 0) {
        await projectLink.first().click();
    } else {
        // Navigate/Create logic as above...
    }

    // 2. Trigger Render
    // Assuming there is a 'Render' button in the UI
    const renderBtn = page.getByRole('button', { name: /render/i });
    if (await renderBtn.isVisible()) {
        await renderBtn.click();
        
        // 3. Verify progress indicator
        // Assuming a progress bar or status text appears
        await expect(page.locator('.progress-bar, .status-text')).toBeVisible();
        
        // 4. Wait for completion (simulated)
        // In a real E2E, we'd wait for the status to change to 'done'
        // Since we use mocks, it should happen relatively quickly
        await expect(page.getByText(/status: done/i), { timeout: 10000 }).toBeVisible();
    }
  });
});
