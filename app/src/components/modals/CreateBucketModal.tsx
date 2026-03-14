import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Database,
  Plus,
  Pencil,
  X,
  Image as ImageIcon,
  Video,
  FileText,
  Music,
  MoreHorizontal,
  Info,
  Check,
  Lock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { type BucketAllowedType } from "@/lib/bucket-types";

export interface EditBucketData {
  id: string;
  name: string;
  description: string;
  allowedTypes: BucketAllowedType[];
}

interface CreateBucketModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** Called when creating a new bucket */
  onCreate: (name: string, selectedTypes: BucketAllowedType[]) => Promise<boolean> | boolean;
  /** When provided the modal switches to edit mode */
  editBucket?: EditBucketData | null;
  /** Called when saving an edited bucket */
  onEdit?: (id: string, name: string) => Promise<boolean> | boolean;
}

const MEDIA_TYPES = [
  { id: "image", label: "Image", icon: ImageIcon, color: "text-blue-400", bg: "bg-blue-400/10" },
  { id: "audio", label: "Audio", icon: Music, color: "text-orange-400", bg: "bg-orange-400/10" },
  { id: "video", label: "Video", icon: Video, color: "text-purple-400", bg: "bg-purple-400/10" },
  { id: "files", label: "Files", icon: FileText, color: "text-green-400", bg: "bg-green-400/10" },
  { id: "other", label: "Other", icon: MoreHorizontal, color: "text-pink-400", bg: "bg-pink-400/10" },
] as const satisfies ReadonlyArray<{
  id: BucketAllowedType;
  label: string;
  icon: typeof ImageIcon;
  color: string;
  bg: string;
}>;

const CreateBucketModal: React.FC<CreateBucketModalProps> = ({
  isOpen,
  onClose,
  onCreate,
  editBucket,
  onEdit,
}) => {
  const isEditMode = Boolean(editBucket);
  const [bucketName, setBucketName] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<BucketAllowedType[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  // Sync form state whenever the modal opens or the edit target changes
  useEffect(() => {
    if (isOpen) {
      setBucketName(editBucket ? editBucket.name : "");
      setSelectedTypes(editBucket ? editBucket.allowedTypes : []);
      setIsSaving(false);
    }
  }, [isOpen, editBucket]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = bucketName.trim();
    if (!trimmedName) return;
    setIsSaving(true);
    try {
      if (isEditMode && editBucket && onEdit) {
        const saved = await onEdit(editBucket.id, trimmedName);
        if (saved === false) return;
      } else {
        if (selectedTypes.length === 0) return;
        const created = await onCreate(trimmedName, selectedTypes);
        if (created === false) return;
      }
      setBucketName("");
      setSelectedTypes([]);
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  const toggleType = (id: BucketAllowedType) => {
    // Types are immutable after creation – only toggle in create mode
    if (isEditMode) return;
    setSelectedTypes(prev =>
      prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id]
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={isSaving ? undefined : onClose}>
      {/* [&>button]:hidden suppresses the default shadcn close button which breaks under p-0 */}
      <DialogContent className="sm:max-w-3xl w-[95vw] sm:w-[50vw] bg-neutral-950/95 backdrop-blur-xl border-white/10 shadow-2xl overflow-hidden p-0 gap-0 [&>button]:hidden">
        <div className="absolute inset-0 bg-linear-to-br from-primary/5 via-transparent to-transparent pointer-events-none" />

        {/* Custom close button */}
        <button
          type="button"
          onClick={onClose}
          disabled={isSaving}
          aria-label="Close"
          className="absolute top-4 right-4 z-50 size-8 rounded-full flex items-center justify-center bg-white/5 hover:bg-white/15 border border-white/10 hover:border-white/25 text-muted-foreground hover:text-foreground transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <X className="w-4 h-4" />
        </button>

        <DialogHeader className="p-8 pb-4 relative z-10">
          <div className="flex items-center gap-4 mb-2">
            <div className="size-12 rounded-2xl bg-linear-to-br from-primary/20 via-primary/10 to-transparent border border-primary/20 flex items-center justify-center">
              {isEditMode ? <Pencil className="size-6 text-primary" /> : <Database className="size-6 text-primary" />}
            </div>
            <div>
              <DialogTitle className="text-2xl font-bold tracking-tight">
                {isEditMode ? "Edit Bucket" : "Create New Bucket"}
              </DialogTitle>
              <DialogDescription className="text-muted-foreground/80 mt-1">
                {isEditMode
                  ? "Update the bucket name. Content types are locked after creation."
                  : "Establish a dedicated storage container for your research assets."}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="p-8 pt-2 space-y-8 relative z-10">
          {/* Bucket Name Input */}
          <div className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <label htmlFor="bucket-name" className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/70">
                Bucket Identifier
              </label>
              <span className="text-[10px] text-primary/60 font-medium">Required</span>
            </div>
            <div className="relative group">
              <Input
                id="bucket-name"
                placeholder="e.g. market-research-2024"
                value={bucketName}
                onChange={(e) => setBucketName(e.target.value)}
                autoFocus
                className="h-12 bg-white/5 border-white/10 hover:border-primary/50 focus-visible:ring-primary/20 transition-all text-base px-4 rounded-xl"
              />
            </div>
          </div>

          {/* Media Types Selection Grid */}
          <div className="space-y-4">
            <div className="flex items-center justify-between px-1">
              <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/70">
                Allowed Content Types
              </label>
              <div className="flex items-center gap-1.5 opacity-60">
                {isEditMode ? <Lock className="w-3 h-3" /> : <Info className="w-3 h-3" />}
                <span className="text-[10px]">
                  {isEditMode ? "Locked — types are immutable after creation" : "Only 5 types supported. Choose once, then immutable"}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
              {MEDIA_TYPES.map((type) => {
                const Icon = type.icon;
                const isSelected = selectedTypes.includes(type.id);
                return (
                  <button
                    key={type.id}
                    type="button"
                    onClick={() => toggleType(type.id)}
                    disabled={isEditMode}
                    className={cn(
                      "flex items-center gap-3 p-4 rounded-xl border-2 transition-all text-left group relative",
                      isEditMode
                        ? isSelected
                          ? "bg-primary/10 border-primary/40 opacity-70 cursor-not-allowed"
                          : "bg-white/3 border-white/5 opacity-40 cursor-not-allowed"
                        : isSelected
                          ? "bg-primary/10 border-primary shadow-lg ring-4 ring-primary/5"
                          : "bg-white/5 border-white/5 hover:border-white/20 hover:bg-white/10"
                    )}
                  >
                    {isSelected && (
                      <div className="absolute top-3 right-3 size-5 rounded-full bg-primary flex items-center justify-center">
                        {isEditMode
                          ? <Lock className="w-3 h-3 text-primary-foreground" />
                          : <Check className="w-3 h-3 text-primary-foreground animate-in zoom-in duration-300" />}
                      </div>
                    )}
                    <div className={cn("p-2 rounded-lg transition-colors", isSelected ? type.bg : "bg-white/5")}>
                      <Icon className={cn("w-5 h-5 transition-colors", isSelected ? type.color : "text-muted-foreground/60")} />
                    </div>
                    <span className={cn("font-semibold text-sm transition-colors", isSelected ? "text-primary" : "text-muted-foreground/80")}>
                      {type.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <DialogFooter className="pt-4  flex flex-row items-center justify-end gap-3 translate-x-3">
            <p className="mr-auto text-[11px] text-muted-foreground">
              {isEditMode
                ? "Update the name above and save"
                : selectedTypes.length === 0
                  ? "Select at least one content type"
                  : `${selectedTypes.length} type${selectedTypes.length > 1 ? "s" : ""} selected`}
            </p>
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              disabled={isSaving}
              className="px-6 hover:bg-white/5 text-muted-foreground h-11"
            >
              Discard
            </Button>
            <Button
              type="submit"
              disabled={isSaving || !bucketName.trim() || (!isEditMode && selectedTypes.length === 0)}
              className="px-8 rounded-xl h-11 bg-primary text-primary-foreground hover:bg-primary/90 shadow-xl shadow-primary/20 transition-all font-bold gap-2"
            >
              {isEditMode ? <Pencil className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
              {isSaving ? "Saving..." : isEditMode ? "Save Changes" : "Create Bucket"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default CreateBucketModal;
