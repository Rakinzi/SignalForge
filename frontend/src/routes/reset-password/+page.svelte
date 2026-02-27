<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	let newPassword = $state('');
	let confirmPassword = $state('');
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);
	const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

	const token = $derived($page.url.searchParams.get('token') ?? '');

	async function handleSubmit(e: Event) {
		e.preventDefault();
		error = null;
		success = null;
		if (!token) {
			error = 'Missing reset token';
			return;
		}
		if (newPassword.length < 8) {
			error = 'Password must be at least 8 characters';
			return;
		}
		if (newPassword !== confirmPassword) {
			error = 'Passwords do not match';
			return;
		}
		isLoading = true;
		try {
			const res = await fetch(`${API_BASE_URL}/auth/reset-password`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
				body: new URLSearchParams({ token, new_password: newPassword })
			});
			if (!res.ok) {
				const msg = await res.json().catch(() => ({ detail: 'Failed to reset password' }));
				throw new Error(msg.detail || 'Failed to reset password');
			}
			success = 'Password updated successfully. Redirecting to login...';
			setTimeout(() => goto('/login'), 1400);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to reset password';
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head><title>Reset Password - SignalForge</title></svelte:head>

<div class="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
	<div class="w-full max-w-md bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg shadow-lg p-8">
		<h1 class="text-2xl font-semibold text-[var(--text-primary)] mb-2">Reset Password</h1>
		<p class="text-sm text-[var(--text-secondary)] mb-6">Set a new password for your account.</p>

		{#if error}
			<div class="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-md text-sm text-red-500">{error}</div>
		{/if}
		{#if success}
			<div class="mb-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-md text-sm text-emerald-600">{success}</div>
		{/if}

		<form onsubmit={handleSubmit} class="space-y-4">
			<input
				type="password"
				bind:value={newPassword}
				required
				placeholder="New password"
				class="w-full px-4 py-2 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-md text-[var(--text-primary)]"
			/>
			<input
				type="password"
				bind:value={confirmPassword}
				required
				placeholder="Confirm new password"
				class="w-full px-4 py-2 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-md text-[var(--text-primary)]"
			/>
			<button
				type="submit"
				disabled={isLoading}
				class="w-full bg-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/90 text-white font-medium py-2.5 px-4 rounded-md disabled:opacity-50"
			>
				{isLoading ? 'Updating...' : 'Update Password'}
			</button>
		</form>
	</div>
</div>
