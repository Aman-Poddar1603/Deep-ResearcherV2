import * as React from "react"
import {
    Home,
    Search,
    Layers,
    Layout as LayoutIcon,
    Settings,
} from "lucide-react"

import {
    Sidebar,
    SidebarContent,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarRail,
} from "@/components/ui/sidebar"

const data = {
    navMain: [
        {
            title: "Dashboard",
            url: "#",
            icon: Home,
        },
        {
            title: "Research",
            url: "#",
            icon: Search,
        },
        {
            title: "Projects",
            url: "#",
            icon: Layers,
        },
        {
            title: "Templates",
            url: "#",
            icon: LayoutIcon,
        },
        {
            title: "Settings",
            url: "#",
            icon: Settings,
        },
        {
            title: "Dev Tools",
            url: "#",
            icon: LayoutIcon,
            isDev: true
        },
    ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
    return (
        <Sidebar collapsible="icon" className="border-none bg-background mt-10" {...props}>
            <SidebarHeader className="p-4 bg-background">
                <div className="flex items-center gap-3">
                    <div className="flex skeleton-sidebar-icon size-10 shrink-0 items-center justify-center rounded-lg bg-background text-primary-foreground group-data-[collapsible=icon]:size-8">
                        <img
                            src="/brand/DeepResearcherAgentModeAdvance.png"
                            alt="Logo"
                            className="h-full w-full object-contain"
                        />
                    </div>
                    <div className="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
                        <span className="truncate font-semibold">Deep Researcher</span>
                        <span className="truncate text-xs text-muted-foreground">v1.0.0</span>
                    </div>
                </div>
            </SidebarHeader>
            <SidebarContent className="bg-background">
                <SidebarGroup>
                    <SidebarGroupLabel>Application</SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {data.navMain.map((item) => (
                                <SidebarMenuItem key={item.title}>
                                    <SidebarMenuButton
                                        asChild={!('isDev' in item)}
                                        tooltip={item.title}
                                        onClick={('isDev' in item) ? () => window.electron.toggleDevTools() : undefined}
                                    >
                                        {('isDev' in item) ? (
                                            <button className="flex w-full items-center gap-2">
                                                <item.icon />
                                                <span>{item.title}</span>
                                            </button>
                                        ) : (
                                            <a href={item.url}>
                                                <item.icon />
                                                <span>{item.title}</span>
                                            </a>
                                        )}
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            ))}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>
            <SidebarRail />
        </Sidebar>
    )
}
