<script lang="ts">
	import { authStore } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { Icon } from 'svelte-hero-icons';

	let username = $state('');
	let email = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let role = $state('viewer');
	let showPassword = $state(false);
	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let success = $state(false);

	// Redirect if already authenticated
	onMount(() => {
		const unsubscribe = authStore.subscribe((auth) => {
			if (auth.user && !auth.isLoading) {
				goto('/');
			}
		});

		return unsubscribe;
	});

	async function handleRegister(e: Event) {
		e.preventDefault();
		error = null;

		// Validate passwords match
		if (password !== confirmPassword) {
			error = 'Passwords do not match';
			return;
		}

		// Validate password length
		if (password.length < 6) {
			error = 'Password must be at least 6 characters';
			return;
		}

		isLoading = true;

		const result = await authStore.register(username, email, password, role);

		if (result.success) {
			success = true;
			// Redirect to login after 2 seconds
			setTimeout(() => {
				goto('/login');
			}, 2000);
		} else {
			error = result.error || 'Registration failed';
		}

		isLoading = false;
	}

	function togglePasswordVisibility() {
		showPassword = !showPassword;
	}
</script>

<svelte:head>
	<title>Register - SignalForge</title>
</svelte:head>

<div class="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center p-4">
	<div class="w-full max-w-md">
		<!-- Logo/Header -->
		<div class="text-center mb-8">
			<h1 class="text-3xl font-bold text-[var(--accent-primary)] mb-2">SignalForge</h1>
			<p class="text-[var(--text-secondary)]">Network Detection Platform</p>
		</div>

		<!-- Register Card -->
		<div class="bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-lg shadow-lg p-8">
			<h2 class="text-xl font-semibold text-[var(--text-primary)] mb-6">Create Account</h2>

			{#if success}
				<div class="mb-4 p-3 bg-green-500/10 border border-green-500/30 rounded-md flex items-start gap-2">
					<Icon src="check-circle" class="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
					<div class="text-sm text-green-500">
						<p class="font-medium">Registration successful!</p>
						<p>Redirecting to login...</p>
					</div>
				</div>
			{/if}

			{#if error}
				<div class="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-md flex items-start gap-2">
					<Icon src="exclamation-circle" class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
					<p class="text-sm text-red-500">{error}</p>
				</div>
			{/if}

			{#if !success}
				<form onsubmit={handleRegister}>
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
							minlength="3"
							class="w-full px-4 py-2 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-md text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
							placeholder="Choose a username"
						/>
					</div>

					<!-- Email -->
					<div class="mb-4">
						<label for="email" class="block text-sm font-medium text-[var(--text-primary)] mb-2">
							Email
						</label>
						<input
							type="email"
							id="email"
							bind:value={email}
							required
							disabled={isLoading}
							class="w-full px-4 py-2 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-md text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
							placeholder="your.email@example.com"
						/>
					</div>

					<!-- Role -->
					<div class="mb-4">
						<label for="role" class="block text-sm font-medium text-[var(--text-primary)] mb-2">
							Role
						</label>
						<select
							id="role"
							bind:value={role}
							disabled={isLoading}
							class="w-full px-4 py-2 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-md text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
						>
							<option value="viewer">Viewer (Read-only)</option>
							<option value="analyst">Analyst (Detection & Analysis)</option>
							<option value="admin">Admin (Full Access)</option>
						</select>
					</div>

					<!-- Password -->
					<div class="mb-4">
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
								minlength="6"
								class="w-full px-4 py-2 pr-10 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-md text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
								placeholder="At least 6 characters"
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

					<!-- Confirm Password -->
					<div class="mb-6">
						<label for="confirmPassword" class="block text-sm font-medium text-[var(--text-primary)] mb-2">
							Confirm Password
						</label>
						<input
							type={showPassword ? 'text' : 'password'}
							id="confirmPassword"
							bind:value={confirmPassword}
							required
							disabled={isLoading}
							class="w-full px-4 py-2 bg-[var(--bg-primary)] border border-[var(--border-primary)] rounded-md text-[var(--text-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)] focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
							placeholder="Re-enter your password"
						/>
					</div>

					<!-- Submit Button -->
					<button
						type="submit"
						disabled={isLoading}
						class="w-full bg-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/90 text-white font-medium py-2.5 px-4 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
					>
						{#if isLoading}
							<Icon src="arrow-path" class="w-5 h-5 animate-spin" />
							<span>Creating account...</span>
						{:else}
							<span>Create Account</span>
						{/if}
					</button>
				</form>
			{/if}

			<!-- Login Link -->
			<div class="mt-6 text-center">
				<p class="text-sm text-[var(--text-secondary)]">
					Already have an account?
					<a
						href="/login"
						class="text-[var(--accent-primary)] hover:underline font-medium"
					>
						Sign In
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
