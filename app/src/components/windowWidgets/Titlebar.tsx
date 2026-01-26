import React from 'react'
import { Square, X, Minus } from 'lucide-react'
import { ThemeSwitcher } from '../ThemeSwitcher'

interface DraggableStyle extends React.CSSProperties {
    WebkitAppRegion: 'drag' | 'no-drag';
}

const Titlebar = () => {
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
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    return (
        <div
            className='w-full h-10 bg-background/80 backdrop-blur-md flex items-center justify-between px-4  select-none z-50'
            style={{ WebkitAppRegion: 'drag' } as DraggableStyle}
        >
            <div className='flex items-center gap-2'>
                <div className='w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_rgba(var(--primary),0.5)]' />
                <h1 className='text-xs font-medium tracking-tight text-muted-foreground uppercase'>Deep Researcher</h1>
            </div>
            <div className='flex items-center gap-1' style={{ WebkitAppRegion: 'no-drag' } as DraggableStyle}>
                <ThemeSwitcher />
                <div className='flex items-center -mr-4'>
                    <button
                        onClick={handleMinimize}
                        className='h-10 px-4 hover:bg-muted transition-colors flex items-center justify-center group'
                        title='Minimize'
                    >
                        <Minus className='w-3.5 h-3.5 text-muted-foreground group-hover:text-foreground' />
                    </button>
                    <button
                        onClick={handleMaximize}
                        className='h-10 px-4 hover:bg-muted transition-colors flex items-center justify-center group'
                        title='Maximize'
                    >
                        <Square className='w-3 h-3 text-muted-foreground group-hover:text-foreground' />
                    </button>
                    <button
                        onClick={handleClose}
                        className='h-10 px-4 hover:bg-destructive hover:text-destructive-foreground transition-colors flex items-center justify-center group'
                        title='Close'
                    >
                        <X className='w-4 h-4 text-muted-foreground group-hover:text-destructive-foreground' />
                    </button>
                </div>
            </div>
        </div>
    )
}

export default Titlebar
