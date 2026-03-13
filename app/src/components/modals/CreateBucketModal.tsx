import React, { useState } from "react";
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
import { Checkbox } from "@/components/ui/checkbox";
import { Database, Plus } from "lucide-react";

interface CreateBucketModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string) => void;
}

const CreateBucketModal: React.FC<CreateBucketModalProps> = ({
  isOpen,
  onClose,
  onCreate,
}) => {
  const [bucketName, setBucketName] = useState("");
  const [types, setTypes] = useState({
    images: false,
    videos: false,
    files: false,
    audio: false,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (bucketName.trim()) {
      // We can pass the types back if needed, but for now just following user request for UI
      onCreate(bucketName.trim());
      setBucketName("");
      setTypes({
        images: false,
        videos: false,
        files: false,
        audio: false,
      });
      onClose();
    }
  };

  const toggleType = (type: keyof typeof types) => {
    setTypes((prev) => ({ ...prev, [type]: !prev[type] }));
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-2 rounded-lg bg-primary/10">
              <Database className="w-5 h-5 text-primary" />
            </div>
            <DialogTitle className="text-xl">Create New Bucket</DialogTitle>
          </div>
          <DialogDescription>
            Enter a unique name and select allowed media types.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-6 pt-4">
          <div className="space-y-2">
            <label htmlFor="bucket-name" className="text-sm font-medium">
              Bucket Name
            </label>
            <Input
              id="bucket-name"
              placeholder="e.g. workspace-alpha-storage"
              value={bucketName}
              onChange={(e) => setBucketName(e.target.value)}
              autoFocus
            />
          </div>

          <div className="space-y-3">
            <label className="text-sm font-medium">Allowed Media Types</label>
            <div className="grid grid-cols-2 gap-4 pt-1">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="images"
                  checked={types.images}
                  onCheckedChange={() => toggleType("images")}
                />
                <label
                  htmlFor="images"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                >
                  Images
                </label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="videos"
                  checked={types.videos}
                  onCheckedChange={() => toggleType("videos")}
                />
                <label
                  htmlFor="videos"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                >
                  Videos
                </label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="files"
                  checked={types.files}
                  onCheckedChange={() => toggleType("files")}
                />
                <label
                  htmlFor="files"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                >
                  Files
                </label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="audio"
                  checked={types.audio}
                  onCheckedChange={() => toggleType("audio")}
                />
                <label
                  htmlFor="audio"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                >
                  Audio
                </label>
              </div>
              <div className="flex items-center space-x-2 opacity-60">
                <Checkbox id="other" checked={true} disabled />
                <label
                  htmlFor="other"
                  className="text-sm font-medium leading-none cursor-not-allowed"
                >
                  Other (Required)
                </label>
              </div>
            </div>
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="flex-1 sm:flex-none"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!bucketName.trim()}
              className="flex-1 sm:flex-none gap-2"
            >
              <Plus className="w-4 h-4" />
              Create Bucket
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default CreateBucketModal;
