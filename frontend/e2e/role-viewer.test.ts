import { expect, test } from '@playwright/test';
import { signIn } from './helpers/auth';

test.describe('Viewer role route behavior', () => {
	test('viewer sees safe permission handling on restricted pages', async ({ page }) => {
		await signIn(page, 'viewer', 'viewer');

		await page.goto('/detection');
		await expect(page.getByText(/^forbidden$/i)).toHaveCount(0);
		await expect(page.getByRole('heading', { name: 'Detection Dashboard' })).toBeVisible();

		await page.goto('/evaluation');
		await expect(page.getByText(/^forbidden$/i)).toHaveCount(0);
		await expect(page.getByRole('heading', { name: 'Evaluation Metrics', exact: true })).toBeVisible();

		await page.goto('/reports');
		await expect(page.getByText(/^forbidden$/i)).toHaveCount(0);
		await expect(page.getByRole('heading', { name: 'Detection Reports' })).toBeVisible();

		await page.goto('/settings');
		await expect(page.getByText('System settings are admin-only')).toBeVisible();
	});

	test('viewer can still access operational pages', async ({ page }) => {
		await signIn(page, 'viewer', 'viewer');

		await page.goto('/');
		await expect(page.getByRole('heading', { name: 'Overview' })).toBeVisible();

		await page.goto('/flows');
		await expect(page.getByRole('heading', { name: 'Network Flows' })).toBeVisible();

		await page.goto('/alerts');
		await expect(page.getByRole('heading', { name: 'Security Alerts' })).toBeVisible();
	});
});
