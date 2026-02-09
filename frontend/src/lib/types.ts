// Auto-generated from JSON schemas

export interface FlowSummary {
	schema_version: string;
	flow_id: string;
	start_time: string;
	end_time: string;
	src_ip: string;
	dst_ip: string;
	src_port: number;
	dst_port: number;
	protocol: string;
	packet_count: number;
	byte_count: number;
	duration_ms: number;
	packet_rate: number;
}

export interface AlertEvent {
	schema_version: string;
	alert_id: string;
	detection_id: string;
	severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
	status: 'active' | 'acknowledged' | 'resolved';
	summary: string;
	timestamp?: string;
	flow_id?: string;
}

export interface DetectionResult {
	schema_version: string;
	flow_id: string;
	rules_triggered: string[];
	anomaly_score: number;
	baseline: Record<string, unknown>;
	explanation: string;
}

export interface HealthMetrics {
	status: 'healthy' | 'degraded' | 'unhealthy';
	ingest_rate: number;
	flows_per_second: number;
	alerts_count: number;
	latency_ms: number;
	uptime_seconds: number;
	packets_per_second?: number;
	flows_total?: number;
	alerts_total?: number;
	alerts_open?: number;
}

export interface EntityBaseline {
	entity_id: string;
	entity_type: 'ip' | 'service' | 'host';
	avg_packet_rate: number;
	avg_byte_rate: number;
	connection_count: number;
	last_seen: string;
	baseline_confidence: number;
}

export interface EvaluationMetrics {
	true_positives: number;
	false_positives: number;
	true_negatives: number;
	false_negatives: number;
	precision: number;
	recall: number;
	f1_score: number;
	accuracy: number;
}

export interface SystemConfig {
	detector_enabled: boolean;
	rules_version: string;
	baseline_window_hours: number;
	alert_threshold: number;
	capture_interface: string;
}

export interface HybridDecisionBreakdown {
	flow_id?: string;
	rules_triggered?: string[] | string;
	anomaly_score?: number;
	explanation?: string;
	[key: string]: unknown;
}

export interface LabUploadResponse {
	status: string;
	filename: string;
	file_path: string;
	size_bytes: number;
}

export interface LabAnalyzeResult {
	job_id: string;
	status: string;
	flows_processed?: number;
	decisions?: HybridDecisionBreakdown[];
	evaluation?: Record<string, unknown>;
}

export interface LabTrainResult {
	job_id: string;
	status: string;
	baseline_path: string;
	profile_summary: Record<string, unknown>;
}

export interface LabDatasetParseResult {
	job_id: string;
	dataset_type: string;
	flows_parsed: number;
	total_ground_truth: number;
	sample_flows: Array<Record<string, unknown>>;
	malicious_count: number;
	benign_count: number;
}

export interface LabJob {
	job_id: string;
	created_at: string;
	actor: string;
	job_type: string;
	status: string;
	input: Record<string, unknown>;
	result: Record<string, unknown> | null;
	error?: string | null;
}
