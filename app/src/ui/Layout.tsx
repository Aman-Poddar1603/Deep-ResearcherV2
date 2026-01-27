import { Outlet } from "react-router-dom"
import { GlobalLayout } from "@/components/layout"
import Composer from "@/components/widgets/Composer"

export function Layout() {
    return (
        <GlobalLayout>
            <div className="flex flex-col h-full relative">
                {/* Scrollable Content Area */}
                <div className="flex-1 overflow-y-auto p-8 pt-12 pb-32">
                    <Outlet />
                </div>

                {/* Floating Composer Area at the bottom */}
                <div className="absolute bottom-0 left-0 w-full pb-8 pt-4 px-4 bg-linear-to-t from-background via-background/80 to-transparent pointer-events-none z-20">
                    <div className="pointer-events-auto">
                        <Composer />
                    </div>
                </div>
            </div>
        </GlobalLayout>
    )
}
