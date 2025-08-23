import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
    base: "/wattmeter-sharp/metrics/",
    plugins: [react()],
    define: {
        "import.meta.env.VITE_BUILD_DATE": JSON.stringify(
            new Date().toISOString(),
        ),
    },
    build: {
        // 並列処理を有効化
        target: "esnext",
        // CSS code splittingを無効化してビルド高速化
        cssCodeSplit: false,
        // バンドルサイズの最適化
        rollupOptions: {
            output: {
                // ベンダーチャンクを分離して効率的なキャッシュを実現
                manualChunks: {
                    vendor: ["react", "react-dom"],
                    utils: ["dayjs", "chart.js", "framer-motion"],
                },
            },
        },
        // 大きなチャンクの警告レベルを調整
        chunkSizeWarningLimit: 1000,
        // ソースマップを無効化してファイルサイズを削減
        sourcemap: false,
        // minifyの最適化（esbuildで高速ビルド）
        minify: "esbuild",
        // gzipサイズを表示
        reportCompressedSize: true,
    },
    // 依存関係の事前バンドル最適化
    optimizeDeps: {
        include: [
            "react",
            "react-dom",
            "chart.js",
            "dayjs",
            "framer-motion",
            "react-chartjs-2",
        ],
        // 依存関係の強制事前バンドル
        force: true,
    },
    // ビルド時のエラーをより厳密にチェック（開発時のみ）
    esbuild: {
        // 本番ビルドでconsole.logを削除
        drop: ["console", "debugger"],
    },
    // 開発サーバー最適化
    server: {
        warmup: {
            // よく使われるファイルを事前にウォームアップ
            clientFiles: ["./src/components/**/*.tsx", "./src/lib/**/*.ts"],
        },
    },
});
