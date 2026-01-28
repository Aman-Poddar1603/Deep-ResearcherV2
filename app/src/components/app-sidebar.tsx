import * as React from "react"
import {
    Database,
    FolderOpen,
    FileSearch,
    MessageSquare,
    Settings,
    History,
    ChevronDown,
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
    SidebarMenuSub,
    SidebarMenuSubButton,
    SidebarMenuSubItem,
    SidebarRail,
} from "@/components/ui/sidebar"

import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from "@/components/ui/collapsible"

import { useInternalLogo } from "../ui/components/GetLogo"

const data = {
    navMain: [
        {
            title: "Data",
            icon: Database,
            items: [
                {
                    title: "Databases",
                    url: "#/data/databases",
                },
                {
                    title: "Bucket",
                    url: "#/data/bucket",
                },
            ],
        },
        {
            title: "Workspaces",
            icon: FolderOpen,
            items: [
                {
                    title: "Create new Workspace",
                    url: "#/workspaces/new",
                },
                {
                    title: "View All Workspaces",
                    url: "#/workspaces/all",
                },
            ],
        },
        {
            title: "Researches",
            icon: FileSearch,
            items: [
                {
                    title: "Start new Research",
                    url: "#/researches/new",
                },
                {
                    title: "View All Researches",
                    url: "#/researches/all",
                },
            ],
        },
        {
            title: "Chat",
            icon: MessageSquare,
            items: [
                {
                    title: "Start new Chat",
                    url: "#/chat/new",
                },
                {
                    title: "View All Chats",
                    url: "#/chat/all",
                },
            ],
        },
        {
            title: "Settings",
            url: "#/settings",
            icon: Settings,
        },
        {
            title: "History",
            url: "#/history",
            icon: History,
        },
    ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
    const internalLogo = useInternalLogo()
    return (
        <Sidebar collapsible="icon" className="border-none bg-background mt-10" {...props}>
            <SidebarHeader className="p-4 bg-background animate-in fade-in slide-in-from-left-4 duration-1000 fill-mode-both" style={{ animationDelay: '100ms' }}>
                <div className="flex items-center gap-3">
                    <div className="flex skeleton-sidebar-icon size-10 shrink-0 items-center justify-center rounded-lg bg-background text-primary-foreground group-data-[collapsible=icon]:size-8">
                        <img
                            src={internalLogo}
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
                    <SidebarGroupLabel className="animate-in fade-in slide-in-from-left-4 duration-1000 fill-mode-both" style={{ animationDelay: '200ms' }}>Application</SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {data.navMain.map((item, index) => {
                                // Check if the item has sub-items
                                if ('items' in item && item.items) {
                                    return (
                                        <Collapsible
                                            key={item.title}
                                            asChild
                                            defaultOpen={false}
                                            className="group/collapsible"
                                        >
                                            <SidebarMenuItem className="animate-in fade-in slide-in-from-left-4 duration-1000 fill-mode-both" style={{ animationDelay: `${300 + index * 100}ms` }}>
                                                <CollapsibleTrigger asChild>
                                                    <SidebarMenuButton tooltip={item.title}>
                                                        <item.icon />
                                                        <span>{item.title}</span>
                                                        <ChevronDown className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-180" />
                                                    </SidebarMenuButton>
                                                </CollapsibleTrigger>
                                                <CollapsibleContent>
                                                    <SidebarMenuSub>
                                                        {item.items.map((subItem) => (
                                                            <SidebarMenuSubItem key={subItem.title}>
                                                                <SidebarMenuSubButton asChild>
                                                                    <a href={subItem.url}>
                                                                        <span>{subItem.title}</span>
                                                                    </a>
                                                                </SidebarMenuSubButton>
                                                            </SidebarMenuSubItem>
                                                        ))}
                                                    </SidebarMenuSub>
                                                </CollapsibleContent>
                                            </SidebarMenuItem>
                                        </Collapsible>
                                    )
                                }

                                // Regular menu item without sub-items
                                return (
                                    <SidebarMenuItem key={item.title} className="animate-in fade-in slide-in-from-left-4 duration-1000 fill-mode-both" style={{ animationDelay: `${300 + index * 100}ms` }}>
                                        <SidebarMenuButton asChild tooltip={item.title}>
                                            <a href={item.url}>
                                                <item.icon />
                                                <span>{item.title}</span>
                                            </a>
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                )
                            })}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>
            <SidebarRail />
        </Sidebar>
    )
}
