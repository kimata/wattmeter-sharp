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
