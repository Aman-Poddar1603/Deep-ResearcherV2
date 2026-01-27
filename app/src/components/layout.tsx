import React from "react"
import Titlebar from "@/components/windowWidgets/Titlebar"
import { AppSidebar } from "./app-sidebar"
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar"
import { cn } from "@/lib/utils"

interface GlobalLayoutProps {
    children: React.ReactNode
    contentClassName?: string
}

export function GlobalLayout({ children, contentClassName }: GlobalLayoutProps) {
    return (
        <div className="flex flex-col h-screen bg-background text-foreground overflow-hidden">
            <Titlebar />
            <SidebarProvider defaultOpen={true}>
                <div className="flex flex-1 overflow-hidden relative">
                    <AppSidebar />
                    <SidebarInset className=" flex flex-col p-4">
                        <header className="flex items-center px-4 mb-2">
                            <SidebarTrigger />
                        </header>
                        <div className={cn("h-[calc(100vh-6.5rem)] bg-card rounded-2xl overflow-auto no-scrollbar border", contentClassName)}>
                            {children}
                        </div>
                    </SidebarInset>
                </div>
            </SidebarProvider>
        </div>
    )
}
