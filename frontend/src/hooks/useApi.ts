import { useState, useEffect, useCallback, useRef } from "react";

interface UseApiOptions {
    interval?: number;
}

// NOTE: 一時的な取得失敗では直前のデータを保持し、UI 側で
// 「古いデータ + エラーバナー」を表示できるようにする
export function useApi<T>(url: string, options?: UseApiOptions) {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const urlRef = useRef(url);
    urlRef.current = url;

    const fetchData = useCallback(async () => {
        const requestUrl = urlRef.current;
        try {
            const response = await fetch(requestUrl);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const jsonData = await response.json();
            // URL が切り替わった後に古いリクエストが返ってきた場合は無視
            if (urlRef.current !== requestUrl) return;
            setData(jsonData);
            setError(null);
        } catch (err) {
            if (urlRef.current !== requestUrl) return;
            setError(
                err instanceof Error
                    ? err.message
                    : "データの取得に失敗しました",
            );
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();

        if (options?.interval) {
            const intervalId = setInterval(() => {
                // 非表示タブではポーリングを止めて無駄なリクエストを抑える
                if (document.visibilityState === "visible") {
                    fetchData();
                }
            }, options.interval);
            return () => clearInterval(intervalId);
        }
    }, [fetchData, options?.interval, url]);

    return { data, loading, error, refetch: fetchData };
}
