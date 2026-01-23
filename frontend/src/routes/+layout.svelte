<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import Navbar from '$lib/components/Navbar.svelte';

	let { children } = $props();

	let mobileMenuOpen = $state(false);

	function toggleMobileMenu() {
		mobileMenuOpen = !mobileMenuOpen;
	}

	function closeMobileMenu() {
		mobileMenuOpen = false;
	}
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="min-h-screen bg-[var(--bg-primary)]">
	<Navbar onMenuToggle={toggleMobileMenu} />
	<div class="flex pt-16">
		<Sidebar {mobileMenuOpen} onClose={closeMobileMenu} />
		<main class="flex-1 lg:ml-64 p-4 md:p-6 lg:p-8">
			{@render children()}
		</main>
	</div>
</div>
