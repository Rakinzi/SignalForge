<script lang="ts">
	import { onMount } from 'svelte';
	import { currentUser } from '$lib/stores/auth';
	import {
		uploadDetectionPcap,
		uploadGroundTruthFile,
		analyzeDetectionPcap,
		trainDetectionStatistical,
		parseDetectionDataset,
		getDetectionJobs,
		normalizeApiError
	} from '$lib/api/client';
	import type {
		LabAnalyzeResult,
		LabDatasetParseResult,
		LabJob,
		LabTrainResult,
		LabUploadResponse
	} from '$lib/types';
	import PageStateForbidden from '$lib/components/PageStateForbidden.svelte';
	import PageStateError from '$lib/components/PageStateError.svelte';
	import PageStateLoading from '$lib/components/PageStateLoading.svelte';

	let role = $derived($currentUser?.role ?? 'viewer');
	let canRun = $derived(role === 'admin' || role === 'analyst');

	let selectedFile = $state<File | null>(null);
	let selectedGroundTruth = $state<File | null>(null);
	let uploaded = $state<LabUploadResponse | null>(null);
	let uploadedGroundTruth = $state<LabUploadResponse | null>(null);
	let lastAnalyze = $state<LabAnalyzeResult | null>(null);
	let lastTrain = $state<LabTrainResult | null>(null);
	let lastDataset = $state<LabDatasetParseResult | null>(null);

	let analyzePath = $state('');
	let rulesPath = $state('');
	let baselinePath = $state('');
	let groundTruthPath = $state('');

	let trainingPcap = $state('');
	let outputPath = $state(`/tmp/baseline-${Date.now()}.json`);

	let datasetType = $state('cicids');
	let datasetPath = $state('');

	let isUploading = $state(false);
	let isUploadingGroundTruth = $state(false);
	let isAnalyzing = $state(false);
	let isTraining = $state(false);
	let isParsing = $state(false);

	let historyLoading = $state(true);
	let historyError = $state<string | null>(null);
	let jobs = $state<LabJob[]>([]);

	let actionError = $state<string | null>(null);
	let actionSuccess = $state<string | null>(null);

	function harareTime(value: string): string {
		return new Date(value).toLocaleString('en-ZW', { timeZone: 'Africa/Harare' });
	}

	async function refreshJobs() {
		historyLoading = true;
		historyError = null;
		try {
			jobs = await getDetectionJobs({ limit: 25, offset: 0 });
		} catch (err) {
			historyError = normalizeApiError(err, 'Failed to load experiment history').message;
		} finally {
			historyLoading = false;
		}
	}

	async function handleUpload() {
		actionError = null;
		actionSuccess = null;
		if (!selectedFile) {
			actionError = 'Select a PCAP file first.';
			return;
		}
		isUploading = true;
		try {
			uploaded = await uploadDetectionPcap(selectedFile);
			analyzePath = uploaded.file_path;
			trainingPcap = uploaded.file_path;
			actionSuccess = `Uploaded ${uploaded.filename}`;
		} catch (err) {
			actionError = normalizeApiError(err, 'PCAP upload failed').message;
		} finally {
			isUploading = false;
		}
	}

	async function handleAnalyze() {
		actionError = null;
		actionSuccess = null;
		if (!analyzePath.trim()) {
			actionError = 'Provide a PCAP path to analyze.';
			return;
		}
		isAnalyzing = true;
		try {
			lastAnalyze = await analyzeDetectionPcap({
				pcap_path: analyzePath,
				rules_path: rulesPath || undefined,
				baseline_path: baselinePath || undefined,
				ground_truth_path: groundTruthPath || undefined
			});
			actionSuccess = `Analysis completed (${lastAnalyze.job_id})`;
			await refreshJobs();
		} catch (err) {
			actionError = normalizeApiError(err, 'Analysis failed').message;
		} finally {
			isAnalyzing = false;
		}
	}

	async function handleGroundTruthUpload() {
		actionError = null;
		actionSuccess = null;
		if (!selectedGroundTruth) {
			actionError = 'Select a ground truth JSON file first.';
			return;
		}
		isUploadingGroundTruth = true;
		try {
			uploadedGroundTruth = await uploadGroundTruthFile(selectedGroundTruth);
			groundTruthPath = uploadedGroundTruth.file_path;
			actionSuccess = `Uploaded labels: ${uploadedGroundTruth.filename}`;
		} catch (err) {
			actionError = normalizeApiError(err, 'Ground truth upload failed').message;
		} finally {
			isUploadingGroundTruth = false;
		}
	}

	async function handleTrain() {
		actionError = null;
		actionSuccess = null;
		if (!trainingPcap.trim() || !outputPath.trim()) {
			actionError = 'Provide training PCAP and output baseline path.';
			return;
		}
		isTraining = true;
		try {
			lastTrain = await trainDetectionStatistical({
				training_pcap: trainingPcap,
				output_path: outputPath
			});
			actionSuccess = `Training completed (${lastTrain.job_id})`;
			await refreshJobs();
		} catch (err) {
			actionError = normalizeApiError(err, 'Statistical training failed').message;
		} finally {
			isTraining = false;
		}
	}

	async function handleParseDataset() {
		actionError = null;
		actionSuccess = null;
		if (!datasetPath.trim()) {
			actionError = 'Provide a dataset path to parse.';
			return;
		}
		isParsing = true;
		try {
			lastDataset = await parseDetectionDataset({
				dataset_type: datasetType,
				dataset_path: datasetPath
			});
			actionSuccess = `Dataset parsed (${lastDataset.job_id})`;
			await refreshJobs();
		} catch (err) {
			actionError = normalizeApiError(err, 'Dataset parsing failed').message;
		} finally {
			isParsing = false;
		}
	}

	onMount(refreshJobs);
</script>

<svelte:head>
	<title>Research Lab - SignalForge</title>
</svelte:head>

{#if !canRun}
	<PageStateForbidden
		title="Lab access is restricted"
		message="Active hybrid testing operations are available to analyst and admin roles."
		requiredRole="analyst or admin"
	/>
{:else}
	<div class="space-y-6">
		<div>
			<h1 class="text-2xl font-semibold text-[var(--text-primary)]">Hybrid Detection Lab</h1>
			<p class="mt-1 text-sm text-[var(--text-secondary)]">
				Run PCAP analysis, train statistical baselines, parse research datasets, and inspect experiment history.
			</p>
		</div>

		{#if actionError}
			<PageStateError message={actionError} />
		{/if}
		{#if actionSuccess}
			<div class="rounded-xl border border-emerald-300/60 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
				{actionSuccess}
			</div>
		{/if}

		<div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
			<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-5 shadow-[var(--shadow-soft)] space-y-4">
				<h2 class="text-lg font-semibold text-[var(--text-primary)]">PCAP Upload + Analyze</h2>
				<div class="space-y-2">
					<label class="block text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
						PCAP file
					</label>
					<input
						id="pcap-file-input"
						type="file"
						accept=".pcap,.pcapng"
						onchange={(event) => {
							const target = event.target as HTMLInputElement;
							selectedFile = target.files?.[0] ?? null;
						}}
						class="sr-only"
					/>
					<label
						for="pcap-file-input"
						class="inline-flex cursor-pointer items-center rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-2 text-sm font-medium text-[var(--text-primary)] transition hover:bg-[var(--bg-tertiary)]"
					>
						Choose PCAP
					</label>
					<p class="text-xs text-[var(--text-secondary)]">
						{selectedFile ? `Selected: ${selectedFile.name}` : 'No PCAP file selected.'}
					</p>
				</div>
				<button
					onclick={handleUpload}
					disabled={isUploading}
					class="rounded-lg bg-[var(--accent-primary)] px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
				>
					{isUploading ? 'Uploading...' : 'Upload PCAP'}
				</button>
				<div class="space-y-2">
					<label class="block text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
						Ground truth JSON
					</label>
					<input
						id="ground-truth-file-input"
						type="file"
						accept=".json"
						onchange={(event) => {
							const target = event.target as HTMLInputElement;
							selectedGroundTruth = target.files?.[0] ?? null;
						}}
						class="sr-only"
					/>
					<label
						for="ground-truth-file-input"
						class="inline-flex cursor-pointer items-center rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-2 text-sm font-medium text-[var(--text-primary)] transition hover:bg-[var(--bg-tertiary)]"
					>
						Choose Ground Truth
					</label>
					<p class="text-xs text-[var(--text-secondary)]">
						{selectedGroundTruth
							? `Selected: ${selectedGroundTruth.name}`
							: 'No ground truth file selected.'}
					</p>
				</div>
				<button
					onclick={handleGroundTruthUpload}
					disabled={isUploadingGroundTruth}
					class="rounded-lg border border-[var(--border-color)] px-3 py-2 text-sm font-medium text-[var(--text-primary)] disabled:opacity-60"
				>
					{isUploadingGroundTruth ? 'Uploading labels...' : 'Upload Ground Truth'}
				</button>
				<input bind:value={analyzePath} placeholder="PCAP path" class="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-2 text-sm" />
				<input bind:value={rulesPath} placeholder="Rules path (optional)" class="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-2 text-sm" />
				<input bind:value={baselinePath} placeholder="Baseline path (optional)" class="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-2 text-sm" />
				<input bind:value={groundTruthPath} placeholder="Ground truth path (optional JSON)" class="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-2 text-sm" />
				<button
					onclick={handleAnalyze}
					disabled={isAnalyzing}
					class="rounded-lg bg-[var(--accent-primary)] px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
				>
					{isAnalyzing ? 'Analyzing...' : 'Run Analysis'}
				</button>
				{#if lastAnalyze}
					<p class="text-sm text-[var(--text-secondary)]">
						Latest analysis: {lastAnalyze.job_id}, flows processed: {lastAnalyze.flows_processed ?? 0}
					</p>
				{/if}
				{#if uploadedGroundTruth}
					<p class="text-sm text-[var(--text-secondary)]">
						Ground truth uploaded: {uploadedGroundTruth.filename}
					</p>
				{/if}
			</div>

			<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-5 shadow-[var(--shadow-soft)] space-y-4">
				<h2 class="text-lg font-semibold text-[var(--text-primary)]">Statistical Baseline Training</h2>
				<input bind:value={trainingPcap} placeholder="Training PCAP path" class="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-2 text-sm" />
				<input bind:value={outputPath} placeholder="Output baseline path" class="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-2 text-sm" />
				<button
					onclick={handleTrain}
					disabled={isTraining}
					class="rounded-lg bg-[var(--accent-primary)] px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
				>
					{isTraining ? 'Training...' : 'Train Baseline'}
				</button>
				{#if lastTrain}
					<p class="text-sm text-[var(--text-secondary)]">
						Latest training: {lastTrain.job_id} -> {lastTrain.baseline_path}
					</p>
				{/if}
			</div>
		</div>

		<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-5 shadow-[var(--shadow-soft)] space-y-4">
			<h2 class="text-lg font-semibold text-[var(--text-primary)]">Dataset Parser</h2>
			<select bind:value={datasetType} class="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-2 text-sm">
				<option value="cicids">CICIDS</option>
				<option value="ctu13">CTU-13</option>
				<option value="unsw-nb15">UNSW-NB15</option>
			</select>
			<input bind:value={datasetPath} placeholder="Dataset path" class="w-full rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] px-3 py-2 text-sm" />
			<button
				onclick={handleParseDataset}
				disabled={isParsing}
				class="rounded-lg bg-[var(--accent-primary)] px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
			>
				{isParsing ? 'Parsing...' : 'Parse Dataset'}
			</button>
			{#if lastDataset}
				<p class="text-sm text-[var(--text-secondary)]">
					Parsed {lastDataset.flows_parsed} flows. Malicious: {lastDataset.malicious_count}, Benign: {lastDataset.benign_count}
				</p>
			{/if}
		</div>

		<div class="rounded-xl border border-[var(--border-color)] bg-[var(--panel)] p-5 shadow-[var(--shadow-soft)]">
			<div class="flex items-center justify-between">
				<h2 class="text-lg font-semibold text-[var(--text-primary)]">Experiment History</h2>
				<button onclick={refreshJobs} class="rounded-lg border border-[var(--border-color)] px-3 py-2 text-sm">Refresh</button>
			</div>
			{#if historyLoading}
				<div class="mt-4">
					<PageStateLoading label="Loading history..." />
				</div>
			{:else if historyError}
				<div class="mt-4">
					<PageStateError message={historyError} onAction={refreshJobs} />
				</div>
			{:else if jobs.length === 0}
				<p class="mt-4 text-sm text-[var(--text-secondary)]">No experiments yet.</p>
			{:else}
				<div class="mt-4 overflow-x-auto">
					<table class="min-w-full text-sm">
						<thead>
							<tr class="text-left text-[var(--text-secondary)]">
								<th class="px-2 py-2">Job</th>
								<th class="px-2 py-2">Type</th>
								<th class="px-2 py-2">Status</th>
								<th class="px-2 py-2">Actor</th>
								<th class="px-2 py-2">Created (Harare)</th>
							</tr>
						</thead>
						<tbody>
							{#each jobs as job (job.job_id)}
								<tr class="border-t border-[var(--border-color)]">
									<td class="px-2 py-2 font-mono"><a href={`/lab/${job.job_id}`} class="text-[var(--accent-primary)] hover:underline">{job.job_id}</a></td>
									<td class="px-2 py-2">{job.job_type}</td>
									<td class="px-2 py-2">{job.status}</td>
									<td class="px-2 py-2">{job.actor}</td>
									<td class="px-2 py-2">{harareTime(job.created_at)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</div>
	</div>
{/if}
