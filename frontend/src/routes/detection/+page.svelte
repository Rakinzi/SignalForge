<script lang="ts">
	import Icon from '$lib/components/Icon.svelte';
	import MetricCard from '$lib/components/MetricCard.svelte';
	import DataTable from '$lib/components/DataTable.svelte';
	import PageStateLoading from '$lib/components/PageStateLoading.svelte';
	import PageStateEmpty from '$lib/components/PageStateEmpty.svelte';
	import PageStateForbidden from '$lib/components/PageStateForbidden.svelte';
	import PageStateError from '$lib/components/PageStateError.svelte';
	import { onMount } from 'svelte';
	import { getDetections, normalizeApiError } from '$lib/api/client';

	interface Detection {
		flow_id: string;
		created_at: string;
		rules_triggered: string[];
		anomaly_score: number;
		explanation: string;
	}

	interface DetectionRow {
		confidence: number;
		threat_level: 'critical' | 'high' | 'medium' | 'low' | 'benign';
		requires_investigation: boolean;
		flow_id: string;
		rules_triggered: string;
		created_at: string;
		explanation: string;
	}

	type ThreatLevel = DetectionRow['threat_level'];

	let detections = $state<DetectionRow[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let isForbidden = $state(false);

	let stats = $derived({
		critical: detections.filter((d) => d.threat_level === 'critical').length,
		high: detections.filter((d) => d.threat_level === 'high').length,
		medium: detections.filter((d) => d.threat_level === 'medium').length,
		low: detections.filter((d) => d.threat_level === 'low').length,
		benign: detections.filter((d) => d.threat_level === 'benign').length,
		needsInvestigation: detections.filter((d) => d.requires_investigation).length
	});

	const columns: Array<{
		key: keyof DetectionRow;
		label: string;
		format?: (value: unknown) => string;
	}> = [
		{ key: 'flow_id', label: 'Flow ID' },
		{
			key: 'threat_level',
			label: 'Threat Level',
			format: (value: unknown) => String(value).toUpperCase()
		},
		{
			key: 'confidence',
			label: 'Confidence',
			format: (value: unknown) => `${(Number(value) * 100).toFixed(1)}%`
		},
		{ key: 'rules_triggered', label: 'Rules Triggered' },
		{
			key: 'created_at',
			label: 'Detected At',
			format: (value: unknown) => new Date(String(value)).toLocaleString()
		},
		{
			key: 'explanation',
			label: 'Explanation',
			format: (value: unknown) => {
				const text = String(value);
				return text.length > 96 ? `${text.slice(0, 96)}...` : text;
			}
		},
		{
			key: 'requires_investigation',
			label: 'Investigation',
			format: (value: unknown) => (Boolean(value) ? 'Required' : 'No')
		}
	];

	function threatLevelFromScore(score: number): ThreatLevel {
		if (score >= 0.9) return 'critical';
		if (score >= 0.75) return 'high';
		if (score >= 0.55) return 'medium';
		if (score >= 0.35) return 'low';
		return 'benign';
	}

	function parseRules(value: unknown): string[] {
		if (Array.isArray(value)) return value.map((v) => String(v));
		if (typeof value !== 'string' || value.trim() === '') return [];
		try {
			const parsed = JSON.parse(value);
			return Array.isArray(parsed) ? parsed.map((v) => String(v)) : [];
		} catch {
			return [];
		}
	}

	function mapDetection(row: Detection): DetectionRow {
		const score = Number(row.anomaly_score ?? 0);
		const level = threatLevelFromScore(score);
		const rules = parseRules(row.rules_triggered);

		return {
			flow_id: row.flow_id,
			created_at: row.created_at,
			confidence: score,
			threat_level: level,
			requires_investigation: score >= 0.75,
			rules_triggered: rules.length > 0 ? rules.join(', ') : 'none',
			explanation: row.explanation
		};
	}

	async function loadDetections() {
		isLoading = true;
		error = null;
		isForbidden = false;
		try {
			const rows = (await getDetections({ limit: 50 })) as Detection[];
			detections = rows.map(mapDetection);
		} catch (err) {
			detections = [];
			const normalized = normalizeApiError(err, 'Failed to load detections');
			if (normalized.kind === 'forbidden') {
				isForbidden = true;
			} else {
				error = normalized.message;
			}
		} finally {
			isLoading = false;
		}
	}

	function getThreatColor(level: ThreatLevel): string {
		const colors: Record<ThreatLevel, string> = {
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
		const interval = setInterval(loadDetections, 30000);
		return () => clearInterval(interval);
	});
</script>

<svelte:head>
	<title>Detection Dashboard - SignalForge</title>
</svelte:head>

<div class="space-y-6">
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-2xl font-bold text-[var(--text-primary)]">Detection Dashboard</h1>
			<p class="mt-1 text-sm text-[var(--text-secondary)]">
				Hybrid malware detection results (deterministic + statistical)
			</p>
		</div>
		<button
			onclick={loadDetections}
			class="self-start rounded-xl bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 sm:self-auto"
		>
			Refresh
		</button>
	</div>

	{#if isLoading}
		<PageStateLoading label="Loading detections..." />
	{:else if isForbidden}
		<PageStateForbidden
			title="Detection data requires elevated access"
			message="Your current role can access high-level monitoring views, but not raw detection output."
			requiredRole="analyst or admin"
		/>
	{:else if error}
		<PageStateError message={error} onAction={loadDetections} />
	{:else if detections.length === 0}
		<PageStateEmpty
			title="No detections available"
			message="Start traffic analysis to populate this table."
			icon="shield-check"
		/>
	{:else}
		<div class="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-5">
			<MetricCard
				label="Critical"
				value={stats.critical}
				icon="shield-exclamation"
				color={getThreatColor('critical')}
			/>
			<MetricCard
				label="High"
				value={stats.high}
				icon="exclamation-triangle"
				color={getThreatColor('high')}
			/>
			<MetricCard
				label="Medium"
				value={stats.medium}
				icon="exclamation-circle"
				color={getThreatColor('medium')}
			/>
			<MetricCard
				label="Benign"
				value={stats.benign}
				icon="check-circle"
				color={getThreatColor('benign')}
			/>
			<MetricCard
				label="Needs Investigation"
				value={stats.needsInvestigation}
				icon="magnifying-glass"
				color="var(--color-medium)"
			/>
		</div>

		<div class="rounded-2xl border border-[var(--border-color)] bg-[var(--panel)] p-6 shadow-[var(--shadow-soft)]">
			<h2 class="text-lg font-semibold text-[var(--text-primary)]">Recent Detections</h2>
			<p class="mt-1 text-sm text-[var(--text-secondary)]">
				Showing detections from the hybrid pipeline.
			</p>
			<div class="mt-4">
				<DataTable data={detections} {columns} />
			</div>
		</div>
	{/if}
</div>
