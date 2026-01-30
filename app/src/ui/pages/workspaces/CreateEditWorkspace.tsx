import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import {
  Briefcase,
  TrendingUp,
  Users,
  Zap,
  BookOpen,
  Target,
  Rocket,
  Brain,
  Sparkles,
  Globe,
  Database,
  Code,
  Cpu,
  Network,
  FileText,
  MessageSquare,
  Upload,
  X,
  ChevronLeft,
  ChevronRight,
  Check,
  LucideIcon,
  Palette,
  Image as ImageIcon,
  Bot,
  Settings2,
} from 'lucide-react'

// Icons available for workspace
const WORKSPACE_ICONS = [
  { icon: Briefcase, name: 'Briefcase', color: 'text-blue-400' },
  { icon: TrendingUp, name: 'Trending Up', color: 'text-green-400' },
  { icon: Users, name: 'Users', color: 'text-purple-400' },
  { icon: Zap, name: 'Zap', color: 'text-yellow-400' },
  { icon: BookOpen, name: 'Book', color: 'text-pink-400' },
  { icon: Target, name: 'Target', color: 'text-red-400' },
  { icon: Rocket, name: 'Rocket', color: 'text-orange-400' },
  { icon: Brain, name: 'Brain', color: 'text-indigo-400' },
  { icon: Sparkles, name: 'Sparkles', color: 'text-cyan-400' },
  { icon: Globe, name: 'Globe', color: 'text-teal-400' },
  { icon: Database, name: 'Database', color: 'text-emerald-400' },
  { icon: Code, name: 'Code', color: 'text-violet-400' },
  { icon: Cpu, name: 'CPU', color: 'text-blue-500' },
  { icon: Network, name: 'Network', color: 'text-green-500' },
  { icon: FileText, name: 'Document', color: 'text-amber-400' },
  { icon: MessageSquare, name: 'Chat', color: 'text-rose-400' },
]

// Color palette for accent colors
const ACCENT_COLORS = [
  { name: 'Blue', class: 'text-blue-400', bg: 'bg-blue-400' },
  { name: 'Green', class: 'text-green-400', bg: 'bg-green-400' },
  { name: 'Purple', class: 'text-purple-400', bg: 'bg-purple-400' },
  { name: 'Pink', class: 'text-pink-400', bg: 'bg-pink-400' },
  { name: 'Yellow', class: 'text-yellow-400', bg: 'bg-yellow-400' },
  { name: 'Red', class: 'text-red-400', bg: 'bg-red-400' },
  { name: 'Orange', class: 'text-orange-400', bg: 'bg-orange-400' },
  { name: 'Indigo', class: 'text-indigo-400', bg: 'bg-indigo-400' },
  { name: 'Cyan', class: 'text-cyan-400', bg: 'bg-cyan-400' },
  { name: 'Teal', class: 'text-teal-400', bg: 'bg-teal-400' },
  { name: 'Emerald', class: 'text-emerald-400', bg: 'bg-emerald-400' },
  { name: 'Violet', class: 'text-violet-400', bg: 'bg-violet-400' },
]

// AI Modes
const AI_MODES = [
  {
    id: 'auto',
    title: 'Auto',
    description: 'Intelligently switches between online and offline models based on availability and context.',
    icon: Sparkles,
  },
  {
    id: 'offline',
    title: 'Offline',
    description: 'Uses only local models for privacy and offline operation.',
    icon: Cpu,
  },
  {
    id: 'online',
    title: 'Online',
    description: 'Leverages cloud-based models for maximum capability and performance.',
    icon: Globe,
  },
]

interface WorkspaceFormData {
  name: string
  description: string
  icon: { icon: LucideIcon; name: string; color: string } | null
  accentColor: { name: string; class: string; bg: string } | null
  bannerImage: File | null
  aiMode: string
  resources: File[]
  enableResearch: boolean
  enableChat: boolean
}

const CreateEditWorkspace = () => {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState<WorkspaceFormData>({
    name: '',
    description: '',
    icon: null,
    accentColor: null,
    bannerImage: null,
    aiMode: 'auto',
    resources: [],
    enableResearch: true,
    enableChat: true,
  })

  const totalSteps = 4

  // Form validation
  const isStep1Valid = formData.name.trim().length > 0 && formData.description.trim().length > 0
  const isStep2Valid = formData.icon !== null && formData.accentColor !== null
  const isStep3Valid = true // AI mode has default
  const isStep4Valid = true // All fields optional

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return isStep1Valid
      case 2:
        return isStep2Valid
      case 3:
        return isStep3Valid
      case 4:
        return isStep4Valid
      default:
        return false
    }
  }

  const handleNext = () => {
    if (currentStep < totalSteps && canProceed()) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSubmit = () => {
    console.log('Workspace Data:', formData)
    // TODO: Save workspace to backend
    navigate('/workspaces/all')
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files)
      setFormData({ ...formData, resources: [...formData.resources, ...newFiles] })
    }
  }

  const removeFile = (index: number) => {
    const newResources = formData.resources.filter((_, i) => i !== index)
    setFormData({ ...formData, resources: newResources })
  }

  const handleBannerUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFormData({ ...formData, bannerImage: e.target.files[0] })
    }
  }

  return (
    <div className="p-8 space-y-8 h-full text-foreground overflow-y-auto animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Create New Workspace</h1>
        <p className="text-muted-foreground">Set up your research environment in a few simple steps.</p>
      </div>

      {/* Progress Indicator */}
      <div className="flex items-center justify-center gap-2 max-w-2xl mx-auto">
        {Array.from({ length: totalSteps }).map((_, index) => {
          const stepNumber = index + 1
          const isActive = stepNumber === currentStep
          const isCompleted = stepNumber < currentStep

          return (
            <div key={stepNumber} className="flex items-center flex-1">
              <div
                className={`flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all ${isCompleted
                    ? 'bg-primary border-primary text-primary-foreground'
                    : isActive
                      ? 'border-primary text-primary'
                      : 'border-muted-foreground/30 text-muted-foreground'
                  }`}
              >
                {isCompleted ? <Check className="w-5 h-5" /> : stepNumber}
              </div>
              {stepNumber < totalSteps && (
                <div
                  className={`flex-1 h-1 mx-2 rounded-full transition-all ${isCompleted ? 'bg-primary' : 'bg-muted-foreground/20'
                    }`}
                />
              )}
            </div>
          )
        })}
      </div>

      {/* Step Content */}
      <div className="max-w-4xl mx-auto">
        {currentStep === 1 && (
          <Card className="border-muted-foreground/20 animate-in fade-in slide-in-from-right-4 duration-300">
            <CardHeader>
              <CardTitle className="text-2xl">Basic Information</CardTitle>
              <CardDescription>Give your workspace a name and description</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <label htmlFor="workspace-name" className="text-sm font-medium">
                  Workspace Name <span className="text-destructive">*</span>
                </label>
                <Input
                  id="workspace-name"
                  placeholder="e.g., Market Analysis 2024"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  maxLength={50}
                  className="text-base"
                />
                <p className="text-xs text-muted-foreground text-right">{formData.name.length}/50</p>
              </div>

              <div className="space-y-2">
                <label htmlFor="workspace-description" className="text-sm font-medium">
                  Short Description <span className="text-destructive">*</span>
                </label>
                <textarea
                  id="workspace-description"
                  placeholder="Briefly describe what this workspace is for..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  maxLength={150}
                  rows={4}
                  className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] resize-none"
                />
                <p className="text-xs text-muted-foreground text-right">{formData.description.length}/150</p>
              </div>
            </CardContent>
          </Card>
        )}

        {currentStep === 2 && (
          <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
            {/* Icon Selection */}
            <Card className="border-muted-foreground/20">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <Palette className="w-6 h-6 text-primary" />
                  <div>
                    <CardTitle className="text-2xl">Choose an Icon</CardTitle>
                    <CardDescription>Select an icon to represent your workspace</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-3">
                  {WORKSPACE_ICONS.map((item) => {
                    const Icon = item.icon
                    const isSelected = formData.icon?.name === item.name
                    return (
                      <button
                        key={item.name}
                        onClick={() => setFormData({ ...formData, icon: item })}
                        className={`p-4 rounded-lg border-2 transition-all hover:scale-105 ${isSelected
                            ? 'border-primary bg-primary/10 shadow-md'
                            : 'border-muted-foreground/20 bg-muted/10 hover:border-primary/50'
                          }`}
                      >
                        <Icon className={`w-8 h-8 mx-auto ${item.color}`} />
                      </button>
                    )
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Color Selection */}
            <Card className="border-muted-foreground/20">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <Palette className="w-6 h-6 text-primary" />
                  <div>
                    <CardTitle className="text-2xl">Accent Color</CardTitle>
                    <CardDescription>Choose a color theme for your workspace</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-6 sm:grid-cols-8 md:grid-cols-12 gap-3">
                  {ACCENT_COLORS.map((color) => {
                    const isSelected = formData.accentColor?.name === color.name
                    return (
                      <button
                        key={color.name}
                        onClick={() => setFormData({ ...formData, accentColor: color })}
                        className={`relative p-0 rounded-lg border-2 transition-all hover:scale-105 aspect-square ${isSelected ? 'border-primary shadow-lg' : 'border-muted-foreground/20'
                          }`}
                      >
                        <div className={`w-full h-full rounded-md ${color.bg}`}>
                          {isSelected && (
                            <div className="absolute inset-0 flex items-center justify-center">
                              <Check className="w-5 h-5 text-white drop-shadow-lg" />
                            </div>
                          )}
                        </div>
                      </button>
                    )
                  })}
                </div>
              </CardContent>
            </Card>

            {/* Banner Upload (Optional) */}
            <Card className="border-muted-foreground/20">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <ImageIcon className="w-6 h-6 text-primary" />
                  <div>
                    <CardTitle className="text-2xl">Banner Image</CardTitle>
                    <CardDescription>Optional: Add a custom banner image</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <label
                    htmlFor="banner-upload"
                    className="flex flex-col items-center justify-center w-full h-40 border-2 border-dashed border-muted-foreground/30 rounded-lg cursor-pointer hover:border-primary/50 hover:bg-muted/30 transition-all"
                  >
                    {formData.bannerImage ? (
                      <div className="text-center space-y-2">
                        <ImageIcon className="w-12 h-12 mx-auto text-primary" />
                        <p className="text-sm font-medium">{formData.bannerImage.name}</p>
                        <p className="text-xs text-muted-foreground">Click to change</p>
                      </div>
                    ) : (
                      <div className="text-center space-y-2">
                        <Upload className="w-12 h-12 mx-auto text-muted-foreground" />
                        <p className="text-sm font-medium">Click to upload banner</p>
                        <p className="text-xs text-muted-foreground">PNG, JPG up to 5MB</p>
                      </div>
                    )}
                    <input
                      id="banner-upload"
                      type="file"
                      className="hidden"
                      accept="image/*"
                      onChange={handleBannerUpload}
                    />
                  </label>
                </div>
              </CardContent>
            </Card>

            {/* Preview */}
            {formData.icon && formData.accentColor && (
              <Card className="border-primary/30 bg-primary/5">
                <CardHeader>
                  <CardTitle className="text-lg">Preview</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 p-4 rounded-lg bg-background border border-muted-foreground/20">
                    <div className={`p-3 rounded-lg bg-secondary/30 ${formData.accentColor.class}`}>
                      <formData.icon.icon className="w-6 h-6" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-lg">{formData.name || 'Workspace Name'}</h3>
                      <p className="text-sm text-muted-foreground">
                        {formData.description || 'Workspace description'}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {currentStep === 3 && (
          <Card className="border-muted-foreground/20 animate-in fade-in slide-in-from-right-4 duration-300">
            <CardHeader>
              <div className="flex items-center gap-3">
                <Bot className="w-6 h-6 text-primary" />
                <div>
                  <CardTitle className="text-2xl">AI Configuration</CardTitle>
                  <CardDescription>Choose how AI models should operate in this workspace</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {AI_MODES.map((mode) => {
                  const Icon = mode.icon
                  const isSelected = formData.aiMode === mode.id
                  return (
                    <button
                      key={mode.id}
                      onClick={() => setFormData({ ...formData, aiMode: mode.id })}
                      className={`p-6 rounded-xl border-2 text-left transition-all hover:scale-105 ${isSelected
                          ? 'border-primary bg-primary/10 shadow-lg'
                          : 'border-muted-foreground/20 bg-muted/5 hover:border-primary/50 hover:bg-muted/20'
                        }`}
                    >
                      <Icon
                        className={`w-10 h-10 mb-4 ${isSelected ? 'text-primary' : 'text-muted-foreground'}`}
                      />
                      <h3 className="font-semibold text-lg mb-2">{mode.title}</h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">{mode.description}</p>
                      {isSelected && (
                        <div className="mt-4 flex items-center gap-2 text-primary text-sm font-medium">
                          <Check className="w-4 h-4" />
                          Selected
                        </div>
                      )}
                    </button>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {currentStep === 4 && (
          <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
            {/* Resources Upload */}
            <Card className="border-muted-foreground/20">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <Upload className="w-6 h-6 text-primary" />
                  <div>
                    <CardTitle className="text-2xl">Add Resources</CardTitle>
                    <CardDescription>
                      Upload PDF, Word docs, Excel files, or paste URLs (optional)
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <label
                  htmlFor="resource-upload"
                  className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-muted-foreground/30 rounded-lg cursor-pointer hover:border-primary/50 hover:bg-muted/30 transition-all"
                >
                  <Upload className="w-10 h-10 mb-2 text-muted-foreground" />
                  <p className="text-sm font-medium">Click to upload or drag and drop</p>
                  <p className="text-xs text-muted-foreground">PDF, DOC, DOCX, XLS, XLSX</p>
                  <input
                    id="resource-upload"
                    type="file"
                    className="hidden"
                    multiple
                    accept=".pdf,.doc,.docx,.xls,.xlsx"
                    onChange={handleFileUpload}
                  />
                </label>

                {/* Uploaded Files List */}
                {formData.resources.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-muted-foreground">Uploaded Files</h4>
                    <div className="space-y-2">
                      {formData.resources.map((file, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-muted-foreground/20"
                        >
                          <div className="flex items-center gap-3">
                            <FileText className="w-5 h-5 text-primary" />
                            <div>
                              <p className="text-sm font-medium">{file.name}</p>
                              <p className="text-xs text-muted-foreground">
                                {(file.size / 1024).toFixed(1)} KB
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => removeFile(index)}
                            className="p-1 rounded-md hover:bg-destructive/10 transition-colors"
                          >
                            <X className="w-4 h-4 text-destructive" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Agent Toggles */}
            <Card className="border-muted-foreground/20">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <Settings2 className="w-6 h-6 text-primary" />
                  <div>
                    <CardTitle className="text-2xl">Enable Agents</CardTitle>
                    <CardDescription>Choose which AI agents can operate in this workspace</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-lg bg-muted/20 border border-muted-foreground/20">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <FileText className="w-5 h-5 text-primary" />
                      <h4 className="font-medium">Research Agents</h4>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Enable autonomous research and information gathering
                    </p>
                  </div>
                  <button
                    onClick={() => setFormData({ ...formData, enableResearch: !formData.enableResearch })}
                    className={`relative w-14 h-7 rounded-full transition-colors ${formData.enableResearch ? 'bg-primary' : 'bg-muted-foreground/30'
                      }`}
                  >
                    <div
                      className={`absolute top-1 w-5 h-5 rounded-full bg-white shadow-md transition-transform ${formData.enableResearch ? 'translate-x-8' : 'translate-x-1'
                        }`}
                    />
                  </button>
                </div>

                <div className="flex items-center justify-between p-4 rounded-lg bg-muted/20 border border-muted-foreground/20">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <MessageSquare className="w-5 h-5 text-primary" />
                      <h4 className="font-medium">Chat Agents</h4>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Enable conversational AI for interactive discussions
                    </p>
                  </div>
                  <button
                    onClick={() => setFormData({ ...formData, enableChat: !formData.enableChat })}
                    className={`relative w-14 h-7 rounded-full transition-colors ${formData.enableChat ? 'bg-primary' : 'bg-muted-foreground/30'
                      }`}
                  >
                    <div
                      className={`absolute top-1 w-5 h-5 rounded-full bg-white shadow-md transition-transform ${formData.enableChat ? 'translate-x-8' : 'translate-x-1'
                        }`}
                    />
                  </button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {/* Navigation Buttons */}
      <div className="max-w-4xl mx-auto">
        <Separator className="mb-6" />
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={handlePrevious}
            disabled={currentStep === 1}
            className="gap-2"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous
          </Button>

          {currentStep < totalSteps ? (
            <Button onClick={handleNext} disabled={!canProceed()} className="gap-2">
              Next
              <ChevronRight className="w-4 h-4" />
            </Button>
          ) : (
            <Button onClick={handleSubmit} className="gap-2 bg-primary hover:bg-primary/90">
              <Check className="w-4 h-4" />
              Create Workspace
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

export default CreateEditWorkspace