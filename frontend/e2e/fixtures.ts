import { test as base, expect } from '@playwright/test';

/**
 * Custom test fixtures for E2E tests.
 *
 * Provides common utilities and authenticated user contexts.
 */

// Test user credentials (should match seeded test data)
export const TEST_USERS = {
  admin: {
    email: 'admin@bobby.test',
    password: 'AdminPassword123!',
    role: 'admin',
  },
  commercial: {
    email: 'commercial@bobby.test',
    password: 'CommercialPassword123!',
    role: 'commercial',
  },
  rh: {
    email: 'rh@bobby.test',
    password: 'RhPassword123!',
    role: 'rh',
  },
  user: {
    email: 'user@bobby.test',
    password: 'UserPassword123!',
    role: 'user',
  },
} as const;

type TestUser = keyof typeof TEST_USERS;

/**
 * Extended test fixtures with authentication helpers.
 */
export const test = base.extend<{
  authenticatedPage: {
    login: (userType: TestUser) => Promise<void>;
    logout: () => Promise<void>;
  };
}>({
  authenticatedPage: async ({ page }, use) => {
    const login = async (userType: TestUser) => {
      const user = TEST_USERS[userType];
      await page.goto('/login');
      await page.getByLabel(/email/i).fill(user.email);
      await page.getByLabel(/mot de passe/i).fill(user.password);
      await page.getByRole('button', { name: /se connecter/i }).click();

      // Wait for redirect to dashboard
      await expect(page).toHaveURL(/dashboard/, { timeout: 10000 });
    };

    const logout = async () => {
      // Click on user menu and logout
      await page.getByRole('button', { name: /profil|compte|menu/i }).click();
      await page.getByRole('menuitem', { name: /déconnexion/i }).click();

      // Wait for redirect to login
      await expect(page).toHaveURL(/login/);
    };

    await use({ login, logout });
  },
});

export { expect } from '@playwright/test';

/**
 * Page object models for common pages.
 */
export class LoginPage {
  constructor(private page: unknown) {}

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.page.getByLabel(/email/i).fill(email);
    await this.page.getByLabel(/mot de passe/i).fill(password);
    await this.page.getByRole('button', { name: /se connecter/i }).click();
  }

  async expectError(message: RegExp) {
    await expect(this.page.getByText(message)).toBeVisible();
  }
}

export class DashboardPage {
  constructor(private page: unknown) {}

  async goto() {
    await this.page.goto('/dashboard');
  }

  async expectWelcomeMessage() {
    await expect(
      this.page.getByRole('heading', { name: /tableau de bord|bienvenue/i })
    ).toBeVisible();
  }
}

export class OpportunitiesPage {
  constructor(private page: unknown) {}

  async goto() {
    await this.page.goto('/opportunities');
  }

  async expectOpportunitiesList() {
    await expect(
      this.page.getByRole('heading', { name: /opportunités/i })
    ).toBeVisible();
  }

  async clickFirstOpportunity() {
    await this.page.locator('[data-testid="opportunity-card"]').first().click();
  }

  async submitCooptation(data: {
    candidateName: string;
    candidateEmail: string;
    candidatePhone?: string;
  }) {
    await this.page.getByLabel(/nom.*candidat/i).fill(data.candidateName);
    await this.page.getByLabel(/email.*candidat/i).fill(data.candidateEmail);
    if (data.candidatePhone) {
      await this.page.getByLabel(/téléphone/i).fill(data.candidatePhone);
    }
    await this.page.getByRole('button', { name: /proposer|soumettre/i }).click();
  }
}
