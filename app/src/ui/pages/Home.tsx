import { useLogo } from "../components/GetLogo"
import { Link } from "react-router-dom"

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

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl mx-auto pt-8">
                <Link 
                    to="/search" 
                    className="group relative p-6 rounded-2xl bg-white/5 border border-white/10 text-left space-y-2 animate-in fade-in slide-in-from-bottom-4 duration-1000 fill-mode-both hover:bg-white/(7) hover:border-primary/50 transition-all block overflow-hidden" 
                    style={{ animationDelay: '600ms' }}
                >
                    {/* Unique Glow Effect */}
                    <div className="absolute -inset-1 bg-linear-to-r from-primary/20 to-secondary/20 blur-xl opacity-0 group-hover:opacity-100 transition-opacity" />
                    
                    <div className="relative z-10 flex justify-between items-start">
                        <h3 className="font-semibold text-lg text-zinc-100 group-hover:text-primary transition-colors">Autonomous Search</h3>
                        <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all translate-x-4 group-hover:translate-x-0">
                            <svg className="w-4 h-4 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                            </svg>
                        </div>
                    </div>
                    <p className="text-sm text-zinc-400 group-hover:text-zinc-300 transition-colors relative z-10">Multi-step web searching and information gathering across multiple sources.</p>
                </Link>
                
                <Link 
                    to="/researches/new" 
                    className="group relative p-6 rounded-2xl bg-white/5 border border-white/10 text-left space-y-2 animate-in fade-in slide-in-from-bottom-4 duration-1000 fill-mode-both hover:bg-white/(7) hover:border-primary/50 transition-all block overflow-hidden" 
                    style={{ animationDelay: '750ms' }}
                >
                    {/* Unique Glow Effect */}
                    <div className="absolute -inset-1 bg-linear-to-r from-primary/20 to-secondary/20 blur-xl opacity-0 group-hover:opacity-100 transition-opacity" />
                    
                    <div className="relative z-10 flex justify-between items-start">
                        <h3 className="font-semibold text-lg text-zinc-100 group-hover:text-primary transition-colors">In-depth Analysis</h3>
                        <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all translate-x-4 group-hover:translate-x-0">
                            <svg className="w-4 h-4 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                            </svg>
                        </div>
                    </div>
                    <p className="text-sm text-zinc-400 group-hover:text-zinc-300 transition-colors relative z-10">Synthesizing gathered data into coherent, professional reports and insights.</p>
                </Link>
            </div>
        </div>
    )
}
