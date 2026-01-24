import React, { createContext, useContext, useEffect, useState } from "react";

type Theme = string;

interface ThemeContextType {
    theme: Theme;
    setTheme: (theme: Theme) => void;
    isDark: boolean;
    setIsDark: (dark: boolean) => void;
    availableThemes: string[];
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const availableThemes = [
    "default",
    "amethyst",
    "bubblegum",
    "caffeine",
    "calude",
    "clay",
    "darkmatter",
    "eleluxary",
    "solardusk",
    "supabase",
    "t3chat",
    "voiletbloom",
];

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const [theme, setTheme] = useState<Theme>(() => {
        return localStorage.getItem("ui-theme") || "default";
    });
    const [isDark, setIsDark] = useState<boolean>(() => {
        return localStorage.getItem("ui-dark-mode") === "true";
    });

    useEffect(() => {
        const root = window.document.documentElement;

        // Remove all previous theme classes
        availableThemes.forEach((t) => {
            root.classList.remove(`theme-${t}`);
        });

        // Add current theme class
        root.classList.add(`theme-${theme}`);

        // Handle dark mode
        if (isDark) {
            root.classList.add("dark");
        } else {
            root.classList.remove("dark");
        }

        localStorage.setItem("ui-theme", theme);
        localStorage.setItem("ui-dark-mode", String(isDark));
    }, [theme, isDark]);

    return (
        <ThemeContext.Provider value={{ theme, setTheme, isDark, setIsDark, availableThemes }}>
            {children}
        </ThemeContext.Provider>
    );
}

export const useTheme = () => {
    const context = useContext(ThemeContext);
    if (context === undefined)
        throw new Error("useTheme must be used within a ThemeProvider");
    return context;
};
