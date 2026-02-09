<script lang="ts">
	import MetricCard from '$lib/components/MetricCard.svelte';
	import PageStateLoading from '$lib/components/PageStateLoading.svelte';
	import PageStateEmpty from '$lib/components/PageStateEmpty.svelte';
	import PageStateForbidden from '$lib/components/PageStateForbidden.svelte';
	import PageStateError from '$lib/components/PageStateError.svelte';
	import { onMount } from 'svelte';
	import { getReports, normalizeApiError } from '$lib/api/client';

	interface EvaluationData {
		confusion_matrix: {
			true_positives: number;
			false_positives: number;
			true_negatives: number;
			false_negatives: number;
		};
		metrics: {
			precision: number;
			recall: number;
			f1_score: number;
			accuracy: number;
			false_positive_rate: number;
			false_negative_rate: number;
		};
		total_flows: number;
	}

	let evaluation = $state<EvaluationData | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let isForbidden = $state(false);

	async function loadEvaluation() {
		isLoading = true;
		error = null;
		isForbidden = false;
		try {
			const report = await getReports();
			if (!report) {
				evaluation = null;
				return;
			}

			evaluation = {
				confusion_matrix: {
					true_positives: report.true_positives,
					false_positives: report.false_positives,
					true_negatives: report.true_negatives,
					false_negatives: report.false_negatives
				},
				metrics: {
					precision: report.precision,
					recall: report.recall,
					f1_score: report.f1_score,
					accuracy: report.accuracy,
					false_positive_rate:
						report.false_positives /
						Math.max(report.false_positives + report.true_negatives, 1),
					false_negative_rate:
						report.false_negatives /
						Math.max(report.false_negatives + report.true_positives, 1)
				},
				total_flows:
					report.true_positives +
					report.false_positives +
					report.true_negatives +
					report.false_negatives
			};
		} catch (err) {
			evaluation = null;
			const normalized = normalizeApiError(err, 'Failed to load evaluation metrics');
			if (normalized.kind === 'forbidden') {
				isForbidden = true;
			} else {
				error = normalized.message;
			}
		} finally {
			isLoading = false;
		}
	}

	onMount(loadEvaluation);
</script>

<svelte:head>
	<title>Evaluation Metrics - SignalForge</title>
</svelte:head>

<div class="space-y-6">
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-2xl font-bold text-[var(--text-primary)]">Evaluation Metrics</h1>
			<p class="mt-1 text-sm text-[var(--text-secondary)]">
				Detection accuracy and classification quality summary.
			</p>
		</div>
		<button
			onclick={loadEvaluation}
			class="self-start rounded-xl bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 sm:self-auto"
		>
			Refresh
		</button>
	</div>

	{#if isLoading}
		<PageStateLoading label="Loading evaluation metrics..." />
	{:else if isForbidden}
		<PageStateForbidden
			title="Evaluation metrics require elevated access"
			message="Your role can monitor operations, but full model-evaluation data is restricted."
			requiredRole="analyst or admin"
		/>
	{:else if error}
		<PageStateError message={error} onAction={loadEvaluation} />
	{:else if !evaluation}
		<PageStateEmpty
			title="No evaluation data available"
			message="Run labeled detection analysis to generate quality metrics."
			icon="chart-bar"
		/>
	{:else}
		<div class="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
			<MetricCard
				label="Precision"
				value={(evaluation.metrics.precision * 100).toFixed(1) + '%'}
				icon="check-circle"
				color="var(--color-success)"
			/>
			<MetricCard
				label="Recall"
				value={(evaluation.metrics.recall * 100).toFixed(1) + '%'}
				icon="shield-check"
				color="var(--accent-primary)"
			/>
			<MetricCard
				label="F1 Score"
				value={(evaluation.metrics.f1_score * 100).toFixed(1) + '%'}
				icon="chart-bar"
				color="var(--accent-primary)"
			/>
			<MetricCard
				label="Accuracy"
				value={(evaluation.metrics.accuracy * 100).toFixed(1) + '%'}
				icon="check-badge"
				color="var(--color-success)"
			/>
			<MetricCard
				label="FPR"
				value={(evaluation.metrics.false_positive_rate * 100).toFixed(1) + '%'}
				icon="x-circle"
				color="var(--color-medium)"
			/>
			<MetricCard
				label="FNR"
				value={(evaluation.metrics.false_negative_rate * 100).toFixed(1) + '%'}
				icon="exclamation-circle"
				color="var(--color-high)"
			/>
		</div>

		<div class="rounded-2xl border border-[var(--border-color)] bg-[var(--panel)] p-6 shadow-[var(--shadow-soft)]">
			<h2 class="mb-4 text-lg font-semibold text-[var(--text-primary)]">Confusion Matrix</h2>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				<div class="rounded-xl border border-emerald-400/40 bg-emerald-50/60 p-4 dark:bg-emerald-900/10">
					<p class="text-sm text-[var(--text-secondary)]">True Positives</p>
					<p class="text-3xl font-semibold text-emerald-700 dark:text-emerald-300">
						{evaluation.confusion_matrix.true_positives}
					</p>
				</div>
				<div class="rounded-xl border border-rose-400/40 bg-rose-50/60 p-4 dark:bg-rose-900/10">
					<p class="text-sm text-[var(--text-secondary)]">False Negatives</p>
					<p class="text-3xl font-semibold text-rose-700 dark:text-rose-300">
						{evaluation.confusion_matrix.false_negatives}
					</p>
				</div>
				<div class="rounded-xl border border-orange-400/40 bg-orange-50/60 p-4 dark:bg-orange-900/10">
					<p class="text-sm text-[var(--text-secondary)]">False Positives</p>
					<p class="text-3xl font-semibold text-orange-700 dark:text-orange-300">
						{evaluation.confusion_matrix.false_positives}
					</p>
				</div>
				<div class="rounded-xl border border-sky-400/40 bg-sky-50/60 p-4 dark:bg-sky-900/10">
					<p class="text-sm text-[var(--text-secondary)]">True Negatives</p>
					<p class="text-3xl font-semibold text-sky-700 dark:text-sky-300">
						{evaluation.confusion_matrix.true_negatives}
					</p>
				</div>
			</div>
			<p class="mt-4 text-sm text-[var(--text-secondary)]">
				Total labeled flows: {evaluation.total_flows.toLocaleString()}
			</p>
		</div>
	{/if}
</div>
