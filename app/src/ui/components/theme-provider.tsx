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
    "coffee",
    "fresh",
    "nerd",
    "smooth",
];

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const [theme, setTheme] = useState<Theme>(() => {
        const stored = localStorage.getItem("ui-theme");
        return stored && availableThemes.includes(stored) ? stored : "default";
    });
    const [isDark, setIsDark] = useState<boolean>(() => {
        return localStorage.getItem("ui-dark-mode") === "true";
    });

    useEffect(() => {
        const root = window.document.documentElement;

        // Remove all previous theme classes
        const classes = Array.from(root.classList);
        classes.forEach((c) => {
            if (c.startsWith("theme-")) {
                root.classList.remove(c);
            }
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
