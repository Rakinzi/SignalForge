<script lang="ts">
	import { page } from '$app/stores';
	import Icon from '$lib/components/Icon.svelte';
	import { currentUser } from '$lib/stores/auth';

	interface Props {
		mobileMenuOpen?: boolean;
		onClose?: () => void;
	}

	let { mobileMenuOpen = false, onClose }: Props = $props();

	const navItems = [
		{ label: 'Overview', href: '/', icon: 'squares-2x2' },
		{ label: 'Flows', href: '/flows', icon: 'arrows-right-left' },
		{ label: 'Detection', href: '/detection', icon: 'shield-check' },
		{ label: 'Lab', href: '/lab', icon: 'beaker' },
		{ label: 'Alerts', href: '/alerts', icon: 'exclamation-triangle' },
		{ label: 'Entities', href: '/entities', icon: 'cube' },
		{ label: 'Evaluation', href: '/evaluation', icon: 'chart-pie' },
		{ label: 'Reports', href: '/reports', icon: 'chart-bar' },
		{ label: 'Settings', href: '/settings', icon: 'cog-6-tooth' }
	];

	let currentPath = $derived($page.url.pathname);
	let role = $derived($currentUser?.role ?? 'viewer');
	function canView(href: string): boolean {
		if (href === '/settings') return role === 'admin';
		if (href === '/lab') return role === 'admin' || role === 'analyst';
		return true;
	}

	let visibleNavItems = $derived(navItems.filter((item) => canView(item.href)));

	function handleLinkClick() {
		// Close mobile menu when link is clicked
		if (onClose) onClose();
	}
</script>

<!-- Mobile Overlay -->
{#if mobileMenuOpen}
	<button
		onclick={onClose}
		class="fixed inset-0 bg-black/50 z-30 lg:hidden"
		aria-label="Close menu"
	></button>
{/if}

<!-- Sidebar -->
<aside
	class="fixed left-0 top-16 h-[calc(100vh-4rem)] w-64 bg-[var(--bg-secondary)] border-r border-[var(--border-color)] flex flex-col z-40 transition-transform duration-300 ease-in-out
	{mobileMenuOpen
		? 'translate-x-0 visible pointer-events-auto'
		: '-translate-x-full invisible pointer-events-none lg:translate-x-0 lg:visible lg:pointer-events-auto'}"
>
	<!-- Navigation -->
	<nav class="flex-1 overflow-y-auto p-4">
		<ul class="space-y-2">
			{#each visibleNavItems as item (item.href)}
				<li>
					<a
						href={item.href}
						onclick={handleLinkClick}
						class="flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200
						{currentPath === item.href
							? 'bg-[var(--accent-primary)] text-white shadow-lg cyber-glow'
							: 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--text-primary)]'}"
					>
						<Icon
							src={item.icon}
							class="w-5 h-5 {currentPath === item.href ? 'text-white' : ''}"
						/>
						<span class="font-medium">{item.label}</span>
					</a>
				</li>
			{/each}
		</ul>
	</nav>

	<!-- Footer -->
	<div class="p-4 border-t border-[var(--border-color)]">
		<div class="flex items-center justify-between text-xs text-[var(--text-tertiary)]">
			<span>v1.0.0</span>
			<div class="flex items-center space-x-2">
				<div class="w-2 h-2 rounded-full bg-[var(--color-success)] animate-pulse"></div>
				<span>Online</span>
			</div>
		</div>
	</div>
</aside>

<style>
	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.5;
		}
	}

	.animate-pulse {
		animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
	}
</style>
