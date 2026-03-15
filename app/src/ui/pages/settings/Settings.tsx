import { useState, useEffect, useRef, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
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
    User,
    Camera,
    Palette,
    Bell,
    Database,
    Globe,
    BrainCircuit,
    ChevronRight,
    Save,
    RotateCcw,
    Trash2,
    AlertTriangle,
    RefreshCw,
} from 'lucide-react'
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toast } from '@/components/ui/sonner'
import {
    HoverCard,
    HoverCardContent,
    HoverCardTrigger,
} from '@/components/ui/hover-card'
import { ResearchTemplateSelector } from '@/ui/components/ResearchTemplateSelector'
import { cn, getVersion } from '@/lib/utils'
import { useInternalLogo } from '@/ui/components/GetLogo'

// Settings Section Component
interface SettingsSectionProps {
    title: string
    description: string
    icon: React.ReactNode
    children: React.ReactNode
    delay: string
    className?: string
}

const SettingsSection = ({ title, description, icon, children, delay, className }: SettingsSectionProps) => (
    <div
        className={cn("p-6 rounded-2xl bg-background border border-border/50 space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-700 fill-mode-both", className)}
        style={{ animationDelay: delay }}
    >
        <div className="flex items-center gap-3">
            <div className="size-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center overflow-hidden">
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
    className?: string
}

const SettingItem = ({ label, description, children, className }: SettingItemProps) => (
    <div className={cn("flex items-center justify-between gap-4", className)}>
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
    // Profile Settings - Load from localStorage on initialization
    const [profileAvatar, setProfileAvatar] = useState(() => localStorage.getItem('dr_profile_avatar') || '')
    const [profileName, setProfileName] = useState(() => localStorage.getItem('dr_profile_name') || '')
    const [profileEmail, setProfileEmail] = useState(() => localStorage.getItem('dr_profile_email') || '')
    const [profileBio, setProfileBio] = useState(() => localStorage.getItem('dr_profile_bio') || '')
    const fileInputRef = useRef<HTMLInputElement>(null)

    // Appearance Settings
    const [theme, setTheme] = useState('system')

    // Research Settings
    const [maxSearchDepth, setMaxSearchDepth] = useState('3')
    const [defaultReportFormat, setDefaultReportFormat] = useState('markdown')

    // Notification Settings
    const [researchComplete, setResearchComplete] = useState(true)
    const [errorAlerts, setErrorAlerts] = useState(true)
    const [soundEnabled, setSoundEnabled] = useState(false)

    // Data Settings
    const [dataRetention, setDataRetention] = useState('30')

    // AI Settings
    const [researcherName, setResearcherName] = useState(() => localStorage.getItem('dr_researcher_name') || 'Alfred')
    const [aiPersonality, setAiPersonality] = useState('professional')
    const [customPrompt, setCustomPrompt] = useState('')
    const [researchTemplate, setResearchTemplate] = useState('comprehensive')
    const [streamResponse, setStreamResponse] = useState(true)
    const [showSources, setShowSources] = useState(true)

    // Danger Zone Logic
    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
    const [deleteType, setDeleteType] = useState<'all_data' | 'buckets' | 'reset_app' | null>(null)
    const [confirmCode, setConfirmCode] = useState('')
    const [userCodeInput, setUserCodeInput] = useState('')



    // Memoize handlers to prevent unnecessary re-renders
    const handleProfileNameChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        setProfileName(e.target.value)
    }, [])

    const handleProfileEmailChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        setProfileEmail(e.target.value)
    }, [])

    const handleResearcherNameChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        setResearcherName(e.target.value)
    }, [])

    const handleUserCodeInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        setUserCodeInput(e.target.value)
    }, [])

    // Save profile data to localStorage when changed (debounced)
    useEffect(() => {
        const timeoutId = setTimeout(() => {
            if (profileAvatar) localStorage.setItem('dr_profile_avatar', profileAvatar)
            else localStorage.removeItem('dr_profile_avatar')

            if (profileName) localStorage.setItem('dr_profile_name', profileName)
            else localStorage.removeItem('dr_profile_name')

            if (profileEmail) localStorage.setItem('dr_profile_email', profileEmail)
            else localStorage.removeItem('dr_profile_email')

            if (profileBio) localStorage.setItem('dr_profile_bio', profileBio)
            else localStorage.removeItem('dr_profile_bio')

            if (researcherName) localStorage.setItem('dr_researcher_name', researcherName)
            else localStorage.removeItem('dr_researcher_name')
        }, 1000) // Debounce for 1 second

        return () => clearTimeout(timeoutId)
    }, [profileAvatar, profileName, profileEmail, profileBio, researcherName])

    const handleAvatarClick = () => {
        fileInputRef.current?.click()
    }

    const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        // Validate file type
        if (!file.type.startsWith('image/')) {
            alert('Please select a valid image file')
            return
        }

        // Validate file size (2MB max)
        if (file.size > 2 * 1024 * 1024) {
            alert('Image size must be less than 2MB')
            return
        }

        // Convert to base64
        const reader = new FileReader()
        reader.onloadend = () => {
            setProfileAvatar(reader.result as string)
        }
        reader.readAsDataURL(file)
    }

    const handleResetDefaults = () => {
        // Reset profile
        setProfileAvatar('')
        setProfileName('')
        setProfileEmail('')
        setProfileBio('')
        localStorage.removeItem('dr_profile_avatar')
        localStorage.removeItem('dr_profile_name')
        localStorage.removeItem('dr_profile_email')
        localStorage.removeItem('dr_profile_bio')

        setResearcherName('Alfred')
        localStorage.removeItem('dr_researcher_name')

        // Reset other settings
        setTheme('system')
        setMaxSearchDepth('3')
        setDefaultReportFormat('markdown')
        setResearchComplete(true)
        setErrorAlerts(true)
        setSoundEnabled(false)
        setDataRetention('30')
        setAiPersonality('professional')
        setCustomPrompt('')
        setResearchTemplate('comprehensive')
        setStreamResponse(true)
        setShowSources(true)
    }

    const generateRandomCode = () => {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        let result = ''
        for (let i = 0; i < 8; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length))
        }
        return result
    }

    const initiateDelete = (type: 'all_data' | 'buckets' | 'reset_app') => {
        setDeleteType(type)
        setConfirmCode(generateRandomCode())
        setUserCodeInput('')
        setDeleteConfirmOpen(true)
    }

    const handleConfirmDelete = () => {
        if (userCodeInput !== confirmCode) return

        if (deleteType === 'all_data') {
            // Placeholder for Delete All Data API
            console.log('Deleting all data...')
            toast.success('All data deleted permanently')
        } else if (deleteType === 'buckets') {
            // Placeholder for Delete All Buckets API
            console.log('Deleting all buckets...')
            toast.success('All buckets and static assets deleted permanently')
        } else if (deleteType === 'reset_app') {
            // Placeholder for Reset App Logic
            console.log('Resetting application...')
            handleResetDefaults()
            toast.success('Application reset to default settings')
        }

        setDeleteConfirmOpen(false)
        setDeleteType(null)
    }

    const getDeleteDialogContent = () => {
        switch (deleteType) {
            case 'all_data':
                return {
                    title: 'Delete All Data',
                    description: 'This action cannot be undone. This will permanently delete your account and remove your data from our servers.',
                }
            case 'buckets':
                return {
                    title: 'Delete All Buckets',
                    description: 'This action cannot be undone. This will permanently delete all your buckets and the static assets stored on them.',
                }
            case 'reset_app':
                return {
                    title: 'Reset Application',
                    description: 'This will wipe out the entire app configuration and restore default settings. No personal data will be deleted.',
                }
            default:
                return { title: '', description: '' }
        }
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
                <div className="w-full max-w-7xl mx-auto px-8 py-6 pb-24 space-y-6">

                    {/* Profile Section */}
                    <SettingsSection
                        title="Profile"
                        description={`Personalize your experience and help ${researcherName} understand you better`}
                        icon={<User className="size-5 text-primary" />}
                        delay="150ms"
                    >
                        <div className="flex flex-col md:flex-row gap-6">
                            {/* Avatar Upload */}
                            <div className="flex flex-col items-center gap-3">
                                <div
                                    className="group/avatar relative size-20 rounded-full overflow-hidden border-2 border-border/50 bg-muted cursor-pointer transition-all hover:border-primary/50"
                                    onClick={handleAvatarClick}
                                >
                                    {profileAvatar ? (
                                        <img
                                            src={profileAvatar}
                                            alt="Profile avatar"
                                            className="w-full h-full object-cover"
                                        />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center bg-primary/10">
                                            <User className="size-10 text-primary/50" />
                                        </div>
                                    )}
                                    {/* Hover Overlay */}
                                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover/avatar:opacity-100 transition-opacity flex items-center justify-center">
                                        <Camera className="size-6 text-white" />
                                    </div>
                                </div>
                                <p className="text-xs text-muted-foreground text-center">Click to upload</p>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept="image/*"
                                    onChange={handleAvatarChange}
                                    className="hidden"
                                />
                            </div>

                            {/* Profile Fields */}
                            <div className="flex-1 space-y-4">
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-foreground">Name</label>
                                    <Input
                                        value={profileName}
                                        onChange={handleProfileNameChange}
                                        placeholder="Enter your name"
                                        className="bg-background"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm font-medium text-foreground">Email</label>
                                    <Input
                                        type="email"
                                        value={profileEmail}
                                        onChange={handleProfileEmailChange}
                                        placeholder="your.email@example.com"
                                        className="bg-background"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <label className="text-sm font-medium text-foreground">Bio</label>
                                        <span className="text-xs text-muted-foreground">
                                            {profileBio.length}/300
                                        </span>
                                    </div>
                                    <Textarea
                                        value={profileBio}
                                        onChange={(e) => {
                                            if (e.target.value.length <= 300) {
                                                setProfileBio(e.target.value)
                                            }
                                        }}
                                        placeholder="Tell the AI about yourself, your preferences, and interests..."
                                        className="bg-background min-h-[100px] resize-none"
                                        maxLength={300}
                                    />
                                    <p className="text-xs text-muted-foreground">Help {researcherName} tailor responses to your preferences</p>
                                </div>
                            </div>
                        </div>
                    </SettingsSection>

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
                    </SettingsSection>

                    {/* Research Settings Section */}
                    <SettingsSection
                        title="Research"
                        description="Configure research and analysis behavior"
                        icon={<Globe className="size-5 text-primary" />}
                        delay="350ms"
                    >
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
                        title={`${researcherName} Behavior`}
                        description={`Control how ${researcherName} operates`}
                        icon={<BrainCircuit className="size-5 text-primary" />}
                        delay="450ms"
                    >
                        <SettingItem label="Researcher Name" description="Give your AI assistant a familiar name">
                            <Input
                                value={researcherName}
                                onChange={handleResearcherNameChange}
                                placeholder="Alfred"
                                className="w-[200px] bg-background"
                            />
                        </SettingItem>
                        <SettingItem label={`${researcherName} Personality`} description={`Choose ${researcherName}'s communication style`}>
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
                                <p className="text-sm font-medium text-foreground">Custom {researcherName} Prompt</p>
                                <p className="text-xs text-muted-foreground mt-0.5">Define custom instructions for the assistant</p>
                            </div>
                            <div className="shrink-0">
                                <PromptEditorModal
                                    value={customPrompt}
                                    onChange={setCustomPrompt}
                                />
                            </div>
                        </div>
                        <SettingItem label="Research Template" description="Select a predefined research approach" className="gap-0">
                            <ResearchTemplateSelector
                                value={researchTemplate}
                                onChange={setResearchTemplate}
                                className="w-fit"
                            />
                        </SettingItem>
                        <SettingItem label="Stream Responses" description={`Show ${researcherName} responses as they're generated`}>
                            <Switch checked={streamResponse} onCheckedChange={setStreamResponse} />
                        </SettingItem>
                        <SettingItem label="Show Source Citations" description={`Display sources in ${researcherName} responses`}>
                            <Switch checked={showSources} onCheckedChange={setShowSources} />
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

                    {/* Danger Zone Section */}
                    <SettingsSection
                        title="Danger Zone"
                        description="Irreversible actions for data management"
                        icon={<AlertTriangle className="size-5 text-destructive" />}
                        delay="700ms"
                        className="border-destructive/20"
                    >
                        <div className="space-y-4">
                            <SettingItem label="Delete All Data" description="Permanently remove all your account data">
                                <Button
                                    variant="destructive"
                                    onClick={() => initiateDelete('all_data')}
                                    className="gap-2"
                                >
                                    <Trash2 className="size-4" />
                                    Delete Data
                                </Button>
                            </SettingItem>
                            <Separator className="bg-border/50" />
                            <SettingItem label="Delete All Buckets" description="Remove all storage buckets and assets">
                                <Button
                                    variant="destructive"
                                    onClick={() => initiateDelete('buckets')}
                                    className="gap-2"
                                >
                                    <Database className="size-4" />
                                    Delete Buckets
                                </Button>
                            </SettingItem>
                            <Separator className="bg-border/50" />
                            <SettingItem label="Reset Application" description="Restore app to default state (keeps data)">
                                <Button
                                    variant="outline"
                                    onClick={() => initiateDelete('reset_app')}
                                    className="gap-2 border-destructive/50 text-destructive hover:bg-destructive/10 hover:text-destructive"
                                >
                                    <RefreshCw className="size-4" />
                                    Reset App
                                </Button>
                            </SettingItem>
                        </div>
                    </SettingsSection>

                    {/* About Section */}
                    <SettingsSection
                        title="About Deep Researcher"
                        description="App Information & Credits"
                        icon={<img src={useInternalLogo()} alt="Logo" className="h-full w-full p-1 rounded-lg" />}
                        delay="750ms"
                        className='border-4 border-accent'

                    >

                        <div className="flex flex-col gap-4">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-foreground">Authors</span>
                                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                                    <span>pixelThreader &</span>
                                    <HoverCard>
                                        <HoverCardTrigger asChild>
                                            <span className="underline decoration-dotted underline-offset-4 cursor-pointer hover:text-foreground transition-colors">Team</span>
                                        </HoverCardTrigger>
                                        <HoverCardContent className="w-auto p-3">
                                            <div className="flex flex-col gap-1">
                                                <p className="text-xs font-semibold text-foreground mb-1">The Team</p>
                                                <div className="text-sm text-muted-foreground grid grid-cols-2 gap-x-4 gap-y-1">
                                                    <span>Asif</span>
                                                    <span>Aman</span>
                                                    <span>Pramod</span>
                                                    <span>Ronit</span>
                                                </div>
                                            </div>
                                        </HoverCardContent>
                                    </HoverCard>
                                </div>
                            </div>

                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-foreground">App Version</span>
                                <span className="text-sm text-muted-foreground">v{getVersion()}</span>
                            </div>

                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-foreground">Last Updated</span>
                                <span className="text-sm text-muted-foreground">February 10, 2026</span>
                            </div>
                        </div>
                    </SettingsSection>

                </div>
            </div>

            <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>{getDeleteDialogContent().title}</AlertDialogTitle>
                        <AlertDialogDescription>
                            {getDeleteDialogContent().description}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <div className="py-4 space-y-4">
                        <div className="p-3 bg-muted/50 rounded-lg border border-border/50">
                            <p className="text-sm text-center text-muted-foreground">
                                To confirm, type <span className="font-mono font-bold text-foreground select-all">{confirmCode}</span> below:
                            </p>
                        </div>
                        <Input
                            value={userCodeInput}
                            onChange={handleUserCodeInputChange}
                            placeholder="Enter confirmation code"
                            className="text-center font-mono tracking-widest uppercase"
                        />
                    </div>
                    <AlertDialogFooter>
                        <AlertDialogCancel onClick={() => setDeleteConfirmOpen(false)}>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={handleConfirmDelete}
                            disabled={userCodeInput !== confirmCode}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            Confirm Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    )
}

export default Settings
