import { useLogo } from "../components/GetLogo"

export function Home() {
    const logo = useLogo()
    return (
        <div className="max-w-4xl mx-auto text-center space-y-8">
            <div className="space-y-4">
                <h1 className="text-5xl py-3 font-extrabold tracking-tight lg:text-6xl bg-linear-to-r from-white to-zinc-500 bg-clip-text text-transparent animate-in fade-in slide-in-from-bottom-4 duration-1000 fill-mode-both" style={{ animationDelay: '150ms' }}>
                    Deep Researcher
                </h1>
                <p className="text-xl text-muted-foreground max-w-2xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-1000 fill-mode-both" style={{ animationDelay: '300ms' }}>
                    The next generation of autonomous research and analysis,
                    powered by advanced agentic workflows.
                </p>
            </div>

            <div className="flex justify-center items-center py-12 animate-in fade-in zoom-in-95 duration-1000 fill-mode-both" style={{ animationDelay: '450ms' }}>
                <div className="relative">
                    <div className="absolute inset-0  blur-[100px] rounded-full"></div>
                    <img
                        src={logo}
                        className="w-40 h-40 relative z-10"
                        alt="Deep Researcher logo"
                    />
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto pt-8">
                <div className="p-6 rounded-2xl bg-white/5 border border-white/10 text-left space-y-2 animate-in fade-in slide-in-from-bottom-4 duration-1000 fill-mode-both" style={{ animationDelay: '600ms' }}>
                    <h3 className="font-semibold text-lg">Autonomous Search</h3>
                    <p className="text-sm text-zinc-400">Multi-step web searching and information gathering across multiple sources.</p>
                </div>
                <div className="p-6 rounded-2xl bg-white/5 border border-white/10 text-left space-y-2 animate-in fade-in slide-in-from-bottom-4 duration-1000 fill-mode-both" style={{ animationDelay: '750ms' }}>
                    <h3 className="font-semibold text-lg">In-depth Analysis</h3>
                    <p className="text-sm text-zinc-400">Synthesizing gathered data into coherent, professional reports and insights.</p>
                </div>
            </div>
        </div>
    )
}
