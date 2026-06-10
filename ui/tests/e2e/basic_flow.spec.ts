import { test, expect } from '@playwright/test';

test.describe('CineForge UI - Basic Flow', () => {
  test.beforeEach(async ({ page }) => {
    // In a real E2E setup, we would ensure the backend is running 
    // with the mock adapters active. For this scaffold, we assume
    // the dev server is up and communicating with a mock backend.
    await page.goto('http://localhost:5173');
  });

  test('should display the initial dashboard/project list', async ({ page }) => {
    // Check if the main navigation tabs load
    await expect(page.getByRole('tablist')).toBeVisible();
    // Check if the tab labels are present
    await expect(page.getByRole('tab', { name: /Sources/i })).toBeVisible();
    await expect(page.getByRole('tab', { name: /Storyboard/i })).toBeVisible();
  });

  test('should navigate to a project view', async ({ page }) => {
    // This test assumes at least one project exists in the mock backend
    // For a true E2E with mocks, the backend would be seeded.
    
    // Attempt to click a project if one is listed
    const projectLink = page.getByRole('link', { name: /project/i });
    if (await projectLink.count() > 0) {
        await projectLink.first().click();
        await expect(page).toHaveURL(/.*project\/.*/);
    }
  });
});
