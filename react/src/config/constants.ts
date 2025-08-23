// APIのベースURLを管理
// Viteのbaseパスと同じ値を使用してAPIエンドポイントを構築

// vite.config.tsで明示的に定義されたAPI_BASE_URLを使用
export const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "/wattmeter-sharp/metrics/";

// API URLを構築するヘルパー関数
export const buildApiUrl = (endpoint: string): string => {
    // API_BASE_URLは末尾にスラッシュを含むので、endpointの先頭スラッシュを除去
    const cleanEndpoint = endpoint.startsWith("/")
        ? endpoint.slice(1)
        : endpoint;
    // apiディレクトリを挟んでURLを構築
    return `${API_BASE_URL}api/${cleanEndpoint}`;
};
