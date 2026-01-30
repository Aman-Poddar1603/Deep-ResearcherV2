import { Moon, Sun, Palette, Check } from "lucide-react"
import { useTheme } from "@/ui/components/theme-provider"
import { Button } from "@/components/ui/button"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

const themeNames: Record<string, string> = {
    default: "Default",
    coffee: "Coffee",
    fresh: "Fresh",
    nerd: "Nerd",
    smooth: "Smooth",
}

export function ThemeSwitcher() {
    const { theme, setTheme, isDark, setIsDark, availableThemes } = useTheme()

    return (
        <div className="flex items-center gap-2">
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8">
                        <Palette className="h-4 w-4" />
                        <span className="sr-only">Switch theme</span>
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuLabel>Select Theme</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    {availableThemes.map((t) => (
                        <DropdownMenuItem
                            key={t}
                            onClick={() => setTheme(t)}
                            className="flex items-center justify-between"
                        >
                            {themeNames[t] || t}
                            {theme === t && <Check className="h-4 w-4" />}
                        </DropdownMenuItem>
                    ))}
                    <DropdownMenuSeparator />
                    <DropdownMenuLabel>Mode</DropdownMenuLabel>
                    <DropdownMenuItem
                        onClick={() => setIsDark(false)}
                        className="flex items-center justify-between"
                    >
                        <div className="flex items-center gap-2">
                            <Sun className="h-4 w-4" />
                            Light
                        </div>
                        {!isDark && <Check className="h-4 w-4" />}
                    </DropdownMenuItem>
                    <DropdownMenuItem
                        onClick={() => setIsDark(true)}
                        className="flex items-center justify-between"
                    >
                        <div className="flex items-center gap-2">
                            <Moon className="h-4 w-4" />
                            Dark
                        </div>
                        {isDark && <Check className="h-4 w-4" />}
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </div>
    )
}
