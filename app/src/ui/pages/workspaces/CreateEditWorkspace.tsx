import { useState, useEffect, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
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
  FolderPlus,
} from "lucide-react";
import {
  createBucket,
  createWorkspace,
  updateWorkspace,
  getWorkspaceRecord,
  listBuckets,
  listWorkspaceRecords,
  uploadWorkspaceBanner,
  uploadWorkspaceIcon,
  type BucketRecord,
  type WorkspaceRecord,
} from "@/lib/apis";
import CreateBucketModal from "@/components/modals/CreateBucketModal";
import {
  Search,
  Plus,
  Loader2,
  Info
} from "lucide-react";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from "@/components/ui/tooltip";
import { toast } from "@/components/ui/sonner";
import { resolveApiAssetUrl } from "@/lib/utils";
import {
  formatBucketAllowedTypes,
  getBucketAllowedTypeLabel,
  serializeBucketAllowedTypes,
  getAcceptExtensionsForBucketTypes,
  validateFilesAgainstBucket,
  type BucketAllowedType,
} from "@/lib/bucket-types";

// Icons available for workspace
const WORKSPACE_ICONS = [
  { icon: Briefcase, name: "Briefcase", color: "text-blue-400" },
  { icon: TrendingUp, name: "Trending Up", color: "text-green-400" },
  { icon: Users, name: "Users", color: "text-purple-400" },
  { icon: Zap, name: "Zap", color: "text-yellow-400" },
  { icon: BookOpen, name: "Book", color: "text-pink-400" },
  { icon: Target, name: "Target", color: "text-red-400" },
  { icon: Rocket, name: "Rocket", color: "text-orange-400" },
  { icon: Brain, name: "Brain", color: "text-indigo-400" },
  { icon: Sparkles, name: "Sparkles", color: "text-cyan-400" },
  { icon: Globe, name: "Globe", color: "text-teal-400" },
  { icon: Database, name: "Database", color: "text-emerald-400" },
  { icon: Code, name: "Code", color: "text-violet-400" },
  { icon: Cpu, name: "CPU", color: "text-blue-500" },
  { icon: Network, name: "Network", color: "text-green-500" },
  { icon: FileText, name: "Document", color: "text-amber-400" },
  { icon: MessageSquare, name: "Chat", color: "text-rose-400" },
];

// Color palette for accent colors
const ACCENT_COLORS = [
  { name: "Blue", hex: "#60A5FA", class: "text-blue-400", bg: "bg-blue-400" },
  { name: "Green", hex: "#4ADE80", class: "text-green-400", bg: "bg-green-400" },
  { name: "Purple", hex: "#C084FC", class: "text-purple-400", bg: "bg-purple-400" },
  { name: "Pink", hex: "#F472B6", class: "text-pink-400", bg: "bg-pink-400" },
  { name: "Yellow", hex: "#FACC15", class: "text-yellow-400", bg: "bg-yellow-400" },
  { name: "Red", hex: "#F87171", class: "text-red-400", bg: "bg-red-400" },
  { name: "Orange", hex: "#FB923C", class: "text-orange-400", bg: "bg-orange-400" },
  { name: "Indigo", hex: "#818CF8", class: "text-indigo-400", bg: "bg-indigo-400" },
  { name: "Cyan", hex: "#22D3EE", class: "text-cyan-400", bg: "bg-cyan-400" },
  { name: "Teal", hex: "#2DD4BF", class: "text-teal-400", bg: "bg-teal-400" },
  { name: "Emerald", hex: "#34D399", class: "text-emerald-400", bg: "bg-emerald-400" },
  { name: "Violet", hex: "#A78BFA", class: "text-violet-400", bg: "bg-violet-400" },
];

// AI Modes
const AI_MODES = [
  {
    id: "auto",
    title: "Auto",
    description:
      "Intelligently switches between online and offline models based on availability and context.",
    icon: Sparkles,
  },
  {
    id: "offline",
    title: "Offline",
    description: "Uses only local models for privacy and offline operation.",
    icon: Cpu,
  },
  {
    id: "online",
    title: "Online",
    description:
      "Leverages cloud-based models for maximum capability and performance.",
    icon: Globe,
  },
];

interface WorkspaceFormData {
  name: string;
  description: string;
  icon: { icon: LucideIcon; name: string; color: string } | null;
  accentColor: { name: string; hex: string; class: string; bg: string } | null;
  bannerImage: File | null;
  aiMode: "auto" | "offline" | "local" | "online";
  resources: File[];
  enableResearch: boolean;
  enableChat: boolean;
  bucket: string;
  customIcon: File | null;
}

interface BucketOption {
  id: string;
  name: string;
  description: string | null;
  allowedFileTypes: string;
  totalSize: number;
  totalFiles: number;
}

const DEFAULT_CREATED_BY = "local-user";

const formatBytes = (bytes: number): string => {
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
};

const toBucketOption = (bucket: BucketRecord): BucketOption => ({
  id: bucket.id,
  name: bucket.name,
  description: bucket.description,
  allowedFileTypes: bucket.allowed_file_types,
  totalSize: bucket.total_size,
  totalFiles: bucket.total_files,
});

const isWorkspaceAssetPath = (value?: string | null) =>
  Boolean(value && (value.includes("/") || /^https?:\/\//i.test(value)));

const normalizeWorkspaceValue = (value?: string | null) =>
  (value ?? "").toLowerCase().replace(/[^a-z0-9]/g, "");

const normalizeHexColor = (value?: string | null): string | null => {
  if (!value) return null;
  const trimmed = value.trim();

  const fullHex = trimmed.match(/^#([0-9a-fA-F]{6})([0-9a-fA-F]{2})?$/);
  if (fullHex) {
    return `#${fullHex[1].toUpperCase()}`;
  }

  const shortHex = trimmed.match(/^#([0-9a-fA-F]{3,4})$/);
  if (shortHex) {
    const rgb = shortHex[1].slice(0, 3);
    const expanded = rgb.split("").map((c) => `${c}${c}`).join("").toUpperCase();
    return `#${expanded}`;
  }

  return null;
};

const CreateEditWorkspace = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const isEditMode = Boolean(id);
  const [isLoadingWorkspace, setIsLoadingWorkspace] = useState(false);
  const [existingWorkspace, setExistingWorkspace] = useState<WorkspaceRecord | null>(null);
  const [currentStep, setCurrentStep] = useState(1);
  const [isSaving, setIsSaving] = useState(false);
  const [formData, setFormData] = useState<WorkspaceFormData>({
    name: "",
    description: "",
    icon: null,
    accentColor: null,
    bannerImage: null,
    aiMode: "auto",
    resources: [] as File[],
    enableResearch: true,
    enableChat: true,
    bucket: "",
    customIcon: null,
  });

  const [iconPreview, setIconPreview] = useState<string | null>(null);
  const [bannerPreview, setBannerPreview] = useState<string | null>(null);

  const [buckets, setBuckets] = useState<BucketOption[]>([]);
  const [isLoadingStorage, setIsLoadingStorage] = useState(false);
  const [bucketSearch, setBucketSearch] = useState("");
  const [isBucketModalOpen, setIsBucketModalOpen] = useState(false);
  const [connectedWorkspaceNames, setConnectedWorkspaceNames] = useState<string[]>([]);
  const [isLoadingConnectedWorkspaces, setIsLoadingConnectedWorkspaces] = useState(false);

  const selectedBucket = buckets.find((bucket) => bucket.id === formData.bucket) ?? null;

  // Load existing workspace data when in edit mode
  useEffect(() => {
    if (!id) return;
    setIsLoadingWorkspace(true);
    getWorkspaceRecord(id)
      .then((ws) => {
        setExistingWorkspace(ws);
        const iconMatch =
          WORKSPACE_ICONS.find(
            (item) =>
              normalizeWorkspaceValue(item.name) ===
              normalizeWorkspaceValue(ws.icon),
          ) ?? null;
        const colorMatch =
          ACCENT_COLORS.find(
            (c) =>
              c.hex.toLowerCase() === (normalizeHexColor(ws.accent_clr) ?? "").toLowerCase() ||
              normalizeWorkspaceValue(c.name) ===
              normalizeWorkspaceValue(ws.accent_clr),
          ) ??
          ACCENT_COLORS[0];
        const aiMode =
          ws.ai_config === "local" ? "offline" : (ws.ai_config ?? "auto");

        if (ws.banner_img) {
          setBannerPreview(resolveApiAssetUrl(ws.banner_img));
        }

        if (isWorkspaceAssetPath(ws.icon)) {
          setIconPreview(resolveApiAssetUrl(ws.icon));
        } else {
          setIconPreview(null);
        }

        setFormData((prev) => ({
          ...prev,
          name: ws.name,
          description: ws.desc ?? "",
          icon: iconMatch,
          accentColor: colorMatch,
          aiMode,
          enableResearch: ws.workspace_research_agents,
          enableChat: ws.workspace_chat_agents,
          bucket: ws.connected_bucket_id ?? "",
          bannerImage: null,
          customIcon: null,
        }));
      })
      .catch((err) => {
        console.error("Failed to load workspace for editing:", err);
        toast.error(err instanceof Error ? err.message : "Failed to load workspace");
      })
      .finally(() => {
        setIsLoadingWorkspace(false);
      });
  }, [id]);

  const loadStorageData = useCallback(async () => {
    setIsLoadingStorage(true);
    try {
      const response = await listBuckets({
        page: 1,
        size: 200,
        sortBy: "updated_at",
        sortOrder: "desc",
      });

      const bucketOptions = response.items.map(toBucketOption);

      setBuckets(bucketOptions);

      if (!formData.bucket && bucketOptions.length > 0) {
        setFormData((prev) => ({ ...prev, bucket: bucketOptions[0].id }));
      }
    } catch (err) {
      console.error("Failed to load storage data", err);
    } finally {
      setIsLoadingStorage(false);
    }
  }, [formData.bucket]);

  useEffect(() => {
    if (currentStep === 3) {
      loadStorageData();
    }
  }, [currentStep, loadStorageData]);

  useEffect(() => {
    if (currentStep !== 3 || !formData.bucket) {
      setConnectedWorkspaceNames([]);
      return;
    }

    let isCancelled = false;
    setIsLoadingConnectedWorkspaces(true);

    listWorkspaceRecords({
      page: 1,
      size: 200,
      connectedBucketId: formData.bucket,
      sortBy: "updated_at",
      sortOrder: "desc",
    })
      .then((workspaces) => {
        if (isCancelled) return;
        setConnectedWorkspaceNames(
          workspaces
            .map((workspace) => workspace.name)
            .filter((name): name is string => name.trim().length > 0),
        );
      })
      .catch((err) => {
        if (isCancelled) return;
        console.error("Failed to load connected workspaces", err);
        setConnectedWorkspaceNames([]);
      })
      .finally(() => {
        if (isCancelled) return;
        setIsLoadingConnectedWorkspaces(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [currentStep, formData.bucket]);

  const handleAddBucket = async (name: string, selectedModules: BucketAllowedType[]) => {
    const trimmedName = name.trim();
    if (!trimmedName || selectedModules.length === 0) return false;

    const alreadyExists = buckets.some(
      (bucket) => bucket.name.toLowerCase() === trimmedName.toLowerCase(),
    );

    if (alreadyExists) {
      const existingBucket = buckets.find(
        (bucket) => bucket.name.toLowerCase() === trimmedName.toLowerCase(),
      );
      if (existingBucket) {
        setFormData((prev) => ({ ...prev, bucket: existingBucket.id }));
      }
      toast.info("Bucket already exists. Selected the existing one.");
      return true;
    }

    const allowedFileTypes = serializeBucketAllowedTypes(selectedModules);
    if (!allowedFileTypes) {
      toast.error("No valid content types were selected for this bucket.");
      return false;
    }

    try {
      const createdBucket = await createBucket({
        name: trimmedName,
        description: `Workspace storage bucket for ${selectedModules.map(getBucketAllowedTypeLabel).join(", ")}`,
        allowed_file_types: allowedFileTypes,
        created_by:
          localStorage.getItem("dr_profile_email") ||
          localStorage.getItem("dr_profile_name") ||
          DEFAULT_CREATED_BY,
        deletable: true,
        status: true,
      });

      const option = toBucketOption(createdBucket);
      setBuckets((prev) => [option, ...prev]);
      setFormData((prev) => ({ ...prev, bucket: option.id }));
      toast.success("Bucket created with selected content types");
      return true;
    } catch (err) {
      console.error("Failed to create bucket", err);
      const message = err instanceof Error ? err.message : "Failed to create bucket";
      toast.error(message);
      return false;
    }
  };

  const filteredBuckets = buckets.filter((bucket) =>
    bucket.name.toLowerCase().includes(bucketSearch.toLowerCase()),
  );

  const totalSteps = 4;

  // Form validation
  const isStep1Valid =
    formData.name.trim().length > 0 && formData.description.trim().length > 0;
  const isStep2Valid =
    (formData.icon !== null || formData.customIcon !== null || iconPreview !== null) &&
    formData.accentColor !== null;
  const isStep3Valid = Boolean(formData.aiMode); // aiMode is always valid if selected from list
  const isStep4Valid = true; // All fields optional

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return isStep1Valid;
      case 2:
        return isStep2Valid;
      case 3:
        return isStep3Valid;
      case 4:
        return isStep4Valid;
      default:
        return false;
    }
  };

  const handleNext = () => {
    if (currentStep < totalSteps && canProceed() && !isSaving) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 1 && !isSaving) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    if (isSaving) return;
    setIsSaving(true);
    try {
      const payload = {
        name: formData.name,
        description: formData.description,
        icon:
          formData.customIcon != null
            ? existingWorkspace?.icon ?? null
            : formData.icon?.name ?? existingWorkspace?.icon ?? null,
        accentColor: formData.accentColor?.hex ?? null,
        bannerUrl: existingWorkspace?.banner_img ?? null,
        aiMode: formData.aiMode,
        enableResearch: formData.enableResearch,
        enableChat: formData.enableChat,
        connectedBucketId: formData.bucket || null,
        bucket: formData.bucket || null,
        bannerImage: formData.bannerImage ?? null,
        customIcon: formData.customIcon ?? null,
        resources: formData.resources ?? [],
      };

      if (isEditMode && id) {
        let savedWorkspace = await updateWorkspace(id, payload);

        if (formData.bannerImage) {
          savedWorkspace = await uploadWorkspaceBanner(id, formData.bannerImage);
        }

        if (formData.customIcon) {
          savedWorkspace = await uploadWorkspaceIcon(id, formData.customIcon);
        }

        setExistingWorkspace((prev) =>
          prev
            ? {
              ...prev,
              name: savedWorkspace.name,
              desc: savedWorkspace.description,
              icon: savedWorkspace.icon ?? null,
              accent_clr: savedWorkspace.accentColor ?? existingWorkspace?.accent_clr ?? null,
              banner_img: savedWorkspace.bannerUrl ?? null,
              connected_bucket_id: savedWorkspace.connectedBucketId ?? null,
              ai_config: savedWorkspace.aiMode === "offline" ? "local" : savedWorkspace.aiMode,
              workspace_research_agents: savedWorkspace.enableResearch,
              workspace_chat_agents: savedWorkspace.enableChat,
            }
            : prev,
        );
        setBannerPreview(resolveApiAssetUrl(savedWorkspace.bannerUrl));
        if (isWorkspaceAssetPath(savedWorkspace.icon)) {
          setIconPreview(resolveApiAssetUrl(savedWorkspace.icon));
          setFormData((prev) => ({ ...prev, customIcon: null, icon: null, bannerImage: null }));
        } else {
          setFormData((prev) => ({ ...prev, customIcon: null, bannerImage: null }));
        }
        const normalizedSavedAccent = normalizeHexColor(savedWorkspace.accentColor);
        if (normalizedSavedAccent) {
          const nextAccent = ACCENT_COLORS.find(
            (c) => c.hex.toLowerCase() === normalizedSavedAccent.toLowerCase(),
          );
          if (nextAccent) {
            setFormData((prev) => ({ ...prev, accentColor: nextAccent }));
          }
        }
        toast.success("Workspace updated");
        navigate(`/workspaces/view/${id}`);
      } else {
        const created = await createWorkspace(payload);
        setBannerPreview(resolveApiAssetUrl(created.bannerUrl));
        if (isWorkspaceAssetPath(created.icon)) {
          setIconPreview(resolveApiAssetUrl(created.icon));
        }
        toast.success("Workspace created");
        navigate(`/workspaces/view/${created.id}`);
      }
    } catch (err) {
      console.error(`Failed to ${isEditMode ? "update" : "create"} workspace`, err);
      const message = err instanceof Error ? err.message : String(err);
      toast.error(`Failed to ${isEditMode ? "update" : "create"} workspace: ${message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);

      if (!selectedBucket) {
        toast.error("Please select a storage bucket first.");
        return;
      }

      // Validate files against the selected bucket's allowed types
      const validation = validateFilesAgainstBucket(newFiles, selectedBucket.allowedFileTypes);
      if (!validation.valid) {
        toast.error(validation.rejectedReason);
        // Only consider valid files
        const validFiles = newFiles.filter((f) => !validation.rejectedFiles.includes(f.name));
        if (validFiles.length === 0) {
          e.target.value = "";
          return;
        }
        setFormData({
          ...formData,
          resources: [...formData.resources, ...validFiles],
        });
      } else {
        setFormData({
          ...formData,
          resources: [...formData.resources, ...newFiles],
        });
      }
      e.target.value = "";
    }
  };

  const removeFile = (index: number) => {
    const newResources = formData.resources.filter((_, i) => i !== index);
    setFormData({ ...formData, resources: newResources });
  };

  const handleBannerUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setFormData({ ...formData, bannerImage: file });
      if (bannerPreview) URL.revokeObjectURL(bannerPreview);
      setBannerPreview(URL.createObjectURL(file));
    }
  };

  const handleIconUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setFormData({ ...formData, customIcon: file, icon: null });
      if (iconPreview) URL.revokeObjectURL(iconPreview);
      setIconPreview(URL.createObjectURL(file));
    }
  };

  if (isLoadingWorkspace) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-8 h-full text-foreground overflow-y-auto animate-in fade-in duration-500">
      {/* Header */}
      <div className="border-b bg-background/50 backdrop-blur-sm sticky top-0 z-30">
        <div className="w-full px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-5">
              <div className="size-12 rounded-2xl bg-linear-to-br from-primary/20 via-primary/10 to-transparent border border-primary/20 flex items-center justify-center animate-in fade-in zoom-in duration-500">
                <FolderPlus className="size-6 text-primary" />
              </div>
              <div className="flex flex-col gap-2">
                <h1 className="text-xl font-semibold tracking-tight">
                  {isEditMode ? "Edit Workspace" : "Create New Workspace"}
                </h1>
                <p className="text-muted-foreground">
                  {isEditMode
                    ? "Update your workspace settings."
                    : "Set up your research environment in a few simple steps."}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Indicator */}
      <div className="flex items-center justify-center gap-2 max-w-2xl mx-auto">
        {Array.from({ length: totalSteps }).map((_, index) => {
          const stepNumber = index + 1;
          const isActive = stepNumber === currentStep;
          const isCompleted = stepNumber < currentStep;

          return (
            <div
              key={stepNumber}
              className="flex items-center flex-1 last:flex-none"
            >
              <div
                className={`flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all ${isCompleted
                  ? "bg-primary border-primary text-primary-foreground"
                  : isActive
                    ? "border-primary text-primary"
                    : "border-muted-foreground/30 text-muted-foreground"
                  }`}
              >
                {isCompleted ? <Check className="w-5 h-5" /> : stepNumber}
              </div>
              {stepNumber < totalSteps && (
                <div
                  className={`flex-1 h-1 mx-2 rounded-full transition-all ${isCompleted ? "bg-primary" : "bg-muted-foreground/20"
                    }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Step Content */}
      <div className="max-w-4xl mx-auto">
        {currentStep === 1 && (
          <Card className="border-muted-foreground/20 animate-in fade-in slide-in-from-right-4 duration-300">
            <CardHeader>
              <CardTitle className="text-2xl">Basic Information</CardTitle>
              <CardDescription>
                Give your workspace a name and description
              </CardDescription>
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
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  maxLength={50}
                  className="text-base"
                />
                <p className="text-xs text-muted-foreground text-right">
                  {formData.name.length}/50
                </p>
              </div>

              <div className="space-y-2">
                <label
                  htmlFor="workspace-description"
                  className="text-sm font-medium"
                >
                  Short Description <span className="text-destructive">*</span>
                </label>
                <textarea
                  id="workspace-description"
                  placeholder="Briefly describe what this workspace is for..."
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  maxLength={150}
                  rows={4}
                  className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-base shadow-xs transition-[color,box-shadow] outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] resize-none"
                />
                <p className="text-xs text-muted-foreground text-right">
                  {formData.description.length}/150
                </p>
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
                    <CardDescription>
                      Select an icon to represent your workspace
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-3">
                  {WORKSPACE_ICONS.map((item) => {
                    const Icon = item.icon;
                    const isSelected = formData.icon?.name === item.name;
                    return (
                      <button
                        key={item.name}
                        type="button"
                        onClick={() => setFormData({ ...formData, icon: item, customIcon: null })}
                        className={`aspect-square rounded-xl border-2 transition-all hover:scale-105 flex items-center justify-center ${isSelected
                          ? "border-primary bg-primary/10 shadow-md"
                          : "border-muted-foreground/20 bg-muted/10 hover:border-primary/50"
                          }`}
                      >
                        <Icon className={`w-8 h-8 ${item.color}`} />
                      </button>
                    );
                  })}

                  {/* Custom Icon Upload */}
                  <label
                    htmlFor="icon-upload"
                    className={`aspect-square rounded-xl border-2 border-dashed transition-all cursor-pointer hover:scale-105 flex items-center justify-center relative overflow-hidden ${(formData.customIcon || iconPreview)
                      ? "border-primary bg-primary/10 shadow-md"
                      : "border-muted-foreground/20 bg-muted/10 hover:border-primary/50"
                      }`}
                  >
                    {iconPreview ? (
                      <div className="w-full h-full relative group">
                        <img
                          src={iconPreview}
                          alt="Custom Icon"
                          className="w-full h-full object-cover"
                        />
                        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                          <Upload className="w-5 h-5 text-white" />
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-1">
                        <Plus className="w-8 h-8 text-muted-foreground" />
                        <span className="text-[10px] text-muted-foreground font-semibold">Custom</span>
                      </div>
                    )}
                    <input
                      id="icon-upload"
                      type="file"
                      className="hidden"
                      accept="image/*"
                      onChange={handleIconUpload}
                    />
                  </label>
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
                    <CardDescription>
                      Choose a color theme for your workspace
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-6 sm:grid-cols-8 md:grid-cols-12 gap-3">
                  {ACCENT_COLORS.map((color) => {
                    const isSelected =
                      formData.accentColor?.name === color.name;
                    return (
                      <button
                        key={color.name}
                        onClick={() =>
                          setFormData({ ...formData, accentColor: color })
                        }
                        className={`relative p-0 rounded-lg border-2 transition-all hover:scale-105 aspect-square ${isSelected
                          ? "border-primary shadow-lg"
                          : "border-muted-foreground/20"
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
                    );
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
                    <CardDescription>
                      Optional: Add a custom banner image
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <label
                    htmlFor="banner-upload"
                    className="relative group flex flex-col items-center justify-center w-full min-h-40 border-2 border-dashed border-muted-foreground/30 rounded-lg cursor-pointer hover:border-primary/50 overflow-hidden transition-all bg-muted/5"
                  >
                    {bannerPreview ? (
                      <div className="w-full h-full flex items-center justify-center">
                        <img
                          src={bannerPreview}
                          alt="Banner Preview"
                          className="w-full h-auto max-h-125 object-contain transition-transform group-hover:scale-[1.02]"
                        />
                        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex flex-col items-center justify-center transition-opacity text-white">
                          <Upload className="w-8 h-8 mb-2" />
                          <p className="text-sm font-medium">Change Banner</p>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center space-y-2">
                        <Upload className="w-12 h-12 mx-auto text-muted-foreground" />
                        <p className="text-sm font-medium">
                          Click to upload banner
                        </p>
                        <p className="text-xs text-muted-foreground">
                          PNG, JPG up to 5MB
                        </p>
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

            {/* Final Visual Preview */}
            {(formData.icon || formData.customIcon) && formData.accentColor && (
              <Card className="border-primary/30 bg-primary/5 overflow-hidden">
                <CardHeader>
                  <CardTitle className="text-lg">Workspace Preview</CardTitle>
                </CardHeader>
                <CardContent className="px-6 pb-6">
                  <div className="relative rounded-xl overflow-hidden bg-background border border-muted-foreground/20 shadow-xl max-w-2xl mx-auto">
                    {/* Banner Section */}
                    <div className="min-h-32 bg-muted relative flex items-center justify-center border-b border-muted-foreground/10">
                      {bannerPreview ? (
                        <img
                          src={bannerPreview}
                          alt="Banner"
                          className="w-full h-auto max-h-64 object-contain transition-all"
                        />
                      ) : (
                        <div className={`w-full h-full min-h-32 opacity-20 ${formData.accentColor.bg}`} />
                      )}

                      {/* Icon Overlay */}
                      <div className="absolute -bottom-6 left-6 z-10">
                        <div className={`size-16 rounded-2xl border-4 border-background bg-background shadow-lg flex items-center justify-center overflow-hidden`}>
                          <div className={`w-full h-full flex items-center justify-center bg-secondary/30 ${formData.accentColor.class}`}>
                            {iconPreview ? (
                              <img src={iconPreview} alt="Custom Icon" className="w-full h-full object-cover" />
                            ) : (
                              formData.icon && <formData.icon.icon className="w-8 h-8" />
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Content Section */}
                    <div className="pt-8 pb-6 px-6">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-bold text-xl leading-tight">
                          {formData.name || "Workspace Name"}
                        </h3>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest bg-primary/10 text-primary`}>
                          Active
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {formData.description || "Set your workspace description in Step 1 to see how it looks here."}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {currentStep === 3 && (
          <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
            {/* Environment & Storage Selection */}
            <Card className="border-muted-foreground/20 relative overflow-hidden">
              {isLoadingStorage && (
                <div className="absolute inset-0 bg-background/60 backdrop-blur-[1px] z-10 flex items-center justify-center">
                  <div className="flex flex-col items-center gap-2">
                    <Loader2 className="w-8 h-8 text-primary animate-spin" />
                    <p className="text-sm font-medium animate-pulse">Loading storage data...</p>
                  </div>
                </div>
              )}
              <CardHeader>
                <div className="flex items-center gap-3">
                  <Database className="w-6 h-6 text-primary" />
                  <div>
                    <CardTitle className="text-2xl">Storage Management</CardTitle>
                    <CardDescription>
                      Assign a storage bucket for your workspace research data
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Interactive Method: Quick Bucket Add */}
                <div className="">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-sm font-medium flex items-center gap-2">
                      Select Storage Bucket <span className="text-destructive">*</span>
                    </h4>
                    <div className="relative w-48">
                      <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-foreground" />
                      <input
                        type="text"
                        placeholder="Filter buckets..."
                        value={bucketSearch}
                        onChange={(e) => setBucketSearch(e.target.value)}
                        className="w-full bg-muted/50 border border-muted-foreground/20 rounded-md py-1 pl-7 pr-2 text-[10px] outline-hidden focus:border-primary/50 transition-all"
                      />
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {filteredBuckets.map((bucketOption) => (
                      <button
                        key={bucketOption.id}
                        onClick={() => {
                          if (formData.bucket !== bucketOption.id) {
                            setFormData({ ...formData, bucket: bucketOption.id, resources: [] });
                          }
                        }}
                        className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all flex items-center gap-2 ${formData.bucket === bucketOption.id
                          ? "bg-primary text-primary-foreground scale-110 shadow-lg z-10"
                          : "bg-muted hover:bg-muted-foreground/10 text-muted-foreground"
                          }`}
                      >
                        <Database className="w-3 h-3" />
                        {bucketOption.name}
                      </button>
                    ))}
                    <button
                      onClick={() => setIsBucketModalOpen(true)}
                      className="px-3 py-1.5 rounded-full text-xs font-medium bg-primary/10 text-primary hover:bg-primary/20 transition-all flex items-center gap-2 border border-primary/20 border-dashed"
                    >
                      <Plus className="w-3 h-3" />
                      Add New Bucket
                    </button>
                  </div>
                  {filteredBuckets.length === 0 && buckets.length > 0 && (
                    <p className="text-[10px] text-muted-foreground mt-2 italic">No buckets match your search.</p>
                  )}

                  {/* Bucket Preview */}
                  {selectedBucket && (
                    <div className="mt-8 p-4 rounded-xl border border-primary/20 bg-primary/5 animate-in fade-in slide-in-from-bottom-2 duration-500">
                      <div className="flex items-start justify-between">
                        <div className="flex gap-4">
                          <div className="p-3 rounded-lg bg-primary/10 text-primary h-fit">
                            <Database className="w-6 h-6" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="font-bold text-lg truncate">{selectedBucket.name}</h4>
                              <span className="px-2 py-0.5 rounded-full bg-primary/20 text-primary text-[10px] font-bold uppercase tracking-wider">
                                Active
                              </span>
                            </div>
                            <p className="text-xs text-muted-foreground mb-4 line-clamp-1">
                              {selectedBucket.description || "Primary storage for workspace research data, logs, and generated assets."}
                            </p>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                              <div className="min-w-0">
                                <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter mb-1">Supported Types</p>
                                {(() => {
                                  const supportedTypes = formatBucketAllowedTypes(selectedBucket.allowedFileTypes);
                                  const isLong = supportedTypes.length > 40;
                                  const truncated = isLong ? `${supportedTypes.slice(0, 40)}...` : supportedTypes;

                                  return (
                                    <TooltipProvider>
                                      <Tooltip>
                                        <TooltipTrigger asChild>
                                          <div className="flex items-center gap-1.5 overflow-hidden w-fit max-w-full cursor-help">
                                            <span className="text-sm font-semibold truncate border-b border-dashed border-muted-foreground/30 hover:text-primary hover:border-primary/50 transition-all">
                                              {truncated}
                                            </span>
                                            {isLong && <Info className="w-3 h-3 text-muted-foreground shrink-0" />}
                                          </div>
                                        </TooltipTrigger>
                                        {isLong && (
                                          <TooltipContent side="top" className="max-w-72 p-3 border-primary/20 bg-neutral-900/95 backdrop-blur-xl">
                                            <div className="space-y-1.5">
                                              <p className="text-[10px] font-bold text-primary uppercase tracking-widest">Allowed Bucket Types</p>
                                              <p className="text-xs leading-relaxed text-neutral-300 wrap-break-word">{supportedTypes}</p>
                                            </div>
                                          </TooltipContent>
                                        )}
                                      </Tooltip>
                                    </TooltipProvider>
                                  );
                                })()}
                              </div>
                              <div className="min-w-0">
                                <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter mb-1">Current Size</p>
                                <p className="text-sm font-semibold">{formatBytes(selectedBucket.totalSize)}</p>
                                <p className="text-[10px] text-muted-foreground mt-0.5">{selectedBucket.totalFiles} files</p>
                              </div>
                              <div className="min-w-0">
                                <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter mb-1">Connected Workspaces</p>
                                {(() => {
                                  if (isLoadingConnectedWorkspaces) {
                                    return <p className="text-sm font-semibold text-muted-foreground">Loading...</p>;
                                  }

                                  if (connectedWorkspaceNames.length === 0) {
                                    return <p className="text-sm font-semibold text-muted-foreground">No connected workspaces</p>;
                                  }

                                  const workspaces = connectedWorkspaceNames.join(", ");
                                  const truncated = workspaces.length > 40 ? `${workspaces.slice(0, 40)}...` : workspaces;
                                  return (
                                    <TooltipProvider>
                                      <Tooltip>
                                        <TooltipTrigger asChild>
                                          <p className="text-sm font-semibold cursor-help truncate border-b border-dashed border-muted-foreground/30 hover:text-primary hover:border-primary/50 transition-all w-fit max-w-full">
                                            {truncated}
                                          </p>
                                        </TooltipTrigger>
                                        <TooltipContent side="top" className="max-w-64 p-3 border-primary/20 bg-neutral-900/95 backdrop-blur-xl">
                                          <div className="space-y-1.5">
                                            <p className="text-[10px] font-bold text-primary uppercase tracking-widest">All Connected Workspaces</p>
                                            <p className="text-xs leading-relaxed text-neutral-300">{workspaces}</p>
                                          </div>
                                        </TooltipContent>
                                      </Tooltip>
                                    </TooltipProvider>
                                  );
                                })()}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <CreateBucketModal
              isOpen={isBucketModalOpen}
              onClose={() => setIsBucketModalOpen(false)}
              onCreate={handleAddBucket}
            />

            {/* AI Configuration - Currently Disabled for Future Implementation */}
            <Card className="border-muted-foreground/20 relative overflow-hidden">
              <div className="absolute inset-0 bg-background/20 backdrop-blur-[0.5px] z-10 flex items-center justify-center">
                <div className="bg-primary/10 text-primary text-[10px] font-bold uppercase tracking-widest px-3 py-1 rounded-full border border-primary/20 shadow-sm animate-pulse">
                  Future Implementation
                </div>
              </div>
              <CardHeader>
                <div className="flex items-center gap-3">
                  <Bot className="w-6 h-6 text-primary" />
                  <div>
                    <CardTitle className="text-2xl">AI Configuration</CardTitle>
                    <CardDescription>
                      Choose how AI models should operate in this workspace
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="opacity-50 pointer-events-none">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {AI_MODES.map((mode) => {
                    const Icon = mode.icon;
                    const isSelected = formData.aiMode === mode.id;
                    return (
                      <div
                        key={mode.id}
                        className={`p-4 rounded-xl border-2 text-left transition-all ${isSelected
                          ? "border-primary bg-primary/10 shadow-lg"
                          : "border-muted-foreground/20 bg-muted/5"
                          }`}
                      >
                        <Icon
                          className={`w-8 h-8 mb-3 ${isSelected ? "text-primary" : "text-muted-foreground"}`}
                        />
                        <h3 className="font-semibold text-base mb-1">
                          {mode.title}
                        </h3>
                        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                          {mode.description}
                        </p>
                        {isSelected && (
                          <div className="mt-2 flex items-center gap-1 text-primary text-[10px] font-medium uppercase tracking-wider">
                            <Check className="w-3 h-3" />
                            Selected
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
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
                      {selectedBucket
                        ? `Upload ${formatBucketAllowedTypes(selectedBucket.allowedFileTypes)} files to your workspace (optional)`
                        : "Select a storage bucket in Step 3 to upload resources (optional)"}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {!selectedBucket ? (
                  <div className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-muted-foreground/20 rounded-lg bg-muted/10">
                    <Database className="w-10 h-10 mb-2 text-muted-foreground/40" />
                    <p className="text-sm font-medium text-muted-foreground">
                      No storage bucket selected
                    </p>
                    <p className="text-xs text-muted-foreground/60 mt-1">
                      Go back to Step 3 and select a bucket to enable resource uploads
                    </p>
                  </div>
                ) : (
                  <>
                    <label
                      htmlFor="resource-upload"
                      className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-muted-foreground/30 rounded-lg cursor-pointer hover:border-primary/50 hover:bg-muted/30 transition-all"
                    >
                      <Upload className="w-10 h-10 mb-2 text-muted-foreground" />
                      <p className="text-sm font-medium">
                        Click to upload or drag and drop
                      </p>
                      <input
                        id="resource-upload"
                        type="file"
                        className="hidden"
                        multiple
                        accept={getAcceptExtensionsForBucketTypes(selectedBucket.allowedFileTypes)}
                        onChange={handleFileUpload}
                      />
                    </label>

                    {/* Bucket info badge */}
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Database className="w-3 h-3" />
                      <span>Uploading to: <span className="font-medium text-foreground">{selectedBucket.name}</span></span>
                      <span className="text-muted-foreground/40">•</span>
                      <span>Accepts: <span className="font-medium text-foreground">{formatBucketAllowedTypes(selectedBucket.allowedFileTypes)}</span></span>
                    </div>
                  </>
                )}

                {/* Uploaded Files List */}
                {formData.resources.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-muted-foreground">
                      Uploaded Files ({formData.resources.length})
                    </h4>
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
                    <CardDescription>
                      Choose which AI agents can operate in this workspace
                    </CardDescription>
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
                    onClick={() =>
                      setFormData({
                        ...formData,
                        enableResearch: !formData.enableResearch,
                      })
                    }
                    className={`relative w-14 h-7 rounded-full transition-colors ${formData.enableResearch
                      ? "bg-primary"
                      : "bg-muted-foreground/30"
                      }`}
                    disabled={isSaving}
                  >
                    <div
                      className={`absolute top-1 w-5 h-5 rounded-full bg-white shadow-md transition-transform ${formData.enableResearch
                        ? "translate-x-8"
                        : "translate-x-1"
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
                    onClick={() =>
                      setFormData({
                        ...formData,
                        enableChat: !formData.enableChat,
                      })
                    }
                    className={`relative w-14 h-7 rounded-full transition-colors ${formData.enableChat
                      ? "bg-primary"
                      : "bg-muted-foreground/30"
                      }`}
                    disabled={isSaving}
                  >
                    <div
                      className={`absolute top-1 w-5 h-5 rounded-full bg-white shadow-md transition-transform ${formData.enableChat ? "translate-x-8" : "translate-x-1"
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
      <div className="max-w-4xl mx-auto mb-8">
        <Separator className="mb-6" />
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            onClick={handlePrevious}
            disabled={currentStep === 1 || isSaving}
            className="gap-2"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous
          </Button>

          {currentStep < totalSteps ? (
            <Button
              onClick={handleNext}
              disabled={!canProceed() || isSaving}
              className="gap-2"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              className={`gap-2 bg-primary hover:bg-primary/90 ${isSaving ? "opacity-80 cursor-wait" : ""}`}
              disabled={isSaving}
            >
              <Check className="w-4 h-4" />
              {isSaving ? (isEditMode ? "Saving..." : "Creating...") : (isEditMode ? "Save Changes" : "Create Workspace")}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default CreateEditWorkspace;
