<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { getMetrics } from '$lib/api/client';
	import type { HealthMetrics } from '$lib/types';
	import MetricCard from '$lib/components/MetricCard.svelte';
	import { Icon } from 'svelte-hero-icons';

	let metrics = $state<HealthMetrics | null>(null);
	let loading = $state(true);
	let autoRefresh = $state(true);
	let refreshInterval: ReturnType<typeof setInterval> | null = null;

	async function loadMetrics() {
		try {
			loading = true;
			metrics = await getMetrics();
		} finally {
			loading = false;
		}
	}

	function formatUptime(seconds: number): string {
		const days = Math.floor(seconds / 86400);
		const hours = Math.floor((seconds % 86400) / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		return `${days}d ${hours}h ${minutes}m`;
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'healthy':
				return 'var(--color-success)';
			case 'degraded':
				return 'var(--color-medium)';
			case 'unhealthy':
				return 'var(--color-critical)';
			default:
				return 'var(--text-tertiary)';
		}
	}

	onMount(() => {
		loadMetrics();
	});

	onDestroy(() => {
		if (refreshInterval) {
			clearInterval(refreshInterval);
		}
	});

	$effect(() => {
		// Clear existing interval
		if (refreshInterval) {
			clearInterval(refreshInterval);
			refreshInterval = null;
		}

		// Start new interval if autoRefresh is enabled
		if (autoRefresh) {
			refreshInterval = setInterval(loadMetrics, 5000);
		}

		// Cleanup function
		return () => {
			if (refreshInterval) {
				clearInterval(refreshInterval);
			}
		};
	});
</script>

<svelte:head>
	<title>Overview</title>
</svelte:head>

<!-- Header -->
<div class="flex items-center justify-between mb-6">
	<div>
		<h1 class="text-2xl font-semibold text-[var(--text-primary)]">Overview</h1>
		<p class="text-sm text-[var(--text-secondary)] mt-1">System metrics and health status</p>
	</div>
	<button
		onclick={loadMetrics}
		disabled={loading}
		class="px-4 py-2 bg-[var(--accent-primary)] text-white rounded-lg hover:opacity-90
		       disabled:opacity-50 text-sm font-medium transition-opacity flex items-center gap-2"
	>
		<Icon src="arrow-path" class="w-4 h-4 {loading ? 'animate-spin' : ''}" />
		Refresh
	</button>
</div>

{#if metrics}
	<!-- Metrics Grid -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
		<MetricCard
			label="Ingest Rate"
			value={metrics.ingest_rate.toFixed(2)}
			unit="MB/s"
		/>
		<MetricCard
			label="Flows/Second"
			value={metrics.flows_per_second.toFixed(0)}
			unit="flows"
		/>
		<MetricCard
			label="Active Alerts"
			value={metrics.alerts_count}
		/>
		<MetricCard
			label="Latency"
			value={metrics.latency_ms.toFixed(1)}
			unit="ms"
		/>
	</div>
{/if}

