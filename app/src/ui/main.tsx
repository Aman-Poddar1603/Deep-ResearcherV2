import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import { ThemeProvider } from './components/theme-provider'
import { StatusProvider } from '@/contexts/StatusContext'
import './themes.css'
import { Toaster } from "@/components/ui/sonner"

createRoot(document.getElementById('root')!).render(
	<StrictMode>
		<StatusProvider>
			<ThemeProvider>
				<App />
				<Toaster />
			</ThemeProvider>
		</StatusProvider>
	</StrictMode>
)
