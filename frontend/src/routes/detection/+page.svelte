<script lang="ts">
	import { Icon } from 'svelte-hero-icons';
	import MetricCard from '$lib/components/MetricCard.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import { onMount } from 'svelte';

	interface Detection {
		flow_id: string;
		threat_level: string;
		confidence: number;
		explanation: string;
		deterministic: {
			classification: string;
			triggered_rules: Array<{ id: string; name: string; severity: string; category: string }>;
		};
		statistical: {
			anomaly_score: number;
			anomalous_features: string[];
		};
		requires_investigation: boolean;
	}

	let detections = $state<Detection[]>([]);
	let isLoading = $state(true);
	let currentPage = $state(1);
	let totalDetections = $state(0);

	// Stats
	let stats = $derived({
		critical: detections.filter((d) => d.threat_level === 'critical').length,
		high: detections.filter((d) => d.threat_level === 'high').length,
		medium: detections.filter((d) => d.threat_level === 'medium').length,
		benign: detections.filter((d) => d.threat_level === 'benign').length,
		needsInvestigation: detections.filter((d) => d.requires_investigation).length
	});

	// Table columns
	const columns = [
		{ key: 'flow_id', label: 'Flow ID', sortable: true },
		{
			key: 'threat_level',
			label: 'Threat Level',
			sortable: true,
			formatter: (value: string) => {
				const colors = {
					critical: 'text-[var(--color-critical)]',
					high: 'text-[var(--color-high)]',
					medium: 'text-[var(--color-medium)]',
					low: 'text-[var(--color-low)]',
					benign: 'text-[var(--color-success)]'
				};
				return `<span class="font-semibold ${colors[value] || ''}">${value.toUpperCase()}</span>`;
			}
		},
		{
			key: 'confidence',
			label: 'Confidence',
			sortable: true,
			formatter: (value: number) => `${(value * 100).toFixed(1)}%`
		},
		{
			key: 'deterministic',
			label: 'Rules Triggered',
			formatter: (value: Detection['deterministic']) => value.triggered_rules.length.toString()
		},
		{
			key: 'statistical',
			label: 'Anomaly Score',
			formatter: (value: Detection['statistical']) => (value.anomaly_score * 100).toFixed(1) + '%'
		},
		{
			key: 'requires_investigation',
			label: 'Investigation',
			formatter: (value: boolean) =>
				value
					? '<span class="text-[var(--color-medium)]">Required</span>'
					: '<span class="text-[var(--text-secondary)]">No</span>'
		}
	];

	async function loadDetections() {
		isLoading = true;
		try {
			const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
			const response = await fetch(`${apiUrl}/detections?limit=50`);

			if (response.ok) {
				const data = await response.json();
				detections = data.items || [];
				totalDetections = data.total || detections.length;
			}
		} catch (error) {
			console.error('Failed to load detections:', error);
		} finally {
			isLoading = false;
		}
	}

	function getThreatColor(level: string): string {
		const colors = {
			critical: 'var(--color-critical)',
			high: 'var(--color-high)',
			medium: 'var(--color-medium)',
			low: 'var(--color-low)',
			benign: 'var(--color-success)'
		};
		return colors[level] || 'var(--text-secondary)';
	}

	onMount(() => {
		loadDetections();
		// Auto-refresh every 30 seconds
		const interval = setInterval(loadDetections, 30000);
		return () => clearInterval(interval);
	});
</script>

<svelte:head>
	<title>Detection Dashboard - SignalForge</title>
</svelte:head>

<div class="space-y-6">
	<!-- Header -->
	<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
		<div>
			<h1 class="text-2xl font-bold text-[var(--text-primary)]">Detection Dashboard</h1>
			<p class="text-sm text-[var(--text-secondary)] mt-1">
				Hybrid malware detection results (deterministic + statistical)
			</p>
		</div>
		<button
			onclick={loadDetections}
			class="self-start sm:self-auto px-4 py-2 bg-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/90 text-white rounded-lg transition-colors flex items-center gap-2"
		>
			<Icon src="arrow-path" class="w-4 h-4" />
			<span>Refresh</span>
		</button>
	</div>

	<!-- Stats Cards -->
	<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
		<MetricCard
			label="Critical"
			value={stats.critical}
			icon="shield-exclamation"
			trend="neutral"
			color={getThreatColor('critical')}
		/>
		<MetricCard
			label="High"
			value={stats.high}
			icon="exclamation-triangle"
			trend="neutral"
			color={getThreatColor('high')}
		/>
		<MetricCard
			label="Medium"
			value={stats.medium}
			icon="exclamation-circle"
			trend="neutral"
			color={getThreatColor('medium')}
		/>
		<MetricCard
			label="Benign"
			value={stats.benign}
			icon="check-circle"
			trend="neutral"
			color={getThreatColor('benign')}
		/>
		<MetricCard
			label="Needs Investigation"
			value={stats.needsInvestigation}
			icon="magnifying-glass"
			trend="neutral"
			color="var(--color-medium)"
		/>
	</div>

	<!-- Detection Table -->
	<div class="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-6">
		<div class="mb-4">
			<h2 class="text-lg font-semibold text-[var(--text-primary)]">Recent Detections</h2>
			<p class="text-sm text-[var(--text-secondary)] mt-1">
				Showing detections from the hybrid detection pipeline
			</p>
		</div>

		{#if isLoading}
			<div class="flex items-center justify-center py-12">
				<Icon src="arrow-path" class="w-8 h-8 text-[var(--accent-primary)] animate-spin" />
			</div>
		{:else if detections.length === 0}
			<div class="text-center py-12">
				<Icon src="inbox" class="w-12 h-12 text-[var(--text-secondary)] mx-auto mb-3" />
				<p class="text-[var(--text-secondary)]">No detections found</p>
				<p class="text-sm text-[var(--text-secondary)] mt-1">
					Start analyzing traffic to see detection results
				</p>
			</div>
		{:else}
			<DataTable
				data={detections}
				{columns}
				bind:currentPage
				rowsPerPage={10}
				totalRows={totalDetections}
				onRowClick={(detection) => console.log('View details:', detection)}
			/>
		{/if}
	</div>

	<!-- Detection Explanation (if selected) -->
	<!-- This would show detailed explanation when a row is clicked -->
</div>
