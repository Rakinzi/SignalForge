<script lang="ts">
	import { onMount } from 'svelte';
	import { getConfig, getVersion } from '$lib/api/client';
	import type { SystemConfig } from '$lib/types';
	import { Icon } from 'svelte-hero-icons';

	let config = $state<SystemConfig | null>(null);
	let version = $state<string>('');
	let loading = $state(true);

	async function loadSettings() {
		loading = true;
		const [configData, versionData] = await Promise.all([getConfig(), getVersion()]);
		config = configData;
		version = versionData.version;
		loading = false;
	}

	onMount(loadSettings);
</script>

<svelte:head>
	<title>Settings</title>
</svelte:head>

<!-- Header -->
<div class="flex items-center justify-between mb-6">
	<div>
		<h1 class="text-2xl font-semibold text-[var(--text-primary)]">System Settings</h1>
		<p class="text-sm text-[var(--text-secondary)] mt-1">Configuration and system information</p>
	</div>
	<button
		onclick={loadSettings}
		disabled={loading}
		class="px-4 py-2 bg-[var(--accent-primary)] text-white rounded-lg hover:opacity-90
		       disabled:opacity-50 text-sm font-medium transition-opacity flex items-center gap-2"
	>
		<Icon src="arrow-path" class="w-4 h-4 {loading ? 'animate-spin' : ''}" />
		Refresh
	</button>
</div>

{#if loading && !config}
	<div
		class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-12 text-center"
	>
		<div class="flex items-center justify-center gap-2">
			<div
				class="animate-spin rounded-full h-6 w-6 border-b-2 border-[var(--accent-primary)]"
			></div>
			<span class="text-sm text-[var(--text-secondary)]">Loading settings...</span>
		</div>
	</div>
{:else if config}
	<!-- System Information -->
	<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-6 mb-6">
		<h2 class="text-lg font-semibold text-[var(--text-primary)] mb-4">System Information</h2>
		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<div class="space-y-3">
				<div class="flex justify-between items-center">
					<span class="text-sm text-[var(--text-secondary)]">Platform Version</span>
					<span class="text-sm font-mono text-[var(--text-primary)]">{version}</span>
				</div>
				<div class="flex justify-between items-center">
					<span class="text-sm text-[var(--text-secondary)]">Rules Version</span>
					<span class="text-sm font-mono text-[var(--text-primary)]">
						{config.rules_version}
					</span>
				</div>
			</div>
			<div class="space-y-3">
				<div class="flex justify-between items-center">
					<span class="text-sm text-[var(--text-secondary)]">Frontend</span>
					<span class="text-sm font-mono text-[var(--text-primary)]">SvelteKit + Vite</span>
				</div>
				<div class="flex justify-between items-center">
					<span class="text-sm text-[var(--text-secondary)]">UI Framework</span>
					<span class="text-sm font-mono text-[var(--text-primary)]">
						Tailwind CSS v4 + Skeleton UI
					</span>
				</div>
			</div>
		</div>
	</div>

	<!-- Detector Configuration -->
	<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-6 mb-6">
		<h2 class="text-lg font-semibold text-[var(--text-primary)] mb-4">
			Detector Configuration
		</h2>

		<!-- Detector Status -->
		<div
			class="flex items-center justify-between p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-color)] mb-4"
		>
			<div>
				<p class="text-sm font-medium text-[var(--text-primary)]">Detector Status</p>
				<p class="text-xs text-[var(--text-secondary)] mt-1">
					Real-time anomaly detection engine
				</p>
			</div>
			<span
				class="px-3 py-1 text-sm font-medium rounded-full
				{config.detector_enabled
					? 'bg-green-100 dark:bg-emerald-950/40 text-green-800 dark:text-emerald-300'
					: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200'}"
			>
				{config.detector_enabled ? 'Enabled' : 'Disabled'}
			</span>
		</div>

		<!-- Configuration Parameters -->
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			<div class="p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-color)]">
				<p class="text-sm text-[var(--text-secondary)] mb-2">Baseline Window</p>
				<p class="text-2xl font-semibold text-[var(--text-primary)]">
					{config.baseline_window_hours}
					<span class="text-sm font-normal text-[var(--text-secondary)]">hours</span>
				</p>
			</div>

			<div class="p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-color)]">
				<p class="text-sm text-[var(--text-secondary)] mb-2">Alert Threshold</p>
				<p class="text-2xl font-semibold text-[var(--text-primary)]">
					{(config.alert_threshold * 100).toFixed(0)}%
				</p>
			</div>

			<div class="p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-color)]">
				<p class="text-sm text-[var(--text-secondary)] mb-2">Capture Interface</p>
				<p class="text-xl font-semibold text-[var(--text-primary)] font-mono">
					{config.capture_interface}
				</p>
			</div>

			<div class="p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-color)]">
				<p class="text-sm text-[var(--text-secondary)] mb-2">Detection Mode</p>
				<p class="text-xl font-semibold text-[var(--text-primary)]">Hybrid</p>
			</div>
		</div>
	</div>

	<!-- Architecture Information -->
	<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-6 mb-6">
		<h2 class="text-lg font-semibold text-[var(--text-primary)] mb-4">System Architecture</h2>
		<div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
			<div
				class="text-center p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-color)]"
			>
				<h3 class="text-sm font-semibold text-[var(--text-primary)] mb-1">Collector</h3>
				<p class="text-xs text-[var(--text-secondary)]">Go + gopacket</p>
			</div>

			<div
				class="text-center p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-color)]"
			>
				<h3 class="text-sm font-semibold text-[var(--text-primary)] mb-1">Detector</h3>
				<p class="text-xs text-[var(--text-secondary)]">Python + uv</p>
			</div>

			<div
				class="text-center p-4 bg-[var(--bg-primary)] rounded-lg border border-[var(--border-color)]"
			>
				<h3 class="text-sm font-semibold text-[var(--text-primary)] mb-1">Dashboard</h3>
				<p class="text-xs text-[var(--text-secondary)]">SvelteKit + Tailwind</p>
			</div>
		</div>

		<!-- Key Features -->
		<div class="pt-4 border-t border-[var(--border-color)]">
			<h3 class="text-sm font-semibold text-[var(--text-primary)] mb-3">Key Features</h3>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
				<div class="flex items-center gap-2">
					<Icon src="check-circle" class="w-4 h-4 text-[var(--color-success)]" />
					<span class="text-[var(--text-secondary)]">Encrypted traffic analysis</span>
				</div>
				<div class="flex items-center gap-2">
					<Icon src="check-circle" class="w-4 h-4 text-[var(--color-success)]" />
					<span class="text-[var(--text-secondary)]">Explainable detection results</span>
				</div>
				<div class="flex items-center gap-2">
					<Icon src="check-circle" class="w-4 h-4 text-[var(--color-success)]" />
					<span class="text-[var(--text-secondary)]">Real-time SSE alerts</span>
				</div>
				<div class="flex items-center gap-2">
					<Icon src="check-circle" class="w-4 h-4 text-[var(--color-success)]" />
					<span class="text-[var(--text-secondary)]">Bidirectional flow aggregation</span>
				</div>
				<div class="flex items-center gap-2">
					<Icon src="check-circle" class="w-4 h-4 text-[var(--color-success)]" />
					<span class="text-[var(--text-secondary)]">Entity behavior baselines</span>
				</div>
				<div class="flex items-center gap-2">
					<Icon src="check-circle" class="w-4 h-4 text-[var(--color-success)]" />
					<span class="text-[var(--text-secondary)]">Docker-based deployment</span>
				</div>
			</div>
		</div>
	</div>

	<!-- Privacy & Security Note -->
	<div
		class="bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800 p-6 mb-6"
	>
		<div class="flex items-start gap-3">
			<Icon src="lock-closed" class="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
			<div>
				<h3 class="text-sm font-semibold text-blue-900 dark:text-blue-200 mb-2">
					Privacy by Design
				</h3>
				<p class="text-sm text-blue-800 dark:text-blue-300">
					SignalForge operates exclusively on network flow metadata extracted from packet
					headers. No payload inspection is performed, ensuring compliance with privacy
					regulations while maintaining effective threat detection capabilities.
				</p>
			</div>
		</div>
	</div>

	<!-- Read-Only Notice -->
	<div
		class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800 p-4"
	>
		<div class="flex items-center gap-2">
			<Icon
				src="exclamation-triangle"
				class="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0"
			/>
			<p class="text-sm text-yellow-800 dark:text-yellow-200">
				Configuration changes must be made in the service configuration files. This page is
				read-only.
			</p>
		</div>
	</div>
{/if}
