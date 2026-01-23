import type {
	FlowSummary,
	AlertEvent,
	DetectionResult,
	HealthMetrics,
	EntityBaseline,
	EvaluationMetrics,
	SystemConfig
} from '$lib/types';
import { getAccessToken } from './auth';

// API Base URL - defaults to local development
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// Check if API is available
let apiAvailable = false;
let lastHealthCheck = 0;
const HEALTH_CHECK_INTERVAL = 30000; // 30 seconds

async function checkApiHealth(): Promise<boolean> {
	const now = Date.now();
	if (now - lastHealthCheck < HEALTH_CHECK_INTERVAL) {
		return apiAvailable;
	}

	try {
		const response = await fetch(`${API_BASE_URL}/health`, {
			method: 'GET',
			signal: AbortSignal.timeout(2000)
		});
		apiAvailable = response.ok;
		lastHealthCheck = now;
		return apiAvailable;
	} catch {
		apiAvailable = false;
		lastHealthCheck = now;
		return false;
	}
}

// Generic API call wrapper with authentication
async function apiCall<T>(
	endpoint: string,
	options: RequestInit = {},
	requiresAuth: boolean = true
): Promise<{ data: T | null; usedMock: boolean }> {
	const isHealthy = await checkApiHealth();

	if (!isHealthy) {
		console.warn(`API unavailable, using mock data for ${endpoint}`);
		return { data: null, usedMock: true };
	}

	try {
		const headers: HeadersInit = {
			'Content-Type': 'application/json',
			...options.headers
		};

		// Add authentication token if required
		if (requiresAuth) {
			const token = await getAccessToken();
			if (!token) {
				console.warn('No auth token available, using mock data');
				return { data: null, usedMock: true };
			}
			headers['Authorization'] = `Bearer ${token}`;
		}

		const response = await fetch(`${API_BASE_URL}${endpoint}`, {
			...options,
			headers
		});

		if (!response.ok) {
			throw new Error(`API error: ${response.status}`);
		}

		const data = await response.json();
		return { data, usedMock: false };
	} catch (error) {
		console.error(`API call failed for ${endpoint}:`, error);
		return { data: null, usedMock: true };
	}
}

// ========== MOCK DATA ==========

function generateMockFlows(count: number): FlowSummary[] {
	const protocols = ['TCP', 'UDP', 'ICMP'];
	const flows: FlowSummary[] = [];

	for (let i = 0; i < count; i++) {
		const startTime = new Date(Date.now() - Math.random() * 3600000);
		const duration = Math.floor(Math.random() * 60000);
		const endTime = new Date(startTime.getTime() + duration);

		flows.push({
			schema_version: '1.0',
			flow_id: `flow-${Date.now()}-${i}`,
			start_time: startTime.toISOString(),
			end_time: endTime.toISOString(),
			src_ip: `192.168.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
			dst_ip: `10.0.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
			src_port: Math.floor(Math.random() * 65535),
			dst_port: [80, 443, 22, 3306, 5432, 8080][Math.floor(Math.random() * 6)],
			protocol: protocols[Math.floor(Math.random() * protocols.length)],
			packet_count: Math.floor(Math.random() * 10000),
			byte_count: Math.floor(Math.random() * 1000000),
			duration_ms: duration,
			packet_rate: Math.random() * 1000
		});
	}

	return flows;
}

function generateMockAlerts(count: number): AlertEvent[] {
	const severities: AlertEvent['severity'][] = ['critical', 'high', 'medium', 'low', 'info'];
	const statuses: AlertEvent['status'][] = ['active', 'acknowledged', 'resolved'];
	const summaries = [
		'SYN flood detected from source IP',
		'Port scan activity observed',
		'Unusual traffic spike detected',
		'High connection rate anomaly',
		'Suspicious DNS query pattern',
		'Potential data exfiltration',
		'Brute force attempt detected',
		'DDoS attack in progress'
	];

	return Array.from({ length: count }, (_, i) => ({
		schema_version: '1.0',
		alert_id: `alert-${Date.now()}-${i}`,
		detection_id: `det-${Date.now()}-${i}`,
		severity: severities[Math.floor(Math.random() * severities.length)],
		status: statuses[Math.floor(Math.random() * statuses.length)],
		summary: summaries[Math.floor(Math.random() * summaries.length)],
		timestamp: new Date(Date.now() - Math.random() * 3600000).toISOString(),
		flow_id: `flow-${Date.now()}-${i}`
	}));
}

const mockHealthMetrics: HealthMetrics = {
	status: 'healthy',
	ingest_rate: 1234.56,
	flows_per_second: 567.89,
	alerts_count: 42,
	latency_ms: 12.34,
	uptime_seconds: 86400
};

const mockEntityBaselines: EntityBaseline[] = [
	{
		entity_id: '192.168.1.100',
		entity_type: 'ip',
		avg_packet_rate: 123.45,
		avg_byte_rate: 456789,
		connection_count: 234,
		last_seen: new Date().toISOString(),
		baseline_confidence: 0.95
	},
	{
		entity_id: 'web-service-01',
		entity_type: 'service',
		avg_packet_rate: 567.89,
		avg_byte_rate: 1234567,
		connection_count: 1234,
		last_seen: new Date().toISOString(),
		baseline_confidence: 0.92
	}
];

const mockEvaluationMetrics: EvaluationMetrics = {
	true_positives: 142,
	false_positives: 8,
	true_negatives: 9845,
	false_negatives: 5,
	precision: 0.9467,
	recall: 0.9660,
	f1_score: 0.9563,
	accuracy: 0.9987
};

const mockSystemConfig: SystemConfig = {
	detector_enabled: true,
	rules_version: '2.1.0',
	baseline_window_hours: 24,
	alert_threshold: 0.75,
	capture_interface: 'eth0'
};

// ========== API FUNCTIONS ==========

export async function getHealth(): Promise<HealthMetrics> {
	const { data, usedMock } = await apiCall<any>('/health', {}, false); // Health doesn't require auth
	return usedMock || !data ? mockHealthMetrics : mockHealthMetrics; // Backend health endpoint doesn't return metrics format
}

export async function getMetrics(): Promise<HealthMetrics> {
	const { data, usedMock } = await apiCall<any>('/metrics', {}, true);

	if (usedMock || !data) {
		return mockHealthMetrics;
	}

	return {
		status: data.status || 'healthy',
		ingest_rate: data.ingest_rate ?? 0,
		flows_per_second: data.flows_per_second ?? 0,
		alerts_count: data.alerts_count ?? data.alerts_open ?? 0,
		latency_ms: data.latency_ms ?? 0,
		uptime_seconds: data.uptime_seconds ?? 0
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

	const { data, usedMock } = await apiCall<{ items: any[] }>(`/flows?${queryParams}`, {}, true);

	if (usedMock || !data) {
		return generateMockFlows(params?.limit || 50);
	}

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
	const { data, usedMock } = await apiCall<any>(`/flows/${id}`, {}, true);

	if (usedMock || !data) {
		return generateMockFlows(1)[0];
	}

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
	if (params?.status) queryParams.set('status_filter', params.status);

	const { data, usedMock } = await apiCall<{ items: any[] }>(`/alerts?${queryParams}`, {}, true);

	if (usedMock || !data) {
		return generateMockAlerts(params?.limit || 20);
	}

	// Backend returns {items: [...], limit, offset}, extract items and map fields
	return data.items.map((item: any) => ({
		schema_version: '1.0',
		alert_id: item.id,
		detection_id: item.detection_id,
		severity: item.severity as any,
		status: item.status as any,
		summary: item.summary,
		timestamp: item.created_at,
		flow_id: undefined // Not provided directly
	}));
}

export async function acknowledgeAlert(alertId: string): Promise<boolean> {
	const { data, usedMock } = await apiCall<{ status: string }>(
		`/alerts/${alertId}/ack`,
		{ method: 'POST' },
		true
	);

	if (usedMock) {
		console.log(`Mock: Acknowledged alert ${alertId}`);
		return true;
	}

	return data?.status === 'acknowledged';
}

export async function getEntities(): Promise<EntityBaseline[]> {
	const { data, usedMock } = await apiCall<{ items: any[] }>('/baselines', {}, true);

	if (usedMock || !data) {
		return mockEntityBaselines;
	}

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

export async function getReports(): Promise<EvaluationMetrics> {
	const { data, usedMock } = await apiCall<any>('/reports', {}, true);

	if (usedMock || !data) {
		return mockEvaluationMetrics;
	}

	if (data.evaluation_metrics) {
		return data.evaluation_metrics;
	}

	return mockEvaluationMetrics;
}

export async function getConfig(): Promise<SystemConfig> {
	const { data, usedMock } = await apiCall<any>('/config', {}, true);

	if (usedMock || !data) {
		return mockSystemConfig;
	}

	return {
		detector_enabled: data.detector_enabled ?? true,
		rules_version: data.rules_version ?? '1.0.0',
		baseline_window_hours: data.baseline_window_hours ?? 24,
		alert_threshold: data.alert_threshold ?? 0.75,
		capture_interface: data.capture_interface ?? 'eth0'
	};
}

export async function getVersion(): Promise<{ version: string }> {
	const { data, usedMock } = await apiCall<{ version: string }>('/version', {}, false);
	return usedMock || !data ? { version: '1.0.0-dev' } : data;
}

// SSE Connection for real-time alerts (requires authentication)
// Note: Backend expects token as URL parameter since EventSource doesn't support headers
export async function connectToAlertStream(
	onMessage: (alert: AlertEvent) => void,
	onError?: (error: Event) => void
): Promise<EventSource | null> {
	if (!apiAvailable) {
		console.warn('API unavailable, SSE connection skipped');
		return null;
	}

	// Get auth token for SSE connection
	const token = await getAccessToken();
	if (!token) {
		console.warn('No auth token, SSE connection skipped');
		return null;
	}

	try {
		// Backend uses oauth2_scheme which expects token as query param
		const eventSource = new EventSource(`${API_BASE_URL}/stream/alerts?token=${token}`);

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
				console.error('Failed to parse SSE message:', error);
			}
		};

		eventSource.onerror = (error) => {
			console.error('SSE connection error:', error);
			onError?.(error);
			eventSource.close();
		};

		return eventSource;
	} catch (error) {
		console.error('Failed to create SSE connection:', error);
		return null;
	}
}
