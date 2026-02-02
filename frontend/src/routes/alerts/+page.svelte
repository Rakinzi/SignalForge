<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { getAlerts, acknowledgeAlert, connectToAlertStream } from '$lib/api/client';
	import type { AlertEvent } from '$lib/types';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import FormSelect from '$lib/components/FormSelect.svelte';
	import { Icon } from 'svelte-hero-icons';

	let alerts = $state<AlertEvent[]>([]);
	let loading = $state(true);
	let sseConnected = $state(false);
	let eventSource: EventSource | null = null;

	// Filters
	let severityFilter = $state('all');
	let statusFilter = $state('all');

	// Pagination
	let currentPage = $state(1);
	let pageSize = $state(25);

	async function loadAlerts() {
		loading = true;
		const params: any = { limit: 500 };
		if (statusFilter !== 'all') params.status = statusFilter;
		alerts = await getAlerts(params);
		loading = false;
	}

	async function handleAcknowledge(alertId: string) {
		const success = await acknowledgeAlert(alertId);
		if (success) {
			alerts = alerts.map((a) =>
				a.alert_id === alertId ? { ...a, status: 'acknowledged' } : a
			);
		}
	}

	async function connectSSE() {
		if (eventSource) eventSource.close();

		eventSource = await connectToAlertStream(
			(newAlert) => {
				alerts = [newAlert, ...alerts];
				sseConnected = true;
			},
			() => {
				sseConnected = false;
			}
		);

		if (eventSource) sseConnected = true;
	}

	function disconnectSSE() {
		if (eventSource) {
			eventSource.close();
			eventSource = null;
			sseConnected = false;
		}
	}

	function clearFilters() {
		severityFilter = 'all';
		statusFilter = 'all';
		loadAlerts();
	}

	function getSeverityColor(severity: string): string {
		const colors: Record<string, string> = {
			critical: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 border-red-200 dark:border-red-800',
			high: 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-200 border-orange-200 dark:border-orange-800',
			medium: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200 border-yellow-200 dark:border-yellow-800',
			low: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 border-blue-200 dark:border-blue-800',
			info: 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border-gray-200 dark:border-gray-700'
		};
		return colors[severity] || colors.info;
	}

	onMount(() => {
		loadAlerts();
		setTimeout(connectSSE, 1000);
	});

	onDestroy(disconnectSSE);

	let filteredAlerts = $derived(
		alerts.filter((a) => {
			const severityMatch = severityFilter === 'all' || a.severity === severityFilter;
			const statusMatch = statusFilter === 'all' || a.status === statusFilter;
			return severityMatch && statusMatch;
		})
	);

	let alertStats = $derived({
		active: alerts.filter((a) => a.status === 'active').length,
		acknowledged: alerts.filter((a) => a.status === 'acknowledged').length,
		resolved: alerts.filter((a) => a.status === 'resolved').length
	});

	// Pagination
	let totalPages = $derived(Math.ceil(filteredAlerts.length / pageSize));
	let paginatedAlerts = $derived(
		filteredAlerts.slice((currentPage - 1) * pageSize, currentPage * pageSize)
	);

	function goToPage(page: number) {
		if (page >= 1 && page <= totalPages) currentPage = page;
	}
</script>

<svelte:head>
	<title>Alerts</title>
</svelte:head>

<!-- Header -->
<div class="flex items-center justify-between mb-6">
	<div>
		<h1 class="text-2xl font-semibold text-[var(--text-primary)]">Security Alerts</h1>
		<p class="text-sm text-[var(--text-secondary)] mt-1">
			Detection alerts with real-time updates
		</p>
	</div>
	<div class="flex items-center gap-3">
		{#if sseConnected}
			<div class="flex items-center gap-2 px-3 py-2 bg-green-50 dark:bg-emerald-950/30 rounded-lg border border-green-200 dark:border-emerald-800/50">
				<div class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
				<span class="text-sm text-green-700 dark:text-emerald-400">Live</span>
			</div>
		{:else}
			<button
				onclick={connectSSE}
				class="px-4 py-2 bg-[var(--bg-secondary)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-lg hover:bg-[var(--bg-tertiary)] text-sm font-medium transition-colors"
			>
				Connect Live
			</button>
		{/if}
		<button
			onclick={loadAlerts}
			disabled={loading}
			class="px-4 py-2 bg-[var(--accent-primary)] text-white rounded-lg hover:opacity-90
			       disabled:opacity-50 text-sm font-medium transition-opacity flex items-center gap-2"
		>
			<Icon src="arrow-path" class="w-4 h-4 {loading ? 'animate-spin' : ''}" />
			Refresh
		</button>
	</div>
</div>

<!-- Stats -->
<div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
	<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-4">
		<p class="text-sm text-[var(--text-secondary)] mb-1">Active</p>
		<p class="text-2xl font-semibold text-red-600 dark:text-red-400">{alertStats.active}</p>
	</div>
	<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-4">
		<p class="text-sm text-[var(--text-secondary)] mb-1">Acknowledged</p>
		<p class="text-2xl font-semibold text-yellow-600 dark:text-yellow-400">{alertStats.acknowledged}</p>
	</div>
	<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-4">
		<p class="text-sm text-[var(--text-secondary)] mb-1">Resolved</p>
		<p class="text-2xl font-semibold text-green-600 dark:text-emerald-400">{alertStats.resolved}</p>
	</div>
</div>

<!-- Filters -->
<div class="mb-6">
	<FilterBar onApply={loadAlerts} onClear={clearFilters}>
		<FormSelect
			label="Severity"
			bind:value={severityFilter}
			options={[
				{ value: 'all', label: 'All Severities' },
				{ value: 'critical', label: 'Critical' },
				{ value: 'high', label: 'High' },
				{ value: 'medium', label: 'Medium' },
				{ value: 'low', label: 'Low' },
				{ value: 'info', label: 'Info' }
			]}
		/>
		<FormSelect
			label="Status"
			bind:value={statusFilter}
			options={[
				{ value: 'all', label: 'All Statuses' },
				{ value: 'active', label: 'Active' },
				{ value: 'acknowledged', label: 'Acknowledged' },
				{ value: 'resolved', label: 'Resolved' }
			]}
		/>
	</FilterBar>
</div>

<!-- Results info -->
<div class="flex items-center justify-between mb-4">
	<p class="text-sm text-[var(--text-secondary)]">
		Showing {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, filteredAlerts.length)} of {filteredAlerts.length}
	</p>
</div>

<!-- Alerts List -->
<div class="space-y-3 mb-6">
	{#if loading && alerts.length === 0}
		<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-12 text-center">
			<div class="flex items-center justify-center gap-2">
				<div class="animate-spin rounded-full h-6 w-6 border-b-2 border-[var(--accent-primary)]"></div>
				<span class="text-sm text-[var(--text-secondary)]">Loading alerts...</span>
			</div>
		</div>
	{:else if paginatedAlerts.length === 0}
		<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-12 text-center">
			<p class="text-sm text-[var(--text-secondary)]">No alerts found</p>
		</div>
	{:else}
		{#each paginatedAlerts as alert}
			<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-4 hover:border-[var(--border-color-hover)] transition-colors">
				<div class="flex items-start justify-between gap-4">
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2 mb-2">
							<span class="px-2 py-1 text-xs font-semibold rounded border {getSeverityColor(alert.severity)}">
								{alert.severity.toUpperCase()}
							</span>
							<span class="text-xs text-[var(--text-tertiary)] font-mono">{alert.alert_id}</span>
						</div>
						<h3 class="text-sm font-medium text-[var(--text-primary)] mb-1">{alert.summary}</h3>
						<p class="text-xs text-[var(--text-secondary)]">
							{alert.timestamp ? new Date(alert.timestamp).toLocaleString() : 'N/A'}
						</p>
					</div>
					<div class="flex items-center gap-2">
						{#if alert.status === 'active'}
							<button
								onclick={() => handleAcknowledge(alert.alert_id)}
								class="px-3 py-1.5 bg-[var(--accent-primary)] text-white rounded text-xs font-medium hover:opacity-90 transition-opacity whitespace-nowrap"
							>
								Acknowledge
							</button>
						{:else if alert.status === 'acknowledged'}
							<span class="px-3 py-1.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200 rounded text-xs font-medium">
								Acknowledged
							</span>
						{:else}
							<span class="px-3 py-1.5 bg-green-100 dark:bg-emerald-950/40 text-green-800 dark:text-emerald-300 rounded text-xs font-medium">
								Resolved
							</span>
						{/if}
					</div>
				</div>
			</div>
		{/each}
	{/if}
</div>

<!-- Pagination -->
{#if filteredAlerts.length > pageSize}
	<div class="flex flex-col sm:flex-row items-center justify-between gap-4">
		<div class="flex items-center gap-2">
			<button
				onclick={() => goToPage(currentPage - 1)}
				disabled={currentPage === 1}
				class="px-3 py-2 rounded-lg border border-[var(--border-color)] text-sm font-medium
				       text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] disabled:opacity-50
				       disabled:cursor-not-allowed transition-colors"
			>
				<Icon src="chevron-left" class="w-4 h-4" />
			</button>

			<span class="text-sm text-[var(--text-secondary)]">
				Page {currentPage} of {totalPages}
			</span>

			<button
				onclick={() => goToPage(currentPage + 1)}
				disabled={currentPage === totalPages}
				class="px-3 py-2 rounded-lg border border-[var(--border-color)] text-sm font-medium
				       text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] disabled:opacity-50
				       disabled:cursor-not-allowed transition-colors"
			>
				<Icon src="chevron-right" class="w-4 h-4" />
			</button>
		</div>

		<div class="flex items-center gap-2">
			<label class="text-sm text-[var(--text-secondary)] hidden sm:inline">Per page:</label>
			<select
				bind:value={pageSize}
				onchange={() => (currentPage = 1)}
				class="px-3 py-2 rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)]
				       text-sm text-[var(--text-primary)] focus:outline-none focus:ring-2
				       focus:ring-[var(--accent-primary)] focus:border-transparent"
			>
				<option value={10}>10</option>
				<option value={25}>25</option>
				<option value={50}>50</option>
				<option value={100}>100</option>
			</select>
		</div>
	</div>
{/if}
