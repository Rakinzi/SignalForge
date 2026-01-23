<script lang="ts">
	import { Icon } from 'svelte-hero-icons';
	import { goto } from '$app/navigation';
	import { clearToken } from '$lib/api/auth';

	interface Props {
		onMenuToggle?: () => void;
	}

	let { onMenuToggle }: Props = $props();

	let showDropdown = $state(false);

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
		// Clear auth token
		clearToken();
		// Redirect to home
		goto('/');
	}

	// Close dropdown when clicking outside
	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.profile-dropdown')) {
			closeDropdown();
		}
	}
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
		<!-- Profile Dropdown -->
		<div class="profile-dropdown relative">
			<button
				onclick={toggleDropdown}
				class="flex items-center gap-2 px-2 md:px-3 py-2 rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors"
			>
				<div
					class="w-8 h-8 rounded-full bg-[var(--accent-primary)] flex items-center justify-center text-white text-sm font-semibold"
				>
					U
				</div>
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
