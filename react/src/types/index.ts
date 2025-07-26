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
