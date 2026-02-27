<script lang="ts">
	import { page } from '$app/stores';

	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let success = $state<string | null>(null);

	const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
	const token = $derived($page.url.searchParams.get('token') ?? '');

	$effect(() => {
		async function verify() {
			if (!token) {
				error = 'Missing verification token';
				isLoading = false;
				return;
			}
			try {
				const res = await fetch(`${API_BASE_URL}/auth/verify-email?token=${encodeURIComponent(token)}`);
				if (!res.ok) {
					const msg = await res.json().catch(() => ({ detail: 'Verification failed' }));
					throw new Error(msg.detail || 'Verification failed');
				}
				success = 'Email verified successfully. You can now log in.';
			} catch (err) {
				error = err instanceof Error ? err.message : 'Verification failed';
			} finally {
				isLoading = false;
			}
		}
		verify();
	});
</script>

<svelte:head><title>Verify Email - SignalForge</title></svelte:head>

<div class="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
	<div class="w-full max-w-md bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg shadow-lg p-8">
		<h1 class="text-2xl font-semibold text-[var(--text-primary)] mb-4">Email Verification</h1>
		{#if isLoading}
			<p class="text-sm text-[var(--text-secondary)]">Verifying your email...</p>
		{:else if error}
			<div class="p-3 bg-red-500/10 border border-red-500/30 rounded-md text-sm text-red-500">{error}</div>
		{:else}
			<div class="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-md text-sm text-emerald-600">{success}</div>
		{/if}
		<div class="mt-6 text-sm">
			<a href="/login" class="text-[var(--accent-primary)] hover:underline">Go to login</a>
		</div>
	</div>
</div>
