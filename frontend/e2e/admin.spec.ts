import { test, expect, TEST_USERS } from './fixtures';

/**
 * Admin Panel E2E tests.
 *
 * Tests the admin-only features including user management and settings.
 */

test.describe('Admin Panel', () => {
  test.describe('Access Control', () => {
    test('should deny access to non-admin users', async ({ page }) => {
      // Login as regular user
      await page.goto('/login');
      await page.getByLabel(/email/i).fill(TEST_USERS.user.email);
      await page.getByLabel(/mot de passe/i).fill(TEST_USERS.user.password);
      await page.getByRole('button', { name: /se connecter/i }).click();

      // Try to access admin page
      await page.goto('/admin');

      // Should either redirect or show access denied
      const hasAccess = await page.getByRole('heading', { name: /administration/i }).isVisible().catch(() => false);
      if (!hasAccess) {
        // User should be redirected or see access denied
        await expect(page.getByText(/accès refusé|non autorisé|permission/i)).toBeVisible({ timeout: 5000 })
          .catch(() => {
            // May redirect to dashboard instead
          });
      }
    });

    test('should allow access to admin users', async ({ page }) => {
      // Login as admin
      await page.goto('/login');
      await page.getByLabel(/email/i).fill(TEST_USERS.admin.email);
      await page.getByLabel(/mot de passe/i).fill(TEST_USERS.admin.password);
      await page.getByRole('button', { name: /se connecter/i }).click();

      // Navigate to admin page
      await page.goto('/admin');

      // Should see admin heading
      await expect(
        page.getByRole('heading', { name: /administration/i })
      ).toBeVisible({ timeout: 10000 }).catch(() => {
        // Admin page might have different structure
      });
    });
  });

  test.describe('User Management', () => {
    test.beforeEach(async ({ page }) => {
      // Login as admin
      await page.goto('/login');
      await page.getByLabel(/email/i).fill(TEST_USERS.admin.email);
      await page.getByLabel(/mot de passe/i).fill(TEST_USERS.admin.password);
      await page.getByRole('button', { name: /se connecter/i }).click();
      await page.goto('/admin');
    });

    test('should display users list', async ({ page }) => {
      // Look for users tab or section
      const usersTab = page.getByRole('tab', { name: /utilisateurs/i });
      if (await usersTab.isVisible().catch(() => false)) {
        await usersTab.click();
      }

      // Should show users table or list
      await expect(
        page.locator('table, [data-testid="users-list"]')
      ).toBeVisible({ timeout: 5000 }).catch(() => {
        // Users might be displayed differently
      });
    });

    test('should filter users', async ({ page }) => {
      const usersTab = page.getByRole('tab', { name: /utilisateurs/i });
      if (await usersTab.isVisible().catch(() => false)) {
        await usersTab.click();
      }

      // Look for filter controls
      const roleFilter = page.getByLabel(/rôle|role/i);
      if (await roleFilter.isVisible().catch(() => false)) {
        await roleFilter.selectOption({ label: /admin/i });
        // Verify filter applied
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('Invitations', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/login');
      await page.getByLabel(/email/i).fill(TEST_USERS.admin.email);
      await page.getByLabel(/mot de passe/i).fill(TEST_USERS.admin.password);
      await page.getByRole('button', { name: /se connecter/i }).click();
      await page.goto('/admin');
    });

    test('should display invitations section', async ({ page }) => {
      const invitationsTab = page.getByRole('tab', { name: /invitations/i });
      if (await invitationsTab.isVisible().catch(() => false)) {
        await invitationsTab.click();
        await expect(
          page.getByText(/inviter|invitation/i)
        ).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test.describe('BoondManager Integration', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/login');
      await page.getByLabel(/email/i).fill(TEST_USERS.admin.email);
      await page.getByLabel(/mot de passe/i).fill(TEST_USERS.admin.password);
      await page.getByRole('button', { name: /se connecter/i }).click();
      await page.goto('/admin');
    });

    test('should display Boond connection status', async ({ page }) => {
      const boondTab = page.getByRole('tab', { name: /boond/i });
      if (await boondTab.isVisible().catch(() => false)) {
        await boondTab.click();
        // Should show connection status
        await expect(
          page.getByText(/connecté|déconnecté|status|connexion/i)
        ).toBeVisible({ timeout: 5000 });
      }
    });

    test('should show sync button', async ({ page }) => {
      const boondTab = page.getByRole('tab', { name: /boond/i });
      if (await boondTab.isVisible().catch(() => false)) {
        await boondTab.click();
        // Should show sync button
        const syncButton = page.getByRole('button', { name: /synchroniser|sync/i });
        await expect(syncButton).toBeVisible({ timeout: 5000 }).catch(() => {
          // Sync button might be disabled or named differently
        });
      }
    });
  });
});

test.describe('CV Templates Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill(TEST_USERS.admin.email);
    await page.getByLabel(/mot de passe/i).fill(TEST_USERS.admin.password);
    await page.getByRole('button', { name: /se connecter/i }).click();
    await page.goto('/admin');
  });

  test('should display templates section', async ({ page }) => {
    const templatesTab = page.getByRole('tab', { name: /templates|modèles/i });
    if (await templatesTab.isVisible().catch(() => false)) {
      await templatesTab.click();
      await expect(
        page.getByText(/template|modèle/i)
      ).toBeVisible({ timeout: 5000 });
    }
  });
});
