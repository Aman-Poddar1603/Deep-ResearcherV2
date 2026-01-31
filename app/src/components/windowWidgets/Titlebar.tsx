import React from 'react'
import { Square, Copy, X, Minus } from 'lucide-react'
import { ThemeSwitcher } from '../ThemeSwitcher'
import { useInternalLogo } from '@/ui/components/GetLogo'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

interface DraggableStyle extends React.CSSProperties {
    WebkitAppRegion: 'drag' | 'no-drag';
}

const Titlebar = () => {
    const [isMaximized, setIsMaximized] = React.useState(true); // Default to true as we force maximize on start
    const internalLogo = useInternalLogo()
    const handleMinimize = () => {
        window.electron.minimizeWindow();
    }

    const handleMaximize = () => {
        window.electron.maximizeWindow();
    }

    const handleClose = () => {
        window.electron.closeWindow();
    }

    React.useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'F12' || (e.ctrlKey && e.shiftKey && e.key === 'I')) {
                e.preventDefault();
                window.electron.toggleDevTools();
            }
        };
        window.addEventListener('keydown', handleKeyDown);

        const unsubscribe = window.electron.subscribeWindowResize((maximized) => {
            setIsMaximized(maximized);
        });

        return () => {
            window.removeEventListener('keydown', handleKeyDown);
            unsubscribe();
        }
    }, []);

    return (
        <div
            className='fixed top-0 left-0 right-0 w-full h-10 bg-background/80 backdrop-blur-md flex items-center justify-between px-4 select-none z-50'
            style={{ WebkitAppRegion: 'drag' } as DraggableStyle}
        >
            <div className='flex items-center gap-2'>
                <img src={internalLogo} alt="" className='h-5 w-5' />
                <h1 className='text-xs font-medium tracking-tight text-muted-foreground uppercase'>Deep Researcher</h1>
            </div>
            <div className='flex items-center gap-1' style={{ WebkitAppRegion: 'no-drag' } as DraggableStyle}>
                <TooltipProvider disableHoverableContent>
                    <ThemeSwitcher />
                    <div className='flex items-center -mr-4'>
                        <Tooltip delayDuration={700}>
                            <TooltipTrigger asChild>
                                <button
                                    onClick={handleMinimize}
                                    className='h-10 px-4 hover:bg-muted transition-colors flex items-center justify-center group'
                                >
                                    <Minus className='w-3.5 h-3.5 text-muted-foreground group-hover:text-foreground' />
                                </button>
                            </TooltipTrigger>
                            <TooltipContent side="bottom" showArrow={false}>
                                <p>Minimize</p>
                            </TooltipContent>
                        </Tooltip>

                        <Tooltip delayDuration={700}>
                            <TooltipTrigger asChild>
                                <button
                                    onClick={handleMaximize}
                                    className='h-10 px-4 hover:bg-muted transition-colors flex items-center justify-center group'
                                >
                                    {isMaximized ? (
                                        <Copy className='w-3 h-3 text-muted-foreground group-hover:text-foreground rotate-y-180' />
                                    ) : (
                                        <Square className='w-3 h-3 text-muted-foreground group-hover:text-foreground' />
                                    )}
                                </button>
                            </TooltipTrigger>
                            <TooltipContent side="bottom" showArrow={false}>
                                <p>{isMaximized ? 'Restore' : 'Maximize'}</p>
                            </TooltipContent>
                        </Tooltip>

                        <Tooltip delayDuration={700}>
                            <TooltipTrigger asChild>
                                <button
                                    onClick={handleClose}
                                    className='h-10 px-4 hover:bg-destructive hover:text-destructive-foreground transition-colors flex items-center justify-center group'
                                >
                                    <X className='w-4 h-4 text-muted-foreground group-hover:text-destructive-foreground' />
                                </button>
                            </TooltipTrigger>
                            <TooltipContent side="bottom" showArrow={false}>
                                <p>Close</p>
                            </TooltipContent>
                        </Tooltip>
                    </div>
                </TooltipProvider>
            </div>
        </div>
    )
}

export default Titlebar
