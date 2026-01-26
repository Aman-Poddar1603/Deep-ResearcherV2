import React from "react"
import Titlebar from "@/components/windowWidgets/Titlebar"
import { AppSidebar } from "./app-sidebar"
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar"

interface GlobalLayoutProps {
    children: React.ReactNode
}

export function GlobalLayout({ children }: GlobalLayoutProps) {
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
                        <div className="h-[calc(100vh-6.5rem)] bg-card rounded-2xl overflow-auto">
                            {children}
                        </div>
                    </SidebarInset>
                </div>
            </SidebarProvider>
        </div>
    )
}
