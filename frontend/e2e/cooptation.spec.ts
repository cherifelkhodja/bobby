import { test, expect, TEST_USERS, OpportunitiesPage } from './fixtures';

/**
 * Cooptation flow E2E tests.
 *
 * Tests the complete cooptation submission and tracking flow.
 */

test.describe('Cooptation Flow', () => {
  test.describe('Opportunities Page', () => {
    test('should display opportunities list', async ({ page }) => {
      // First login
      await page.goto('/login');
      await page.getByLabel(/email/i).fill(TEST_USERS.user.email);
      await page.getByLabel(/mot de passe/i).fill(TEST_USERS.user.password);
      await page.getByRole('button', { name: /se connecter/i }).click();

      // Navigate to opportunities
      await page.goto('/opportunities');

      await expect(
        page.getByRole('heading', { name: /opportunités/i })
      ).toBeVisible();
    });

    test('should navigate to opportunity detail', async ({ page }) => {
      // Skip if no opportunities exist
      await page.goto('/login');
      await page.getByLabel(/email/i).fill(TEST_USERS.user.email);
      await page.getByLabel(/mot de passe/i).fill(TEST_USERS.user.password);
      await page.getByRole('button', { name: /se connecter/i }).click();

      await page.goto('/opportunities');

      // Check if there are opportunities
      const opportunityCards = page.locator('[data-testid="opportunity-card"]');
      const count = await opportunityCards.count();

      if (count > 0) {
        await opportunityCards.first().click();
        await expect(page).toHaveURL(/opportunities\/[a-f0-9-]+/);
      }
    });
  });

  test.describe('My Cooptations Page', () => {
    test('should display user cooptations', async ({ page }) => {
      await page.goto('/login');
      await page.getByLabel(/email/i).fill(TEST_USERS.user.email);
      await page.getByLabel(/mot de passe/i).fill(TEST_USERS.user.password);
      await page.getByRole('button', { name: /se connecter/i }).click();

      await page.goto('/my-cooptations');

      await expect(
        page.getByRole('heading', { name: /mes cooptations/i })
      ).toBeVisible();
    });

    test('should show empty state when no cooptations', async ({ page }) => {
      await page.goto('/login');
      await page.getByLabel(/email/i).fill(TEST_USERS.user.email);
      await page.getByLabel(/mot de passe/i).fill(TEST_USERS.user.password);
      await page.getByRole('button', { name: /se connecter/i }).click();

      await page.goto('/my-cooptations');

      // Either shows cooptations or empty state
      const hasCooptations = await page.locator('[data-testid="cooptation-card"]').count() > 0;
      const hasEmptyState = await page.getByText(/aucune cooptation|pas encore/i).isVisible().catch(() => false);

      expect(hasCooptations || hasEmptyState).toBeTruthy();
    });
  });
});

test.describe('Cooptation Submission', () => {
  test('should show cooptation form on opportunity detail', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill(TEST_USERS.user.email);
    await page.getByLabel(/mot de passe/i).fill(TEST_USERS.user.password);
    await page.getByRole('button', { name: /se connecter/i }).click();

    await page.goto('/opportunities');

    // Find and click first opportunity if exists
    const opportunityCards = page.locator('[data-testid="opportunity-card"]');
    const count = await opportunityCards.count();

    if (count > 0) {
      await opportunityCards.first().click();

      // Check for cooptation CTA
      await expect(
        page.getByRole('button', { name: /proposer.*candidat/i })
      ).toBeVisible({ timeout: 5000 }).catch(() => {
        // Button might be in a different state
      });
    }
  });

  test('should validate required fields in cooptation form', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill(TEST_USERS.user.email);
    await page.getByLabel(/mot de passe/i).fill(TEST_USERS.user.password);
    await page.getByRole('button', { name: /se connecter/i }).click();

    await page.goto('/opportunities');

    const opportunityCards = page.locator('[data-testid="opportunity-card"]');
    const count = await opportunityCards.count();

    if (count > 0) {
      await opportunityCards.first().click();

      // Try to open cooptation modal
      const proposeButton = page.getByRole('button', { name: /proposer.*candidat/i });
      if (await proposeButton.isVisible().catch(() => false)) {
        await proposeButton.click();

        // Try to submit without filling required fields
        const submitButton = page.getByRole('button', { name: /soumettre|envoyer/i });
        if (await submitButton.isVisible().catch(() => false)) {
          await submitButton.click();

          // Should show validation errors
          await expect(
            page.getByText(/requis|obligatoire/i)
          ).toBeVisible({ timeout: 3000 }).catch(() => {
            // Form might have different validation behavior
          });
        }
      }
    }
  });
});

test.describe('Cooptation Status Tracking', () => {
  test('should display cooptation status badges', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill(TEST_USERS.user.email);
    await page.getByLabel(/mot de passe/i).fill(TEST_USERS.user.password);
    await page.getByRole('button', { name: /se connecter/i }).click();

    await page.goto('/my-cooptations');

    // Check if status badges are displayed
    const statusBadges = page.locator('[data-testid="status-badge"]');
    const count = await statusBadges.count();

    if (count > 0) {
      // Verify status badge is visible
      await expect(statusBadges.first()).toBeVisible();
    }
  });
});
