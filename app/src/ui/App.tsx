import { useState } from 'react'
import { Button } from "@/components/ui/button"
import reactLogo from './assets/react.svg'
import './App.css'
import { GlobalLayout } from '@/components/layout'

function App() {
    const [count, setCount] = useState(0)

    return (
        <GlobalLayout>
            <div className='p-8 max-w-4xl mx-auto'>
                <div className='text-center'>
                    <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl mb-4">
                        Deep Researcher
                    </h1>
                    <p className="text-xl text-muted-foreground mb-8">
                        Premium Layout with shadcn/ui Sidebar
                    </p>

                    <div className='flex justify-center items-center my-8'>
                        <a href="https://react.dev" target="_blank">
                            <img src={reactLogo} className="w-32 h-32 animate-[spin_20s_linear_infinite]" alt="React logo" />
                        </a>
                    </div>

                    <div className="flex flex-col items-center gap-6">
                        <Button
                            size="lg"
                            className='w-48 text-lg font-semibold'
                            onClick={() => setCount((count) => count + 1)}
                        >
                            Count: {count}
                        </Button>

                        <p className="max-w-md mx-auto text-muted-foreground leading-relaxed italic">
                            "The sidebar is now powered by shadcn/ui.
                            The layout is managed globally, and the content floats in a borderless rounded area."
                        </p>
                    </div>

                    <div className="mt-12 flex flex-wrap items-center justify-center gap-4">
                        <Button asChild variant="secondary" size="lg">
                            <a href="https://buymeacoffee.com/georgimy" target="_blank" rel="noopener noreferrer">
                                ☕ Buy me a coffee
                            </a>
                        </Button>

                        <Button asChild variant="ghost" size="lg">
                            <a href="https://x.com/GeorgiMY" target="_blank" rel="noopener noreferrer">
                                Follow me on X
                            </a>
                        </Button>
                    </div>
                </div>
            </div>
        </GlobalLayout>
    )
}

export default App
