<script lang="ts">
	import { Icon } from 'svelte-hero-icons';
	import MetricCard from '$lib/components/MetricCard.svelte';
	import { onMount } from 'svelte';

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
		performance: {
			avg_processing_time_ms: number;
			throughput_flows_per_second: number;
		};
		total_flows: number;
	}

	let evaluation = $state<EvaluationData | null>(null);
	let isLoading = $state(true);

	async function loadEvaluation() {
		isLoading = true;
		try {
			const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
			const response = await fetch(`${apiUrl}/reports`);

			if (response.ok) {
				const data = await response.json();
				evaluation = data.evaluation_metrics || null;
			}
		} catch (error) {
			console.error('Failed to load evaluation:', error);
		} finally {
			isLoading = false;
		}
	}

	onMount(() => {
		loadEvaluation();
	});
</script>

<svelte:head>
	<title>Evaluation Metrics - SignalForge</title>
</svelte:head>

<div class="space-y-6">
	<!-- Header -->
	<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
		<div>
			<h1 class="text-2xl font-bold text-[var(--text-primary)]">Evaluation Metrics</h1>
			<p class="text-sm text-[var(--text-secondary)] mt-1">
				Detection performance and accuracy metrics
			</p>
		</div>
		<button
			onclick={loadEvaluation}
			class="self-start sm:self-auto px-4 py-2 bg-[var(--accent-primary)] hover:bg-[var(--accent-primary)]/90 text-white rounded-lg transition-colors flex items-center gap-2"
		>
			<Icon src="arrow-path" class="w-4 h-4" />
			<span>Refresh</span>
		</button>
	</div>

	{#if isLoading}
		<div class="flex items-center justify-center py-12">
			<Icon src="arrow-path" class="w-8 h-8 text-[var(--accent-primary)] animate-spin" />
		</div>
	{:else if !evaluation}
		<div class="text-center py-12 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg">
			<Icon src="chart-bar" class="w-12 h-12 text-[var(--text-secondary)] mx-auto mb-3" />
			<p class="text-[var(--text-secondary)]">No evaluation data available</p>
			<p class="text-sm text-[var(--text-secondary)] mt-1">
				Run detection analysis with ground truth labels to generate metrics
			</p>
		</div>
	{:else}
		<!-- Detection Metrics -->
		<div>
			<h2 class="text-lg font-semibold text-[var(--text-primary)] mb-4">Detection Accuracy</h2>
			<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
				<MetricCard
					label="Precision"
					value={(evaluation.metrics.precision * 100).toFixed(1) + '%'}
					icon="check-circle"
					trend="neutral"
					color="var(--color-success)"
				/>
				<MetricCard
					label="Recall"
					value={(evaluation.metrics.recall * 100).toFixed(1) + '%'}
					icon="shield-check"
					trend="neutral"
					color="var(--accent-primary)"
				/>
				<MetricCard
					label="F1-Score"
					value={(evaluation.metrics.f1_score * 100).toFixed(1) + '%'}
					icon="chart-bar"
					trend="neutral"
					color="var(--accent-primary)"
				/>
				<MetricCard
					label="Accuracy"
					value={(evaluation.metrics.accuracy * 100).toFixed(1) + '%'}
					icon="check-badge"
					trend="neutral"
					color="var(--color-success)"
				/>
				<MetricCard
					label="FPR"
					value={(evaluation.metrics.false_positive_rate * 100).toFixed(1) + '%'}
					icon="x-circle"
					trend="neutral"
					color="var(--color-medium)"
				/>
				<MetricCard
					label="FNR"
					value={(evaluation.metrics.false_negative_rate * 100).toFixed(1) + '%'}
					icon="exclamation-circle"
					trend="neutral"
					color="var(--color-high)"
				/>
			</div>
		</div>

		<!-- Performance Metrics -->
		<div>
			<h2 class="text-lg font-semibold text-[var(--text-primary)] mb-4">Performance</h2>
			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
				<MetricCard
					label="Avg Processing Time"
					value={evaluation.performance.avg_processing_time_ms.toFixed(2) + ' ms'}
					icon="clock"
					trend="neutral"
					color="var(--accent-primary)"
				/>
				<MetricCard
					label="Throughput"
					value={evaluation.performance.throughput_flows_per_second.toFixed(1) + ' flows/s'}
					icon="bolt"
					trend="neutral"
					color="var(--color-success)"
				/>
				<MetricCard
					label="Total Flows"
					value={evaluation.total_flows}
					icon="arrows-right-left"
					trend="neutral"
					color="var(--text-primary)"
				/>
			</div>
		</div>

		<!-- Confusion Matrix -->
		<div class="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-6">
			<h2 class="text-lg font-semibold text-[var(--text-primary)] mb-4">Confusion Matrix</h2>

			<!-- Matrix Grid -->
			<div class="grid grid-cols-2 gap-4 max-w-2xl">
				<!-- True Positives -->
				<div class="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
					<div class="flex items-center gap-2 mb-2">
						<Icon src="check-circle" class="w-5 h-5 text-green-500" />
						<span class="text-sm font-medium text-[var(--text-primary)]">True Positives</span>
					</div>
					<div class="text-2xl font-bold text-green-500">
						{evaluation.confusion_matrix.true_positives}
					</div>
					<p class="text-xs text-[var(--text-secondary)] mt-1">Correctly identified threats</p>
				</div>

				<!-- False Positives -->
				<div class="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4">
					<div class="flex items-center gap-2 mb-2">
						<Icon src="exclamation-triangle" class="w-5 h-5 text-orange-500" />
						<span class="text-sm font-medium text-[var(--text-primary)]">False Positives</span>
					</div>
					<div class="text-2xl font-bold text-orange-500">
						{evaluation.confusion_matrix.false_positives}
					</div>
					<p class="text-xs text-[var(--text-secondary)] mt-1">Benign flagged as malicious</p>
				</div>

				<!-- False Negatives -->
				<div class="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
					<div class="flex items-center gap-2 mb-2">
						<Icon src="x-circle" class="w-5 h-5 text-red-500" />
						<span class="text-sm font-medium text-[var(--text-primary)]">False Negatives</span>
					</div>
					<div class="text-2xl font-bold text-red-500">
						{evaluation.confusion_matrix.false_negatives}
					</div>
					<p class="text-xs text-[var(--text-secondary)] mt-1">Missed threats</p>
				</div>

				<!-- True Negatives -->
				<div class="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
					<div class="flex items-center gap-2 mb-2">
						<Icon src="check-badge" class="w-5 h-5 text-blue-500" />
						<span class="text-sm font-medium text-[var(--text-primary)]">True Negatives</span>
					</div>
					<div class="text-2xl font-bold text-blue-500">
						{evaluation.confusion_matrix.true_negatives}
					</div>
					<p class="text-xs text-[var(--text-secondary)] mt-1">Correctly identified benign</p>
				</div>
			</div>

			<!-- Matrix Table -->
			<div class="mt-6 overflow-x-auto">
				<table class="w-full max-w-2xl text-sm">
					<thead>
						<tr class="border-b border-[var(--border-color)]">
							<th class="p-2"></th>
							<th class="p-2 text-[var(--text-primary)] font-semibold text-center">Predicted Positive</th>
							<th class="p-2 text-[var(--text-primary)] font-semibold text-center">Predicted Negative</th>
						</tr>
					</thead>
					<tbody>
						<tr class="border-b border-[var(--border-color)]">
							<td class="p-2 text-[var(--text-primary)] font-semibold">Actual Positive</td>
							<td class="p-2 text-center text-green-500 font-bold">
								{evaluation.confusion_matrix.true_positives}
							</td>
							<td class="p-2 text-center text-red-500 font-bold">
								{evaluation.confusion_matrix.false_negatives}
							</td>
						</tr>
						<tr>
							<td class="p-2 text-[var(--text-primary)] font-semibold">Actual Negative</td>
							<td class="p-2 text-center text-orange-500 font-bold">
								{evaluation.confusion_matrix.false_positives}
							</td>
							<td class="p-2 text-center text-blue-500 font-bold">
								{evaluation.confusion_matrix.true_negatives}
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>

		<!-- Metric Definitions -->
		<div class="bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg p-6">
			<h2 class="text-lg font-semibold text-[var(--text-primary)] mb-4">Metric Definitions</h2>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
				<div>
					<span class="font-semibold text-[var(--text-primary)]">Precision:</span>
					<span class="text-[var(--text-secondary)]"> TP / (TP + FP)</span>
					<p class="text-xs text-[var(--text-secondary)] mt-1">
						Proportion of positive predictions that are correct
					</p>
				</div>
				<div>
					<span class="font-semibold text-[var(--text-primary)]">Recall:</span>
					<span class="text-[var(--text-secondary)]"> TP / (TP + FN)</span>
					<p class="text-xs text-[var(--text-secondary)] mt-1">
						Proportion of actual positives correctly identified
					</p>
				</div>
				<div>
					<span class="font-semibold text-[var(--text-primary)]">F1-Score:</span>
					<span class="text-[var(--text-secondary)]"> 2 * (Precision * Recall) / (Precision + Recall)</span>
					<p class="text-xs text-[var(--text-secondary)] mt-1">
						Harmonic mean of precision and recall
					</p>
				</div>
				<div>
					<span class="font-semibold text-[var(--text-primary)]">Accuracy:</span>
					<span class="text-[var(--text-secondary)]"> (TP + TN) / Total</span>
					<p class="text-xs text-[var(--text-secondary)] mt-1">
						Overall correctness of the model
					</p>
				</div>
			</div>
		</div>
	{/if}
</div>
