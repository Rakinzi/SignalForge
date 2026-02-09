<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import {
		getAlerts,
		acknowledgeAlert,
		connectToAlertStream,
		normalizeApiError
	} from '$lib/api/client';
	import type { AlertEvent } from '$lib/types';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import FormSelect from '$lib/components/FormSelect.svelte';
	import PageStateLoading from '$lib/components/PageStateLoading.svelte';
	import PageStateEmpty from '$lib/components/PageStateEmpty.svelte';
	import PageStateError from '$lib/components/PageStateError.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let alerts = $state<AlertEvent[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let streamMessage = $state<string | null>(null);
	let eventSource: EventSource | null = null;
	let streamState = $state<'idle' | 'connecting' | 'live' | 'error'>('idle');

	let severityFilter = $state('all');
	let statusFilter = $state('all');

	let currentPage = $state(1);
	let pageSize = $state(25);

	async function loadAlerts() {
		loading = true;
		error = null;
		try {
			const params: { limit: number; status?: string } = { limit: 500 };
			if (statusFilter !== 'all') params.status = statusFilter;
			alerts = await getAlerts(params);
			if (currentPage > Math.max(1, Math.ceil(alerts.length / pageSize))) {
				currentPage = 1;
			}
		} catch (err) {
			alerts = [];
			error = normalizeApiError(err, 'Failed to load alerts').message;
		} finally {
			loading = false;
		}
	}

	async function handleAcknowledge(alertId: string) {
		try {
			error = null;
			const success = await acknowledgeAlert(alertId);
			if (success) {
				alerts = alerts.map((a) =>
					a.alert_id === alertId ? { ...a, status: 'acknowledged' } : a
				);
			}
		} catch (err) {
			error = normalizeApiError(err, 'Failed to acknowledge alert').message;
		}
	}

	async function connectLive() {
		streamState = 'connecting';
		streamMessage = null;

		if (eventSource) {
			eventSource.close();
			eventSource = null;
		}

		eventSource = await connectToAlertStream(
			(newAlert) => {
				alerts = [newAlert, ...alerts];
				streamState = 'live';
				streamMessage = null;
			},
			() => {
				streamState = 'error';
				streamMessage = 'Live stream unavailable. You can continue using manual refresh.';
			},
			() => {
				streamState = 'live';
				streamMessage = null;
			}
		);

		if (!eventSource) {
			streamState = 'error';
			streamMessage = 'Unable to connect to live stream.';
		}
	}

	function disconnectLive() {
		if (eventSource) {
			eventSource.close();
			eventSource = null;
		}
		streamState = 'idle';
		streamMessage = null;
	}

	function clearFilters() {
		severityFilter = 'all';
		statusFilter = 'all';
		currentPage = 1;
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

	onMount(loadAlerts);
	onDestroy(disconnectLive);

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

<div class="space-y-6">
	<div class="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
		<div>
			<h1 class="text-2xl font-semibold text-[var(--text-primary)]">Security Alerts</h1>
			<p class="mt-1 text-sm text-[var(--text-secondary)]">
				Detection alerts with optional live stream updates.
			</p>
		</div>
		<div class="flex flex-wrap items-center gap-2">
			{#if streamState === 'live'}
				<div class="flex items-center gap-2 rounded-xl border border-emerald-300/70 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:border-emerald-700/60 dark:bg-emerald-950/20 dark:text-emerald-300">
					<div class="h-2 w-2 rounded-full bg-emerald-500"></div>
					Live stream connected
				</div>
				<button
					onclick={disconnectLive}
					class="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] px-4 py-2 text-sm font-medium text-[var(--text-primary)] transition hover:bg-[var(--bg-tertiary)]"
				>
					Disconnect
				</button>
			{:else}
				<button
					onclick={connectLive}
					disabled={streamState === 'connecting'}
					class="rounded-xl border border-[var(--border-color)] bg-[var(--bg-secondary)] px-4 py-2 text-sm font-medium text-[var(--text-primary)] transition hover:bg-[var(--bg-tertiary)] disabled:opacity-60"
				>
					{streamState === 'connecting' ? 'Connecting...' : 'Connect Live'}
				</button>
			{/if}
			<button
				onclick={loadAlerts}
				disabled={loading}
				class="rounded-xl bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-60"
			>
				Refresh
			</button>
		</div>
	</div>

	{#if streamMessage}
		<div class="rounded-xl border border-amber-300/60 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-700/60 dark:bg-amber-900/20 dark:text-amber-300">
			{streamMessage}
		</div>
	{/if}

	<div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
		<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-4 shadow-[var(--shadow-soft)]">
			<p class="text-sm text-[var(--text-secondary)]">Active</p>
			<p class="text-2xl font-semibold text-red-600 dark:text-red-400">{alertStats.active}</p>
		</div>
		<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-4 shadow-[var(--shadow-soft)]">
			<p class="text-sm text-[var(--text-secondary)]">Acknowledged</p>
			<p class="text-2xl font-semibold text-yellow-600 dark:text-yellow-300">
				{alertStats.acknowledged}
			</p>
		</div>
		<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-4 shadow-[var(--shadow-soft)]">
			<p class="text-sm text-[var(--text-secondary)]">Resolved</p>
			<p class="text-2xl font-semibold text-emerald-600 dark:text-emerald-400">{alertStats.resolved}</p>
		</div>
	</div>

	<div>
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

	<div class="flex items-center justify-between">
		{#if filteredAlerts.length === 0}
			<p class="text-sm text-[var(--text-secondary)]">Showing 0 of 0</p>
		{:else}
			<p class="text-sm text-[var(--text-secondary)]">
				Showing {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, filteredAlerts.length)} of {filteredAlerts.length}
			</p>
		{/if}
	</div>

	{#if loading && alerts.length === 0}
		<PageStateLoading label="Loading alerts..." />
	{:else if error}
		<PageStateError message={error} onAction={loadAlerts} />
	{:else if paginatedAlerts.length === 0}
		<PageStateEmpty title="No alerts found" message="No alerts match the current filters." icon="inbox" />
	{:else}
		<div class="space-y-3">
			{#each paginatedAlerts as alert}
				<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-4 shadow-[var(--shadow-soft)] transition hover:border-[var(--border-color-hover)]">
					<div class="flex items-start justify-between gap-4">
						<div class="min-w-0 flex-1">
							<div class="mb-2 flex items-center gap-2">
								<span class="rounded border px-2 py-1 text-xs font-semibold {getSeverityColor(alert.severity)}">
									{alert.severity.toUpperCase()}
								</span>
								<span class="font-mono text-xs text-[var(--text-tertiary)]">{alert.alert_id}</span>
							</div>
							<h3 class="text-sm font-medium text-[var(--text-primary)]">{alert.summary}</h3>
							<p class="mt-1 text-xs text-[var(--text-secondary)]">
								{alert.timestamp ? new Date(alert.timestamp).toLocaleString() : 'N/A'}
							</p>
						</div>
						<div>
							{#if alert.status === 'active'}
								<button
									onclick={() => handleAcknowledge(alert.alert_id)}
									class="rounded-lg bg-[var(--accent-primary)] px-3 py-1.5 text-xs font-medium text-white transition hover:opacity-90"
								>
									Acknowledge
								</button>
							{:else if alert.status === 'acknowledged'}
								<span class="rounded bg-yellow-100 px-3 py-1.5 text-xs font-medium text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200">
									Acknowledged
								</span>
							{:else}
								<span class="rounded bg-emerald-100 px-3 py-1.5 text-xs font-medium text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200">
									Resolved
								</span>
							{/if}
						</div>
					</div>
				</div>
			{/each}
		</div>

		{#if totalPages > 1}
			<div class="mt-6 flex flex-col items-center justify-between gap-4 sm:flex-row">
				<div class="text-sm text-[var(--text-secondary)]">Page {currentPage} of {totalPages}</div>
				<div class="flex items-center gap-2">
					<button
						onclick={() => goToPage(currentPage - 1)}
						disabled={currentPage === 1}
						aria-label="Go to previous page"
						class="rounded-lg border border-[var(--border-color)] px-3 py-2 text-sm text-[var(--text-primary)] transition hover:bg-[var(--bg-tertiary)] disabled:cursor-not-allowed disabled:opacity-50"
					>
						<Icon src="chevron-left" class="h-4 w-4" />
					</button>
					<button
						onclick={() => goToPage(currentPage + 1)}
						disabled={currentPage === totalPages}
						aria-label="Go to next page"
						class="rounded-lg border border-[var(--border-color)] px-3 py-2 text-sm text-[var(--text-primary)] transition hover:bg-[var(--bg-tertiary)] disabled:cursor-not-allowed disabled:opacity-50"
					>
						<Icon src="chevron-right" class="h-4 w-4" />
					</button>
				</div>
				<div class="flex items-center gap-2">
					<label for="page-size" class="text-sm text-[var(--text-secondary)]">Per page:</label>
					<select
						id="page-size"
						bind:value={pageSize}
						onchange={() => (currentPage = 1)}
						class="rounded-lg border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-transparent focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]"
					>
						<option value={10}>10</option>
						<option value={25}>25</option>
						<option value={50}>50</option>
						<option value={100}>100</option>
					</select>
				</div>
			</div>
		{/if}
	{/if}
</div>
