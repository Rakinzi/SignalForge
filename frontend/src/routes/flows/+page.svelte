<script lang="ts">
	import { onMount } from 'svelte';
	import { getFlows } from '$lib/api/client';
	import type { FlowSummary } from '$lib/types';
	import DataTable from '$lib/components/DataTable.svelte';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import FormInput from '$lib/components/FormInput.svelte';
	import FormSelect from '$lib/components/FormSelect.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let flows = $state<FlowSummary[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Filters
	let srcIp = $state('');
	let dstIp = $state('');
	let protocol = $state('all');

	async function loadFlows() {
		loading = true;
		error = null;
		try {
			const params: any = {};
			if (srcIp) params.src_ip = srcIp;
			if (dstIp) params.dst_ip = dstIp;
			flows = await getFlows(params);
		} catch (err) {
			flows = [];
			error = err instanceof Error ? err.message : 'Failed to load flows';
		} finally {
			loading = false;
		}
	}

	function clearFilters() {
		srcIp = '';
		dstIp = '';
		protocol = 'all';
		loadFlows();
	}

	function formatBytes(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	function formatDuration(ms: number): string {
		if (ms < 1000) return `${ms}ms`;
		return `${(ms / 1000).toFixed(1)}s`;
	}

	onMount(loadFlows);

	let filteredFlows = $derived(
		protocol === 'all'
			? flows
			: flows.filter((f) => f.protocol.toLowerCase() === protocol.toLowerCase())
	);

	const columns = [
		{
			key: 'start_time' as keyof FlowSummary,
			label: 'Time',
			format: (val: string) => new Date(val).toLocaleTimeString()
		},
		{
			key: 'src_ip' as keyof FlowSummary,
			label: 'Source',
			format: (val: string, row: FlowSummary) => `${val}:${row.src_port}`
		},
		{
			key: 'dst_ip' as keyof FlowSummary,
			label: 'Destination',
			format: (val: string, row: FlowSummary) => `${val}:${row.dst_port}`
		},
		{
			key: 'protocol' as keyof FlowSummary,
			label: 'Protocol'
		},
		{
			key: 'packet_count' as keyof FlowSummary,
			label: 'Packets',
			format: (val: number) => val.toLocaleString()
		},
		{
			key: 'byte_count' as keyof FlowSummary,
			label: 'Bytes',
			format: formatBytes
		},
		{
			key: 'duration_ms' as keyof FlowSummary,
			label: 'Duration',
			format: formatDuration
		},
		{
			key: 'packet_rate' as keyof FlowSummary,
			label: 'Rate',
			format: (val: number) => `${val.toFixed(1)} pkt/s`
		}
	];
</script>

<svelte:head>
	<title>Flows</title>
</svelte:head>

<!-- Header -->
<div class="flex items-center justify-between mb-6">
	<div>
		<h1 class="text-2xl font-semibold text-[var(--text-primary)]">Network Flows</h1>
		<p class="text-sm text-[var(--text-secondary)] mt-1">Bidirectional flow summaries</p>
	</div>
	<button
		onclick={loadFlows}
		disabled={loading}
		class="px-4 py-2 bg-[var(--accent-primary)] text-white rounded-lg hover:opacity-90
		       disabled:opacity-50 text-sm font-medium transition-opacity flex items-center gap-2"
	>
		<Icon src="arrow-path" class="w-4 h-4 {loading ? 'animate-spin' : ''}" />
		Refresh
	</button>
</div>

<!-- Filters -->
<div class="mb-6">
	<FilterBar onApply={loadFlows} onClear={clearFilters}>
		<FormInput label="Source IP" bind:value={srcIp} placeholder="192.168.1.1" />
		<FormInput label="Destination IP" bind:value={dstIp} placeholder="10.0.0.1" />
		<FormSelect
			label="Protocol"
			bind:value={protocol}
			options={[
				{ value: 'all', label: 'All Protocols' },
				{ value: 'tcp', label: 'TCP' },
				{ value: 'udp', label: 'UDP' },
				{ value: 'icmp', label: 'ICMP' }
			]}
		/>
	</FilterBar>
</div>

<!-- Table -->
<DataTable data={filteredFlows} {columns} {loading} emptyMessage="No flows found" />

{#if error}
	<div class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
		{error}
	</div>
{/if}
