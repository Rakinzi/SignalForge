import { expect, test } from '@playwright/test';
import { signIn } from './helpers/auth';

test.describe('Admin role route behavior', () => {
	test('admin can open restricted pages without access-limited state', async ({ page }) => {
		await signIn(page, 'admin', 'admin');

		await page.goto('/settings');
		await expect(page.getByRole('heading', { name: 'System Settings' })).toBeVisible();
		await expect(page.getByText('System settings are admin-only')).toHaveCount(0);

		await page.goto('/detection');
		await expect(page.getByRole('heading', { name: 'Detection Dashboard' })).toBeVisible();
		await expect(page.getByText('Access Limited')).toHaveCount(0);

		await page.goto('/evaluation');
		await expect(page.getByRole('heading', { name: 'Evaluation Metrics' })).toBeVisible();
		await expect(page.getByText('Access Limited')).toHaveCount(0);

		await page.goto('/reports');
		await expect(page.getByRole('heading', { name: 'Detection Reports' })).toBeVisible();
		await expect(page.getByText('Access Limited')).toHaveCount(0);
	});
});
