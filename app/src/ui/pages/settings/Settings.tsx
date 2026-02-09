import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { PromptEditorModal } from '@/components/ui/prompt-editor-modal'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select'
import {
    Settings as SettingsIcon,
    Palette,
    Bell,
    Database,
    Globe,
    Sparkles,
    ChevronRight,
    Save,
    RotateCcw,
} from 'lucide-react'

// Settings Section Component
interface SettingsSectionProps {
    title: string
    description: string
    icon: React.ReactNode
    children: React.ReactNode
    delay: string
}

const SettingsSection = ({ title, description, icon, children, delay }: SettingsSectionProps) => (
    <div
        className="p-6 rounded-2xl bg-card border border-border/50 space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-700 fill-mode-both"
        style={{ animationDelay: delay }}
    >
        <div className="flex items-center gap-3">
            <div className="size-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                {icon}
            </div>
            <div>
                <h3 className="font-semibold text-foreground">{title}</h3>
                <p className="text-sm text-muted-foreground">{description}</p>
            </div>
        </div>
        <Separator className="bg-border/50" />
        <div className="space-y-4">
            {children}
        </div>
    </div>
)

// Setting Item Component
interface SettingItemProps {
    label: string
    description?: string
    children: React.ReactNode
}

const SettingItem = ({ label, description, children }: SettingItemProps) => (
    <div className="flex items-center justify-between gap-4">
        <div className="flex-1">
            <p className="text-sm font-medium text-foreground">{label}</p>
            {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
        </div>
        <div className="shrink-0">
            {children}
        </div>
    </div>
)

const Settings = () => {
    // Appearance Settings
    const [theme, setTheme] = useState('system')
    const [reducedMotion, setReducedMotion] = useState(false)

    // Research Settings
    const [autoSave, setAutoSave] = useState(true)
    const [maxSearchDepth, setMaxSearchDepth] = useState('3')
    const [defaultReportFormat, setDefaultReportFormat] = useState('markdown')

    // Notification Settings
    const [researchComplete, setResearchComplete] = useState(true)
    const [errorAlerts, setErrorAlerts] = useState(true)
    const [soundEnabled, setSoundEnabled] = useState(false)

    // Data Settings
    const [autoCleanup, setAutoCleanup] = useState(false)
    const [dataRetention, setDataRetention] = useState('30')

    // AI Settings
    const [aiPersonality, setAiPersonality] = useState('professional')
    const [customPrompt, setCustomPrompt] = useState('')
    const [researchTemplate, setResearchTemplate] = useState('comprehensive')
    const [streamResponse, setStreamResponse] = useState(true)
    const [showSources, setShowSources] = useState(true)
    const [detailedAnalysis, setDetailedAnalysis] = useState(true)

    const handleResetDefaults = () => {
        setTheme('system')
        setReducedMotion(false)
        setAutoSave(true)
        setMaxSearchDepth('3')
        setDefaultReportFormat('markdown')
        setResearchComplete(true)
        setErrorAlerts(true)
        setSoundEnabled(false)
        setAutoCleanup(false)
        setDataRetention('30')
        setAiPersonality('professional')
        setCustomPrompt('')
        setResearchTemplate('comprehensive')
        setStreamResponse(true)
        setShowSources(true)
        setDetailedAnalysis(true)
    }

    return (
        <div className="flex flex-col h-full w-full bg-muted/10 overflow-hidden animate-in fade-in duration-500">
            {/* Header Section */}
            <div className="shrink-0 border-b border-border/50 bg-background/50 backdrop-blur-sm sticky top-0 z-30">
                <div className="w-full px-8 py-6">
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                            <div
                                className="size-12 rounded-2xl bg-linear-to-br from-primary/20 via-primary/10 to-transparent border border-primary/20 flex items-center justify-center animate-in fade-in zoom-in duration-500"
                            >
                                <SettingsIcon className="size-6 text-primary" />
                            </div>
                            <div>
                                <h1
                                    className="text-xl font-semibold tracking-tight animate-in fade-in slide-in-from-bottom-2 duration-500 fill-mode-both"
                                    style={{ animationDelay: '100ms' }}
                                >
                                    Settings
                                </h1>
                                <p
                                    className="text-sm text-muted-foreground animate-in fade-in slide-in-from-bottom-2 duration-500 fill-mode-both"
                                    style={{ animationDelay: '150ms' }}
                                >
                                    Customize your Deep Researcher experience
                                </p>
                            </div>
                        </div>

                        <div
                            className="flex items-center gap-2 animate-in fade-in slide-in-from-right-4 duration-500 fill-mode-both"
                            style={{ animationDelay: '200ms' }}
                        >
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleResetDefaults}
                                className="gap-2"
                            >
                                <RotateCcw className="size-4" />
                                Reset to Defaults
                            </Button>
                            <Button
                                size="sm"
                                className="gap-2"
                            >
                                <Save className="size-4" />
                                Save Changes
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 overflow-y-auto w-full">
                <div className="w-full max-w-4xl mx-auto px-8 py-6 pb-24 space-y-6">

                    {/* Appearance Section */}
                    <SettingsSection
                        title="Appearance"
                        description="Customize how Deep Researcher looks"
                        icon={<Palette className="size-5 text-primary" />}
                        delay="250ms"
                    >
                        <SettingItem label="Theme" description="Select your preferred color scheme">
                            <Select value={theme} onValueChange={setTheme}>
                                <SelectTrigger className="w-[140px] bg-background">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="light">Light</SelectItem>
                                    <SelectItem value="dark">Dark</SelectItem>
                                    <SelectItem value="system">System</SelectItem>
                                </SelectContent>
                            </Select>
                        </SettingItem>
                        <SettingItem label="Reduce Motion" description="Minimize animations throughout the app">
                            <Switch checked={reducedMotion} onCheckedChange={setReducedMotion} />
                        </SettingItem>
                    </SettingsSection>

                    {/* Research Settings Section */}
                    <SettingsSection
                        title="Research"
                        description="Configure research and analysis behavior"
                        icon={<Globe className="size-5 text-primary" />}
                        delay="350ms"
                    >
                        <SettingItem label="Auto-save Research" description="Automatically save research progress">
                            <Switch checked={autoSave} onCheckedChange={setAutoSave} />
                        </SettingItem>
                        <SettingItem label="Max Search Depth" description="Maximum levels of nested searches">
                            <Select value={maxSearchDepth} onValueChange={setMaxSearchDepth}>
                                <SelectTrigger className="w-[100px] bg-background">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="1">1 Level</SelectItem>
                                    <SelectItem value="2">2 Levels</SelectItem>
                                    <SelectItem value="3">3 Levels</SelectItem>
                                    <SelectItem value="5">5 Levels</SelectItem>
                                </SelectContent>
                            </Select>
                        </SettingItem>
                        <SettingItem label="Default Report Format" description="Preferred format for generated reports">
                            <Select value={defaultReportFormat} onValueChange={setDefaultReportFormat}>
                                <SelectTrigger className="w-[140px] bg-background">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="markdown">Markdown</SelectItem>
                                    <SelectItem value="pdf">PDF</SelectItem>
                                    <SelectItem value="html">HTML</SelectItem>
                                </SelectContent>
                            </Select>
                        </SettingItem>
                    </SettingsSection>

                    {/* AI Settings Section */}
                    <SettingsSection
                        title="AI Behavior"
                        description="Control how the AI assistant operates"
                        icon={<Sparkles className="size-5 text-primary" />}
                        delay="450ms"
                    >
                        <SettingItem label="AI Personality" description="Choose the AI's communication style">
                            <Select value={aiPersonality} onValueChange={setAiPersonality}>
                                <SelectTrigger className="w-[160px] bg-background">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="professional">Professional</SelectItem>
                                    <SelectItem value="friendly">Friendly</SelectItem>
                                    <SelectItem value="concise">Concise</SelectItem>
                                    <SelectItem value="detailed">Detailed</SelectItem>
                                    <SelectItem value="creative">Creative</SelectItem>
                                </SelectContent>
                            </Select>
                        </SettingItem>
                        <div className="flex items-center justify-between gap-4">
                            <div className="flex-1">
                                <p className="text-sm font-medium text-foreground">Custom AI Prompt</p>
                                <p className="text-xs text-muted-foreground mt-0.5">Define custom instructions for the AI assistant</p>
                            </div>
                            <div className="shrink-0">
                                <PromptEditorModal
                                    value={customPrompt}
                                    onChange={setCustomPrompt}
                                />
                            </div>
                        </div>
                        <SettingItem label="Research Template" description="Select a predefined research approach">
                            <Select value={researchTemplate} onValueChange={setResearchTemplate}>
                                <SelectTrigger className="w-[180px] bg-background">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="comprehensive">Comprehensive</SelectItem>
                                    <SelectItem value="quick-summary">Quick Summary</SelectItem>
                                    <SelectItem value="academic">Academic</SelectItem>
                                    <SelectItem value="market-analysis">Market Analysis</SelectItem>
                                    <SelectItem value="technical-deep-dive">Technical Deep Dive</SelectItem>
                                    <SelectItem value="comparative">Comparative Study</SelectItem>
                                </SelectContent>
                            </Select>
                        </SettingItem>
                        <SettingItem label="Stream Responses" description="Show AI responses as they're generated">
                            <Switch checked={streamResponse} onCheckedChange={setStreamResponse} />
                        </SettingItem>
                        <SettingItem label="Show Source Citations" description="Display sources in AI responses">
                            <Switch checked={showSources} onCheckedChange={setShowSources} />
                        </SettingItem>
                        <SettingItem label="Detailed Analysis" description="Generate comprehensive, in-depth reports">
                            <Switch checked={detailedAnalysis} onCheckedChange={setDetailedAnalysis} />
                        </SettingItem>
                    </SettingsSection>

                    {/* Notifications Section */}
                    <SettingsSection
                        title="Notifications"
                        description="Manage your notification preferences"
                        icon={<Bell className="size-5 text-primary" />}
                        delay="550ms"
                    >
                        <SettingItem label="Research Complete" description="Notify when a research task finishes">
                            <Switch checked={researchComplete} onCheckedChange={setResearchComplete} />
                        </SettingItem>
                        <SettingItem label="Error Alerts" description="Show alerts when errors occur">
                            <Switch checked={errorAlerts} onCheckedChange={setErrorAlerts} />
                        </SettingItem>
                        <SettingItem label="Sound Effects" description="Play sounds for notifications">
                            <Switch checked={soundEnabled} onCheckedChange={setSoundEnabled} />
                        </SettingItem>
                    </SettingsSection>

                    {/* Data Settings Section */}
                    <SettingsSection
                        title="Data & Storage"
                        description="Manage your data and storage settings"
                        icon={<Database className="size-5 text-primary" />}
                        delay="650ms"
                    >
                        <SettingItem label="Auto Cleanup" description="Automatically remove old cached data">
                            <Switch checked={autoCleanup} onCheckedChange={setAutoCleanup} />
                        </SettingItem>
                        <SettingItem label="Data Retention" description="Keep research data for this many days">
                            <Select value={dataRetention} onValueChange={setDataRetention}>
                                <SelectTrigger className="w-[120px] bg-background">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="7">7 Days</SelectItem>
                                    <SelectItem value="14">14 Days</SelectItem>
                                    <SelectItem value="30">30 Days</SelectItem>
                                    <SelectItem value="90">90 Days</SelectItem>
                                    <SelectItem value="forever">Forever</SelectItem>
                                </SelectContent>
                            </Select>
                        </SettingItem>
                        <div className="pt-2">
                            <Button variant="outline" className="gap-2 text-muted-foreground hover:text-foreground">
                                Clear All Cached Data
                                <ChevronRight className="size-4" />
                            </Button>
                        </div>
                    </SettingsSection>

                    {/* About Section */}
                    <div
                        className="p-6 rounded-2xl bg-card border border-border/50 animate-in fade-in slide-in-from-bottom-4 duration-700 fill-mode-both"
                        style={{ animationDelay: '750ms' }}
                    >
                        <div className="flex items-center justify-between">
                            <div>
                                <h3 className="font-semibold text-foreground">Deep Researcher</h3>
                                <p className="text-sm text-muted-foreground">Version 2.0.0</p>
                            </div>
                            <Button variant="ghost" className="gap-2 text-muted-foreground hover:text-foreground">
                                View Licenses
                                <ChevronRight className="size-4" />
                            </Button>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    )
}

export default Settings
