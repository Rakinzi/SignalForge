<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import Navbar from '$lib/components/Navbar.svelte';
	import { authStore } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';

	let { children } = $props();

	let mobileMenuOpen = $state(false);
	let isAuthPage = $state(false);
	let isLoading = $state(true);

	function toggleMobileMenu() {
		mobileMenuOpen = !mobileMenuOpen;
	}

	function closeMobileMenu() {
		mobileMenuOpen = false;
	}

	onMount(() => {
		const unsubscribe = page.subscribe(($page) => {
			// Check if current page is an auth page
			const p = $page.url.pathname;
			isAuthPage =
				p === '/login' ||
				p === '/register' ||
				p === '/forgot-password' ||
				p === '/reset-password' ||
				p === '/verify-email';
		});

		const unsubscribeAuth = authStore.subscribe((auth) => {
			isLoading = auth.isLoading;

			// Don't redirect if still loading or already on auth page
			if (auth.isLoading) return;

			const currentPath = window.location.pathname;
			const isOnAuthPage =
				currentPath === '/login' ||
				currentPath === '/register' ||
				currentPath === '/forgot-password' ||
				currentPath === '/reset-password' ||
				currentPath === '/verify-email';

			// Redirect to login if not authenticated and not on auth page
			if (!auth.user && !isOnAuthPage) {
				goto('/login');
			}

			// Redirect to home if authenticated and on auth page
			if (auth.user && isOnAuthPage) {
				goto('/');
			}
		});

		return () => {
			unsubscribe();
			unsubscribeAuth();
		};
	});
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

{#if isLoading}
	<div class="min-h-screen bg-[var(--bg-primary)] flex items-center justify-center">
		<div class="text-[var(--text-secondary)]">Loading...</div>
	</div>
{:else if isAuthPage}
	<!-- Auth pages without navbar/sidebar -->
	<div class="min-h-screen bg-[var(--bg-primary)]">
		{@render children()}
	</div>
{:else}
	<!-- Protected pages with navbar/sidebar -->
	<div class="min-h-screen bg-[var(--bg-primary)]">
		<Navbar onMenuToggle={toggleMobileMenu} />
		<div class="flex pt-16">
			<Sidebar {mobileMenuOpen} onClose={closeMobileMenu} />
			<main class="flex-1 lg:ml-64 p-4 md:p-6 lg:p-8">
				{@render children()}
			</main>
		</div>
	</div>
{/if}
