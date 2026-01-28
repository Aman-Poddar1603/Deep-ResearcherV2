import React, { useState } from "react"
import { useNavigate } from "react-router-dom"
import Titlebar from "@/components/windowWidgets/Titlebar"
import { AppSidebar } from "./app-sidebar"
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight, RotateCw, Home } from "lucide-react"
import { cn } from "@/lib/utils"

interface GlobalLayoutProps {
    children: React.ReactNode
    contentClassName?: string
}

export function GlobalLayout({ children, contentClassName }: GlobalLayoutProps) {
    const navigate = useNavigate()
    const [reloadKey, setReloadKey] = useState(0)

    const handleBack = () => {
        navigate(-1)
    }

    const handleForward = () => {
        navigate(1)
    }

    const handleHome = () => {
        navigate("/")
    }

    const handleReload = () => {
        setReloadKey(prev => prev + 1)
    }

    return (
        <div className="flex flex-col h-screen bg-background text-foreground overflow-hidden">
            <Titlebar />
            <SidebarProvider defaultOpen={true}>
                <div className="flex flex-1 overflow-hidden relative">
                    <AppSidebar />
                    <SidebarInset className="flex flex-col p-4">
                        <header className="flex items-center gap-2 px-4 mb-2">
                            <SidebarTrigger />

                            <Separator orientation="vertical" className="h-6" />

                            {/* Home Button */}
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={handleHome}
                                title="Go to home"
                            >
                                <Home className="h-4 w-4" />
                            </Button>

                            <Separator orientation="vertical" className="h-6" />

                            {/* Navigation Buttons */}
                            <div className="flex items-center gap-1">
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-7 w-7"
                                    onClick={handleBack}
                                    title="Go back"
                                >
                                    <ChevronLeft className="h-4 w-4" />
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-7 w-7"
                                    onClick={handleForward}
                                    title="Go forward"
                                >
                                    <ChevronRight className="h-4 w-4" />
                                </Button>
                            </div>

                            <Separator orientation="vertical" className="h-6" />

                            {/* Reload Button */}
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7"
                                onClick={handleReload}
                                title="Reload content"
                            >
                                <RotateCw className="h-4 w-4" />
                            </Button>
                        </header>
                        <div
                            key={reloadKey}
                            className={cn("h-[calc(100vh-6.5rem)] bg-card rounded-2xl overflow-auto no-scrollbar border", contentClassName)}
                        >
                            {children}
                        </div>
                    </SidebarInset>
                </div>
            </SidebarProvider>
        </div>
    )
}
