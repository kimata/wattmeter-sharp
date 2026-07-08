import { useEffect, useState } from "react";

export function usePrefersDark(): boolean {
    const [isDark, setIsDark] = useState(
        () => window.matchMedia("(prefers-color-scheme: dark)").matches,
    );

    useEffect(() => {
        const media = window.matchMedia("(prefers-color-scheme: dark)");
        const listener = (event: MediaQueryListEvent) =>
            setIsDark(event.matches);
        media.addEventListener("change", listener);
        return () => media.removeEventListener("change", listener);
    }, []);

    return isDark;
}
