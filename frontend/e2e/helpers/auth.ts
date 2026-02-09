import { expect, type Page } from '@playwright/test';

export async function signIn(page: Page, username: string, password: string) {
	await page.goto('/login');
	await page.fill('#username', username);
	await page.fill('#password', password);
	await page.click("button[type='submit']");

	try {
		await expect(page).toHaveURL(/\/$/, { timeout: 15000 });
	} catch (error) {
		const loginError = await page
			.locator('text=/invalid|failed|incorrect|unauthorized/i')
			.first()
			.textContent()
			.catch(() => null);
		throw new Error(
			`Login did not redirect for user "${username}". URL: ${page.url()}${loginError ? `, error: ${loginError}` : ''}`,
			{ cause: error }
		);
	}
}
