<script lang="ts">
import Icon from '$lib/components/Icon.svelte';
import { goto } from '$app/navigation';
import { onMount } from 'svelte';
import { authStore, currentUser } from '$lib/stores/auth';

	interface Props {
		onMenuToggle?: () => void;
	}

	let { onMenuToggle }: Props = $props();

	// Get current user from auth store
	let user = $derived($currentUser);

	let showDropdown = $state(false);
	let theme = $state<'light' | 'dark'>('light');

	function applyTheme(next: 'light' | 'dark') {
		theme = next;
		document.documentElement.setAttribute('data-theme', theme);
		localStorage.setItem('theme', theme);
	}

	function toggleTheme() {
		applyTheme(theme === 'dark' ? 'light' : 'dark');
	}

	function toggleDropdown() {
		showDropdown = !showDropdown;
	}

	function closeDropdown() {
		showDropdown = false;
	}

	function handleProfile() {
		closeDropdown();
		// Navigate to profile page if needed
	}

	function handleSettings() {
		closeDropdown();
		goto('/settings');
	}

	function handleLogout() {
		closeDropdown();
		// Use auth store logout (handles token clearing and redirect)
		authStore.logout();
	}

	// Close dropdown when clicking outside
	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.profile-dropdown')) {
			closeDropdown();
		}
	}

	onMount(() => {
		const saved = localStorage.getItem('theme');
		if (saved === 'light' || saved === 'dark') {
			applyTheme(saved);
			return;
		}
		const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
		applyTheme(prefersDark ? 'dark' : 'light');
	});
</script>

<svelte:window onclick={handleClickOutside} />

<nav
	class="fixed top-0 left-0 right-0 bg-[var(--bg-secondary)] border-b border-[var(--border-color)] h-16 flex items-center px-4 md:px-6 z-40"
>
	<!-- Mobile Menu Toggle -->
	<button
		onclick={onMenuToggle}
		class="lg:hidden mr-3 p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors"
		aria-label="Toggle menu"
	>
		<Icon src="bars-3" class="w-6 h-6 text-[var(--text-primary)]" />
	</button>

	<div class="flex-1">
		<h1 class="text-lg md:text-xl font-bold text-[var(--text-primary)]">SignalForge</h1>
	</div>

	<div class="flex items-center gap-2 md:gap-4">
		<button
			onclick={toggleTheme}
			class="p-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors"
			aria-label="Toggle dark mode"
			title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
		>
			<Icon src={theme === 'dark' ? 'sun' : 'moon'} class="w-5 h-5 text-[var(--text-primary)]" />
		</button>
		<!-- Profile Dropdown -->
		<div class="profile-dropdown relative">
			<button
				onclick={toggleDropdown}
				class="flex items-center gap-2 px-2 md:px-3 py-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors"
			>
				<div
					class="w-8 h-8 rounded-full bg-[var(--accent-primary)] flex items-center justify-center text-white text-sm font-semibold"
				>
					{user?.username?.[0]?.toUpperCase() || 'U'}
				</div>
				{#if user}
					<div class="hidden md:block text-left">
						<div class="text-sm font-medium text-[var(--text-primary)]">{user.username}</div>
						<div class="text-xs text-[var(--text-secondary)] capitalize">{user.role}</div>
					</div>
				{/if}
				<Icon src="chevron-down" class="w-4 h-4 text-[var(--text-secondary)] hidden sm:block" />
			</button>

			{#if showDropdown}
				<div
					class="absolute right-0 mt-2 w-48 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg shadow-lg py-1 z-50"
				>
					<button
						onclick={handleProfile}
						class="w-full flex items-center gap-3 px-4 py-2 text-sm text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors text-left"
					>
						<Icon src="user" class="w-4 h-4" />
						<span>Profile</span>
					</button>
					<button
						onclick={handleSettings}
						class="w-full flex items-center gap-3 px-4 py-2 text-sm text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors text-left"
					>
						<Icon src="cog-6-tooth" class="w-4 h-4" />
						<span>Settings</span>
					</button>
					<div class="border-t border-[var(--border-color)] my-1"></div>
					<button
						onclick={handleLogout}
						class="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-[var(--bg-tertiary)] transition-colors text-left"
					>
						<Icon src="arrow-right-on-rectangle" class="w-4 h-4" />
						<span>Log out</span>
					</button>
				</div>
			{/if}
		</div>
	</div>
</nav>
