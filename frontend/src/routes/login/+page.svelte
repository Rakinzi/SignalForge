<script lang="ts">
	import { authStore } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import Icon from '$lib/components/Icon.svelte';

	let username = $state('');
	let password = $state('');
	let showPassword = $state(false);
	let isLoading = $state(false);
	let error = $state<string | null>(null);

	// Redirect if already authenticated
	onMount(() => {
		const unsubscribe = authStore.subscribe((auth) => {
			if (auth.user && !auth.isLoading) {
				goto('/');
			}
		});

		return unsubscribe;
	});

	async function handleLogin(e: Event) {
		e.preventDefault();
		error = null;
		isLoading = true;

		const success = await authStore.login(username, password);

		if (success) {
			goto('/');
		} else {
			// Error is set in the store
			const unsubscribe = authStore.subscribe((auth) => {
				error = auth.error;
			});
			unsubscribe();
		}

		isLoading = false;
	}

	function togglePasswordVisibility() {
		showPassword = !showPassword;
	}
</script>

<svelte:head>
	<title>Login - SignalForge</title>
</svelte:head>

<div class="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
	<div class="w-full max-w-md">
		<!-- Logo/Header -->
		<div class="text-center mb-8">
			<h1 class="text-3xl font-bold text-[var(--accent-primary)] mb-2">SignalForge</h1>
			<p class="text-[var(--text-secondary)]">Network Detection Platform</p>
		</div>

		<!-- Login Card -->
		<div class="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg shadow-lg p-8">
			<h2 class="text-xl font-semibold text-[var(--text-primary)] mb-6">Sign In</h2>

			{#if error}
				<div class="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-md flex items-start gap-2">
					<Icon src="exclamation-circle" class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
					<p class="text-sm text-red-500">{error}</p>
				</div>
			{/if}

			<form onsubmit={handleLogin}>
				<!-- Username -->
				<div class="mb-4">
					<label for="username" class="block text-sm font-medium text-[var(--text-primary)] mb-2">
						Username
					</label>
					<input
						type="text"
						id="username"
						bind:value={username}
						required
						disabled={isLoading}
						class="w-full px-4 py-2 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-md text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
						placeholder="Enter your username"
					/>
				</div>

				<!-- Password -->
				<div class="mb-6">
					<label for="password" class="block text-sm font-medium text-[var(--text-primary)] mb-2">
						Password
					</label>
					<div class="relative">
						<input
							type={showPassword ? 'text' : 'password'}
							id="password"
							bind:value={password}
							required
							disabled={isLoading}
							class="w-full px-4 py-2 pr-10 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-md text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
							placeholder="Enter your password"
						/>
						<button
							type="button"
							onclick={togglePasswordVisibility}
							disabled={isLoading}
							class="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-50 disabled:cursor-not-allowed"
						>
							<Icon src={showPassword ? 'eye-slash' : 'eye'} class="w-5 h-5" />
						</button>
					</div>
				</div>

				<!-- Submit Button -->
				<button
					type="submit"
					disabled={isLoading}
					class="w-full bg-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/90 text-white font-medium py-2.5 px-4 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
				>
					{#if isLoading}
						<Icon src="arrow-path" class="w-5 h-5 animate-spin" />
						<span>Signing in...</span>
					{:else}
						<span>Sign In</span>
					{/if}
				</button>
			</form>

			<!-- Register Link -->
			<div class="mt-6 text-center space-y-2">
				<p class="text-sm text-[var(--text-secondary)]">
					Don't have an account?
					<a
						href="/register"
						class="text-[var(--accent-primary)] hover:underline font-medium"
					>
						Register
					</a>
				</p>
				<p class="text-sm text-[var(--text-secondary)]">
					<a href="/forgot-password" class="text-[var(--accent-primary)] hover:underline font-medium">
						Forgot password?
					</a>
				</p>
			</div>
		</div>

		<!-- Footer -->
		<div class="mt-6 text-center text-xs text-[var(--text-secondary)]">
			<p>SignalForge Detection Platform v0.1.0</p>
		</div>
	</div>
</div>
