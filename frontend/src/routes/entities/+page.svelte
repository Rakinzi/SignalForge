<script lang="ts">
	import { onMount } from 'svelte';
	import { getEntities } from '$lib/api/client';
	import type { EntityBaseline } from '$lib/types';
	import DataTable from '$lib/components/DataTable.svelte';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import FormInput from '$lib/components/FormInput.svelte';
	import FormSelect from '$lib/components/FormSelect.svelte';
	import { Icon } from 'svelte-hero-icons';

	let entities = $state<EntityBaseline[]>([]);
	let loading = $state(true);

	// Filters
	let typeFilter = $state('all');
	let searchQuery = $state('');

	async function loadEntities() {
		loading = true;
		entities = await getEntities();
		loading = false;
	}

	function clearFilters() {
		typeFilter = 'all';
		searchQuery = '';
	}

	function formatBytes(bytes: number): string {
		if (bytes < 1024) return `${bytes} B/s`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB/s`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB/s`;
	}

	function formatTime(isoString: string): string {
		return new Date(isoString).toLocaleString();
	}

	onMount(loadEntities);

	let filteredEntities = $derived(
		entities.filter((e) => {
			const typeMatch = typeFilter === 'all' || e.entity_type === typeFilter;
			const searchMatch =
				searchQuery === '' || e.entity_id.toLowerCase().includes(searchQuery.toLowerCase());
			return typeMatch && searchMatch;
		})
	);

	let entityStats = $derived({
		total: entities.length,
		ip: entities.filter((e) => e.entity_type === 'ip').length,
		service: entities.filter((e) => e.entity_type === 'service').length,
		host: entities.filter((e) => e.entity_type === 'host').length
	});

	const columns = [
		{
			key: 'entity_id' as keyof EntityBaseline,
			label: 'Entity ID'
		},
		{
			key: 'entity_type' as keyof EntityBaseline,
			label: 'Type',
			format: (val: string) => val.charAt(0).toUpperCase() + val.slice(1)
		},
		{
			key: 'avg_packet_rate' as keyof EntityBaseline,
			label: 'Packet Rate',
			format: (val: number) => `${val.toFixed(2)} pkt/s`
		},
		{
			key: 'avg_byte_rate' as keyof EntityBaseline,
			label: 'Byte Rate',
			format: formatBytes
		},
		{
			key: 'connection_count' as keyof EntityBaseline,
			label: 'Connections',
			format: (val: number) => val.toLocaleString()
		},
		{
			key: 'baseline_confidence' as keyof EntityBaseline,
			label: 'Confidence',
			format: (val: number) => `${(val * 100).toFixed(0)}%`
		},
		{
			key: 'last_seen' as keyof EntityBaseline,
			label: 'Last Seen',
			format: formatTime
		}
	];
</script>

<svelte:head>
	<title>Entities</title>
</svelte:head>

<!-- Header -->
<div class="flex items-center justify-between mb-6">
	<div>
		<h1 class="text-2xl font-semibold text-[var(--text-primary)]">Network Entities</h1>
		<p class="text-sm text-[var(--text-secondary)] mt-1">Baseline behavior profiles</p>
	</div>
	<button
		onclick={loadEntities}
		disabled={loading}
		class="px-4 py-2 bg-[var(--accent-primary)] text-white rounded-lg hover:opacity-90
		       disabled:opacity-50 text-sm font-medium transition-opacity flex items-center gap-2"
	>
		<Icon src="arrow-path" class="w-4 h-4 {loading ? 'animate-spin' : ''}" />
		Refresh
	</button>
</div>

<!-- Stats -->
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
	<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-4">
		<p class="text-sm text-[var(--text-secondary)] mb-1">Total</p>
		<p class="text-2xl font-semibold text-[var(--text-primary)]">{entityStats.total}</p>
	</div>
	<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-4">
		<p class="text-sm text-[var(--text-secondary)] mb-1">IP Addresses</p>
		<p class="text-2xl font-semibold text-blue-600 dark:text-blue-400">{entityStats.ip}</p>
	</div>
	<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-4">
		<p class="text-sm text-[var(--text-secondary)] mb-1">Services</p>
		<p class="text-2xl font-semibold text-purple-600 dark:text-purple-400">{entityStats.service}</p>
	</div>
	<div class="bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)] p-4">
		<p class="text-sm text-[var(--text-secondary)] mb-1">Hosts</p>
		<p class="text-2xl font-semibold text-green-600 dark:text-green-400">{entityStats.host}</p>
	</div>
</div>

<!-- Filters -->
<div class="mb-6">
	<FilterBar onApply={loadEntities} onClear={clearFilters}>
		<FormInput label="Search" bind:value={searchQuery} placeholder="Entity ID..." />
		<FormSelect
			label="Type"
			bind:value={typeFilter}
			options={[
				{ value: 'all', label: 'All Types' },
				{ value: 'ip', label: 'IP Addresses' },
				{ value: 'service', label: 'Services' },
				{ value: 'host', label: 'Hosts' }
			]}
		/>
	</FilterBar>
</div>

<!-- Table -->
<DataTable data={filteredEntities} {columns} {loading} emptyMessage="No entities found" />
