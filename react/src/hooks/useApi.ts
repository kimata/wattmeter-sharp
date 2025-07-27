import { useState, useEffect, useCallback } from "react";

interface UseApiOptions {
    interval?: number;
}

export function useApi<T>(url: string, options?: UseApiOptions) {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchData = useCallback(async () => {
        try {
            setError(null);
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const jsonData = await response.json();
            setData(jsonData);
        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "データの取得に失敗しました",
            );
        } finally {
            setLoading(false);
        }
    }, [url]);

    useEffect(() => {
        fetchData();

        if (options?.interval) {
            const intervalId = setInterval(fetchData, options.interval);
            return () => clearInterval(intervalId);
        }
    }, [fetchData, options?.interval]);

    return { data, loading, error, refetch: fetchData };
}
