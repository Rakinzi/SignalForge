<script lang="ts">
	import { goto } from '$app/navigation';

	let email = $state('');
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);

	const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

	async function handleSubmit(e: Event) {
		e.preventDefault();
		error = null;
		success = null;
		isLoading = true;
		try {
			const res = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
				body: new URLSearchParams({ email })
			});
			if (!res.ok) throw new Error('Failed to submit password reset request');
			success = 'If this email exists, a reset link has been sent.';
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to submit request';
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head><title>Forgot Password - SignalForge</title></svelte:head>

<div class="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
	<div class="w-full max-w-md bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg shadow-lg p-8">
		<h1 class="text-2xl font-semibold text-[var(--text-primary)] mb-2">Forgot Password</h1>
		<p class="text-sm text-[var(--text-secondary)] mb-6">Enter your account email to receive a reset link.</p>

		{#if error}
			<div class="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-md text-sm text-red-500">{error}</div>
		{/if}
		{#if success}
			<div class="mb-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-md text-sm text-emerald-600">{success}</div>
		{/if}

		<form onsubmit={handleSubmit} class="space-y-4">
			<input
				type="email"
				bind:value={email}
				required
				placeholder="your.email@example.com"
				class="w-full px-4 py-2 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-md text-[var(--text-primary)]"
			/>
			<button
				type="submit"
				disabled={isLoading}
				class="w-full bg-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/90 text-white font-medium py-2.5 px-4 rounded-md disabled:opacity-50"
			>
				{isLoading ? 'Sending...' : 'Send Reset Link'}
			</button>
		</form>

		<div class="mt-6 text-sm text-[var(--text-secondary)]">
			<a href="/login" class="text-[var(--accent-primary)] hover:underline">Back to login</a>
		</div>
	</div>
</div>
