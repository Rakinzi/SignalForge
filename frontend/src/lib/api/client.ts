import type {
	FlowSummary,
	AlertEvent,
	HealthMetrics,
	EntityBaseline,
	EvaluationMetrics,
	SystemConfig,
	LabUploadResponse,
	LabAnalyzeResult,
	LabTrainResult,
	LabDatasetParseResult,
	LabJob
} from '$lib/types';
import { getAccessToken } from './auth';

// API Base URL - defaults to local development
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

export class ApiError extends Error {
	status?: number;
	endpoint: string;

	constructor(message: string, endpoint: string, status?: number) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
		this.endpoint = endpoint;
	}
}

export type ApiErrorKind =
	| 'unauthorized'
	| 'forbidden'
	| 'not_found'
	| 'server_error'
	| 'network_error'
	| 'invalid_response'
	| 'unknown';

export interface NormalizedApiError {
	kind: ApiErrorKind;
	status?: number;
	message: string;
}

function kindFromStatus(status?: number): ApiErrorKind {
	if (status === 401) return 'unauthorized';
	if (status === 403) return 'forbidden';
	if (status === 404) return 'not_found';
	if (status !== undefined && status >= 500) return 'server_error';
	return 'unknown';
}

function userMessageFromKind(kind: ApiErrorKind, fallback: string): string {
	if (kind === 'unauthorized') {
		return 'Your session has expired. Please sign in again.';
	}
	if (kind === 'forbidden') {
		return 'Access to this data is restricted for your role.';
	}
	if (kind === 'not_found') {
		return 'The requested resource could not be found.';
	}
	if (kind === 'server_error') {
		return 'The backend service returned an error. Please try again.';
	}
	if (kind === 'network_error') {
		return 'Unable to reach the backend service.';
	}
	if (kind === 'invalid_response') {
		return 'The backend service returned an invalid response.';
	}
	return fallback;
}

export function normalizeApiError(error: unknown, fallback: string): NormalizedApiError {
	if (error instanceof ApiError) {
		if (error.message === 'Invalid JSON response from API') {
			const kind = 'invalid_response' as const;
			return {
				kind,
				status: error.status,
				message: userMessageFromKind(kind, fallback)
			};
		}

		const kind = kindFromStatus(error.status);
		return {
			kind,
			status: error.status,
			message: userMessageFromKind(kind, fallback)
		};
	}

	if (error instanceof TypeError) {
		const kind = 'network_error' as const;
		return {
			kind,
			message: userMessageFromKind(kind, fallback)
		};
	}

	return {
		kind: 'unknown',
		message: fallback
	};
}

// Generic API call wrapper with authentication
async function apiCall<T>(
	endpoint: string,
	options: RequestInit = {},
	requiresAuth: boolean = true
): Promise<T> {
	const headers = new Headers(options.headers);
	headers.set('Content-Type', 'application/json');

	// Add authentication token if required
	if (requiresAuth) {
		const token = await getAccessToken();
		if (!token) {
			throw new ApiError('Authentication required', endpoint, 401);
		}
		headers.set('Authorization', `Bearer ${token}`);
	}

	let response: Response;
	try {
		response = await fetch(`${API_BASE_URL}${endpoint}`, {
			...options,
			headers
		});
	} catch {
		throw new ApiError('Network error', endpoint);
	}

	if (!response.ok) {
		let detail = `API error: ${response.status}`;
		try {
			const payload = await response.json();
			if (payload?.detail) {
				detail = String(payload.detail);
			}
		} catch {
			// Keep fallback detail message.
		}
		throw new ApiError(detail, endpoint, response.status);
	}

	try {
		const data = await response.json();
		return data as T;
	} catch {
		throw new ApiError('Invalid JSON response from API', endpoint, response.status);
	}
}

async function authFetch(endpoint: string, options: RequestInit = {}): Promise<Response> {
	const headers = new Headers(options.headers);
	const token = await getAccessToken();
	if (!token) {
		throw new ApiError('Authentication required', endpoint, 401);
	}
	headers.set('Authorization', `Bearer ${token}`);

	let response: Response;
	try {
		response = await fetch(`${API_BASE_URL}${endpoint}`, {
			...options,
			headers
		});
	} catch {
		throw new ApiError('Network error', endpoint);
	}

	if (!response.ok) {
		let detail = `API error: ${response.status}`;
		try {
			const payload = await response.json();
			if (payload?.detail) {
				detail = String(payload.detail);
			}
		} catch {
			// Keep default message.
		}
		throw new ApiError(detail, endpoint, response.status);
	}
	return response;
}

// ========== API FUNCTIONS ==========

export async function getHealth(): Promise<HealthMetrics> {
	const data = await apiCall<any>('/health', {}, false);
	return {
		status: data?.status === 'ok' ? 'healthy' : 'degraded',
		ingest_rate: 0,
		flows_per_second: 0,
		alerts_count: 0,
		latency_ms: 0,
		uptime_seconds: 0
	};
}

export async function getMetrics(): Promise<HealthMetrics> {
	const data = await apiCall<any>('/metrics', {}, true);

	return {
		status: data.status || 'healthy',
		ingest_rate: data.ingest_rate ?? 0,
		flows_per_second: data.flows_per_second ?? 0,
		packets_per_second: data.packets_per_second ?? 0,
		alerts_count: data.alerts_count ?? data.alerts_open ?? 0,
		latency_ms: data.latency_ms ?? 0,
		uptime_seconds: data.uptime_seconds ?? 0,
		flows_total: data.flows_total ?? 0,
		alerts_total: data.alerts_total ?? 0,
		alerts_open: data.alerts_open ?? 0
	};
}

export async function getFlows(params?: {
	limit?: number;
	offset?: number;
	src_ip?: string;
	dst_ip?: string;
}): Promise<FlowSummary[]> {
	const queryParams = new URLSearchParams();
	if (params?.limit) queryParams.set('limit', params.limit.toString());
	if (params?.offset) queryParams.set('offset', params.offset.toString());
	if (params?.src_ip) queryParams.set('src_ip', params.src_ip);
	if (params?.dst_ip) queryParams.set('dst_ip', params.dst_ip);

	const data = await apiCall<{ items: any[] }>(`/flows?${queryParams}`, {}, true);

	// Backend returns {items: [...], limit, offset}, extract items and map fields
	return data.items.map((item: any) => ({
		schema_version: '1.0',
		flow_id: item.id,
		start_time: item.start_time,
		end_time: item.end_time,
		src_ip: item.src_ip,
		dst_ip: item.dst_ip,
		src_port: item.src_port,
		dst_port: item.dst_port,
		protocol: item.protocol,
		packet_count: item.packet_count,
		byte_count: item.byte_count,
		duration_ms: item.duration_ms,
		packet_rate: item.packet_rate
	}));
}

export async function getFlowById(id: string): Promise<FlowSummary | null> {
	const data = await apiCall<any>(`/flows/${id}`, {}, true);

	// Map backend response to FlowSummary
	return {
		schema_version: '1.0',
		flow_id: data.id,
		start_time: data.start_time,
		end_time: data.end_time,
		src_ip: data.src_ip,
		dst_ip: data.dst_ip,
		src_port: data.src_port,
		dst_port: data.dst_port,
		protocol: data.protocol,
		packet_count: data.packet_count,
		byte_count: data.byte_count,
		duration_ms: data.duration_ms,
		packet_rate: data.packet_rate
	};
}

export async function getAlerts(params?: { limit?: number; status?: string }): Promise<AlertEvent[]> {
	const queryParams = new URLSearchParams();
	if (params?.limit) queryParams.set('limit', params.limit.toString());
	// Backend uses status_filter instead of status
	if (params?.status) {
		const backendStatus = params.status === 'active' ? 'open' : params.status;
		queryParams.set('status_filter', backendStatus);
	}

	const data = await apiCall<{ items: any[] }>(`/alerts?${queryParams}`, {}, true);

	// Backend returns {items: [...], limit, offset}, extract items and map fields
	return data.items.map((item: any) => ({
		schema_version: '1.0',
		alert_id: item.id,
		detection_id: item.detection_id,
		severity: item.severity as any,
		status: (item.status === 'open' ? 'active' : item.status) as any,
		summary: item.summary,
		timestamp: item.created_at,
		flow_id: undefined // Not provided directly
	}));
}

export async function acknowledgeAlert(alertId: string): Promise<boolean> {
	const data = await apiCall<{ status: string }>(
		`/alerts/${alertId}/ack`,
		{ method: 'POST' },
		true
	);

	return data?.status === 'acknowledged';
}

export async function getEntities(): Promise<EntityBaseline[]> {
	const data = await apiCall<{ items: any[] }>('/baselines', {}, true);

	return data.items.map((item: any) => ({
		entity_id: item.entity_id,
		entity_type: item.entity_type,
		avg_packet_rate: item.avg_packet_rate,
		avg_byte_rate: item.avg_byte_rate,
		connection_count: item.connection_count,
		last_seen: item.last_seen,
		baseline_confidence: item.baseline_confidence
	}));
}

export async function getReports(): Promise<EvaluationMetrics | null> {
	const data = await apiCall<any>('/reports', {}, true);

	if (data.evaluation_metrics) {
		return data.evaluation_metrics;
	}

	// Fallback: use latest completed labeled analyze job from the Lab history.
	try {
		const jobs = await apiCall<{ items: Array<{ result?: any }> }>(
			'/detection/jobs?limit=20&job_type=analyze&status_filter=completed',
			{},
			true
		);
		for (const job of jobs.items ?? []) {
			const evalPayload = job?.result?.evaluation;
			const confusion = evalPayload?.confusion_matrix;
			const metrics = evalPayload?.metrics;
			if (!confusion || !metrics) continue;
			if (
				typeof confusion.true_positives === 'number' &&
				typeof confusion.false_positives === 'number' &&
				typeof confusion.true_negatives === 'number' &&
				typeof confusion.false_negatives === 'number' &&
				typeof metrics.precision === 'number' &&
				typeof metrics.recall === 'number' &&
				typeof metrics.f1_score === 'number' &&
				typeof metrics.accuracy === 'number'
			) {
				return {
					true_positives: confusion.true_positives,
					false_positives: confusion.false_positives,
					true_negatives: confusion.true_negatives,
					false_negatives: confusion.false_negatives,
					precision: metrics.precision,
					recall: metrics.recall,
					f1_score: metrics.f1_score,
					accuracy: metrics.accuracy
				};
			}
		}
	} catch {
		// Keep null fallback when job history is unavailable.
	}

	return null;
}

export async function getReportsOverview(): Promise<{
	metrics: EvaluationMetrics | null;
	by_rule: Array<{ rules: string; count: number }>;
	latest_evaluation: Record<string, unknown> | null;
}> {
	const data = await apiCall<any>('/reports', {}, true);
	const metrics = await getReports();
	return {
		metrics,
		by_rule: Array.isArray(data?.by_rule) ? data.by_rule : [],
		latest_evaluation:
			data?.latest_evaluation && typeof data.latest_evaluation === 'object'
				? data.latest_evaluation
				: null
	};
}

export async function getDetections(params?: {
	limit?: number;
	offset?: number;
	flow_id?: string;
	min_score?: number;
}): Promise<any[]> {
	const queryParams = new URLSearchParams();
	if (params?.limit) queryParams.set('limit', params.limit.toString());
	if (params?.offset) queryParams.set('offset', params.offset.toString());
	if (params?.flow_id) queryParams.set('flow_id', params.flow_id);
	if (params?.min_score !== undefined) queryParams.set('min_score', params.min_score.toString());

	const data = await apiCall<{ items: any[] }>(`/detections?${queryParams}`, {}, true);
	return data.items ?? [];
}

export async function getConfig(): Promise<SystemConfig> {
	const data = await apiCall<any>('/config', {}, true);

	return {
		detector_enabled: data.detector_enabled ?? true,
		rules_version: data.rules_version ?? '1.0.0',
		baseline_window_hours: data.baseline_window_hours ?? 24,
		alert_threshold: data.alert_threshold ?? 0.75,
		capture_interface: data.capture_interface ?? 'eth0'
	};
}

export async function getVersion(): Promise<{ version: string }> {
	return apiCall<{ version: string }>('/version', {}, false);
}

// SSE Connection for real-time alerts (requires authentication)
// Note: Backend expects token as URL parameter since EventSource doesn't support headers
export async function connectToAlertStream(
	onMessage: (alert: AlertEvent) => void,
	onError?: (error: Event) => void,
	onOpen?: () => void
): Promise<EventSource | null> {
	// Get auth token for SSE connection
	const token = await getAccessToken();
	if (!token) {
		console.warn('No auth token, SSE connection skipped');
		return null;
	}

	try {
		// Backend uses oauth2_scheme which expects token as query param
		const eventSource = new EventSource(
			`${API_BASE_URL}/stream/alerts?token=${encodeURIComponent(token)}`
		);
		eventSource.onopen = () => {
			onOpen?.();
		};

		eventSource.onmessage = (event) => {
			try {
				const payload = JSON.parse(event.data);
				// Backend wraps alert in {event: "alert", data: {...}}
				const alertData = payload.data || payload;

				const alert: AlertEvent = {
					schema_version: '1.0',
					alert_id: alertData.id,
					detection_id: alertData.detection_id,
					severity: alertData.severity,
					status: alertData.status,
					summary: alertData.summary,
					timestamp: alertData.created_at
				};

				onMessage(alert);
			} catch (error) {
				console.warn('Unable to parse alert stream event');
			}
		};

		eventSource.onerror = (error) => {
			onError?.(error);
			eventSource.close();
		};

		return eventSource;
	} catch (error) {
		console.warn('Unable to initialize alert stream');
		return null;
	}
}

export async function uploadDetectionPcap(file: File): Promise<LabUploadResponse> {
	const form = new FormData();
	form.append('file', file);
	const response = await authFetch('/detection/upload-pcap', {
		method: 'POST',
		body: form
	});
	return (await response.json()) as LabUploadResponse;
}

export async function uploadGroundTruthFile(file: File): Promise<LabUploadResponse> {
	const form = new FormData();
	form.append('file', file);
	const response = await authFetch('/detection/upload-ground-truth', {
		method: 'POST',
		body: form
	});
	return (await response.json()) as LabUploadResponse;
}

export async function analyzeDetectionPcap(params: {
	pcap_path: string;
	rules_path?: string;
	baseline_path?: string;
	ground_truth_path?: string;
}): Promise<LabAnalyzeResult> {
	const form = new URLSearchParams();
	form.set('pcap_path', params.pcap_path);
	if (params.rules_path) form.set('rules_path', params.rules_path);
	if (params.baseline_path) form.set('baseline_path', params.baseline_path);
	if (params.ground_truth_path) form.set('ground_truth_path', params.ground_truth_path);

	const response = await authFetch('/detection/analyze', {
		method: 'POST',
		headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
		body: form.toString()
	});
	return (await response.json()) as LabAnalyzeResult;
}

export async function trainDetectionStatistical(params: {
	training_pcap: string;
	output_path: string;
}): Promise<LabTrainResult> {
	const form = new URLSearchParams();
	form.set('training_pcap', params.training_pcap);
	form.set('output_path', params.output_path);
	const response = await authFetch('/detection/train-statistical', {
		method: 'POST',
		headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
		body: form.toString()
	});
	return (await response.json()) as LabTrainResult;
}

export async function parseDetectionDataset(params: {
	dataset_type: string;
	dataset_path: string;
}): Promise<LabDatasetParseResult> {
	const form = new URLSearchParams();
	form.set('dataset_type', params.dataset_type);
	form.set('dataset_path', params.dataset_path);
	const response = await authFetch('/detection/parse-dataset', {
		method: 'POST',
		headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
		body: form.toString()
	});
	return (await response.json()) as LabDatasetParseResult;
}

export async function getDetectionJobs(params?: {
	limit?: number;
	offset?: number;
	job_type?: string;
	status_filter?: string;
}): Promise<LabJob[]> {
	const queryParams = new URLSearchParams();
	if (params?.limit) queryParams.set('limit', params.limit.toString());
	if (params?.offset) queryParams.set('offset', params.offset.toString());
	if (params?.job_type) queryParams.set('job_type', params.job_type);
	if (params?.status_filter) queryParams.set('status_filter', params.status_filter);

	const data = await apiCall<{ items: LabJob[] }>(`/detection/jobs?${queryParams}`, {}, true);
	return data.items ?? [];
}

export async function getDetectionJob(jobId: string): Promise<LabJob> {
	return apiCall<LabJob>(`/detection/jobs/${jobId}`, {}, true);
}

export async function exportDetectionJob(jobId: string, format: 'json' | 'csv'): Promise<string> {
	const response = await authFetch(`/detection/jobs/${jobId}/export?format=${format}`, {});
	return response.text();
}
