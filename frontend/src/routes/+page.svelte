<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { getMetrics } from '$lib/api/client';
	import type { HealthMetrics } from '$lib/types';
	import MetricCard from '$lib/components/MetricCard.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let metrics = $state<HealthMetrics | null>(null);
	let previousMetrics = $state<HealthMetrics | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let autoRefresh = $state(true);
	let refreshInterval: ReturnType<typeof setInterval> | null = null;

	function formatRate(value: number): string {
		if (value <= 0) return '0.00';
		if (value < 0.01) return '<0.01';
		if (value < 10) return value.toFixed(2);
		return value.toFixed(1);
	}

	function formatByteRate(bytesPerSecond: number): string {
		if (bytesPerSecond < 1024) return `${bytesPerSecond.toFixed(0)} B/s`;
		if (bytesPerSecond < 1024 * 1024) return `${(bytesPerSecond / 1024).toFixed(1)} KB/s`;
		return `${(bytesPerSecond / (1024 * 1024)).toFixed(2)} MB/s`;
	}

	function formatUptime(seconds: number): string {
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		if (hours > 0) return `${hours}h ${minutes}m`;
		return `${minutes}m`;
	}

	function getTrend(current: number, previous: number | undefined): 'up' | 'down' | 'neutral' {
		if (!previous || Math.abs(current - previous) < current * 0.05) return 'neutral';
		return current > previous ? 'up' : 'down';
	}

	async function loadMetrics() {
		try {
			loading = true;
			error = null;
			const newMetrics = await getMetrics();
			previousMetrics = metrics;
			metrics = newMetrics;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load metrics';
		} finally {
			loading = false;
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
		<p class="text-sm text-[var(--text-secondary)] mt-1">
			System metrics and health status (rates use a rolling 60s window)
		</p>
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
		<div class="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border border-blue-500/20 rounded-xl p-6 hover:shadow-lg transition-shadow">
			<div class="flex items-center justify-between mb-2">
				<span class="text-sm font-medium text-[var(--text-secondary)]">Ingest Rate</span>
				{#if getTrend(metrics.ingest_rate, previousMetrics?.ingest_rate) === 'up'}
					<Icon src="arrow-trending-up" class="w-5 h-5 text-green-500" />
				{:else if getTrend(metrics.ingest_rate, previousMetrics?.ingest_rate) === 'down'}
					<Icon src="arrow-trending-down" class="w-5 h-5 text-red-500" />
				{:else}
					<Icon src="minus" class="w-5 h-5 text-gray-400" />
				{/if}
			</div>
			<div class="text-3xl font-bold text-[var(--text-primary)]">{formatByteRate(metrics.ingest_rate)}</div>
			<div class="mt-2 text-xs text-[var(--text-secondary)]">Network traffic</div>
		</div>

		<div class="bg-gradient-to-br from-purple-500/10 to-purple-600/5 border border-purple-500/20 rounded-xl p-6 hover:shadow-lg transition-shadow">
			<div class="flex items-center justify-between mb-2">
				<span class="text-sm font-medium text-[var(--text-secondary)]">Flows/Second</span>
				{#if getTrend(metrics.flows_per_second, previousMetrics?.flows_per_second) === 'up'}
					<Icon src="arrow-trending-up" class="w-5 h-5 text-green-500" />
				{:else if getTrend(metrics.flows_per_second, previousMetrics?.flows_per_second) === 'down'}
					<Icon src="arrow-trending-down" class="w-5 h-5 text-red-500" />
				{:else}
					<Icon src="minus" class="w-5 h-5 text-gray-400" />
				{/if}
			</div>
			<div class="text-3xl font-bold text-[var(--text-primary)]">{formatRate(metrics.flows_per_second)}</div>
			<div class="mt-2 text-xs text-[var(--text-secondary)]">{(metrics.flows_total ?? 0).toLocaleString()} total flows</div>
		</div>

		<div class="bg-gradient-to-br from-cyan-500/10 to-cyan-600/5 border border-cyan-500/20 rounded-xl p-6 hover:shadow-lg transition-shadow">
			<div class="flex items-center justify-between mb-2">
				<span class="text-sm font-medium text-[var(--text-secondary)]">Packets/Second</span>
				{#if getTrend(metrics.packets_per_second ?? 0, previousMetrics?.packets_per_second) === 'up'}
					<Icon src="arrow-trending-up" class="w-5 h-5 text-green-500" />
				{:else if getTrend(metrics.packets_per_second ?? 0, previousMetrics?.packets_per_second) === 'down'}
					<Icon src="arrow-trending-down" class="w-5 h-5 text-red-500" />
				{:else}
					<Icon src="minus" class="w-5 h-5 text-gray-400" />
				{/if}
			</div>
			<div class="text-3xl font-bold text-[var(--text-primary)]">{formatRate(metrics.packets_per_second ?? 0)}</div>
			<div class="mt-2 text-xs text-[var(--text-secondary)]">Packet throughput</div>
		</div>

		<div class="bg-gradient-to-br from-red-500/10 to-red-600/5 border border-red-500/20 rounded-xl p-6 hover:shadow-lg transition-shadow">
			<div class="flex items-center justify-between mb-2">
				<span class="text-sm font-medium text-[var(--text-secondary)]">Open Alerts</span>
				<Icon src="exclamation-triangle" class="w-5 h-5 text-red-500" />
			</div>
			<div class="text-3xl font-bold text-red-600">{metrics.alerts_open ?? metrics.alerts_count}</div>
			<div class="mt-2 text-xs text-[var(--text-secondary)]">{(metrics.alerts_total ?? 0).toLocaleString()} total alerts</div>
		</div>
	</div>

	<!-- System Status Cards -->
	<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
		<div class="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-xl p-6">
			<div class="flex items-center gap-3 mb-4">
				<div class="p-3 bg-green-500/10 rounded-lg">
					<Icon src="check-circle" class="w-6 h-6 text-green-500" />
				</div>
				<div>
					<div class="text-sm text-[var(--text-secondary)]">System Status</div>
					<div class="text-lg font-semibold text-green-500">{metrics.status ?? 'healthy'}</div>
				</div>
			</div>
			<div class="text-xs text-[var(--text-secondary)]">
				Uptime: {formatUptime(metrics.uptime_seconds ?? 0)}
			</div>
		</div>

		<div class="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-xl p-6">
			<div class="flex items-center gap-3 mb-4">
				<div class="p-3 bg-blue-500/10 rounded-lg">
					<Icon src="clock" class="w-6 h-6 text-blue-500" />
				</div>
				<div>
					<div class="text-sm text-[var(--text-secondary)]">Avg Latency</div>
					<div class="text-lg font-semibold text-[var(--text-primary)]">{(metrics.latency_ms ?? 0).toFixed(2)} ms</div>
				</div>
			</div>
			<div class="text-xs text-[var(--text-secondary)]">
				Per-flow processing time
			</div>
		</div>

		<div class="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-xl p-6">
			<div class="flex items-center gap-3 mb-4">
				<div class="p-3 bg-purple-500/10 rounded-lg">
					<Icon src="server" class="w-6 h-6 text-purple-500" />
				</div>
				<div>
					<div class="text-sm text-[var(--text-secondary)]">Detection System</div>
					<div class="text-lg font-semibold text-[var(--text-primary)]">Active</div>
				</div>
			</div>
			<div class="text-xs text-[var(--text-secondary)]">
				Hybrid cascaded detection
			</div>
		</div>
	</div>
{/if}

{#if error}
	<div class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
		{error}
	</div>
{/if}
