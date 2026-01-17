export interface SensorData {
    name: string;
    availability_total: number;
    availability_24h: number;
    last_received: string | null;
    power_consumption: number | null;
}

export interface ApiResponse {
    start_date: string;
    sensors: SensorData[];
}

export interface CommunicationError {
    sensor_name: string;
    datetime: string;
    timestamp: number;
    error_type: string;
}

export interface CommunicationErrorHistogram {
    bins: number[];
    bin_labels: string[];
    total_errors: number;
}

export interface CommunicationErrorResponse {
    histogram: CommunicationErrorHistogram;
    latest_errors: CommunicationError[];
}

export interface SysInfo {
    date: string;
    timezone: string;
    image_build_date: string;
    uptime: string;
    load_average: string;
    cpu_usage: number;
    memory_usage_percent: number;
    memory_free_mb: number;
    disk_usage_percent: number;
    disk_free_mb: number;
    process_count: number;
    cpu_temperature?: number;
}
