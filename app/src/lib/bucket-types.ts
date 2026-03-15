export type BucketAllowedType = "image" | "audio" | "video" | "files" | "other";

export const BUCKET_ALLOWED_TYPE_ORDER: BucketAllowedType[] = [
    "image",
    "audio",
    "video",
    "files",
    "other",
];

const BUCKET_ALLOWED_TYPE_LABELS: Record<BucketAllowedType, string> = {
    image: "Image",
    audio: "Audio",
    video: "Video",
    files: "Files",
    other: "Other",
};

const BUCKET_ALLOWED_TYPE_ALIASES: Record<string, BucketAllowedType> = {
    image: "image",
    images: "image",
    audio: "audio",
    video: "video",
    videos: "video",
    file: "files",
    files: "files",
    document: "files",
    documents: "files",
    other: "other",
    others: "other",
};

const LEGACY_EXTENSION_MAP: Record<string, BucketAllowedType> = {
    png: "image",
    jpg: "image",
    jpeg: "image",
    webp: "image",
    gif: "image",
    bmp: "image",
    svg: "image",
    tiff: "image",
    ico: "image",
    mp3: "audio",
    wav: "audio",
    m4a: "audio",
    aac: "audio",
    flac: "audio",
    ogg: "audio",
    mp4: "video",
    mov: "video",
    avi: "video",
    mkv: "video",
    webm: "video",
    wmv: "video",
    flv: "video",
    pdf: "files",
    doc: "files",
    docx: "files",
    xls: "files",
    xlsx: "files",
    ppt: "files",
    pptx: "files",
    txt: "files",
    csv: "files",
    json: "files",
    xml: "files",
    zip: "files",
    tar: "files",
    gz: "files",
    rar: "files",
    yaml: "other",
    yml: "other",
};

/** Reverse map: category → list of file extensions */
const CATEGORY_EXTENSIONS: Record<BucketAllowedType, string[]> = {
    image: ["jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "tiff", "ico"],
    audio: ["mp3", "wav", "ogg", "flac", "aac", "m4a"],
    video: ["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"],
    files: ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv", "json", "xml", "zip", "tar", "gz", "rar"],
    other: ["yaml", "yml"],
};

/**
 * Given a bucket's `allowed_file_types` string (e.g. "image,files"),
 * return the HTML `accept` attribute value (e.g. ".jpg,.jpeg,.png,...,.pdf,.doc,...").
 * Returns `undefined` if no types are configured (= accept all).
 */
export const getAcceptExtensionsForBucketTypes = (
    allowedFileTypes?: string | null,
): string | undefined => {
    if (!allowedFileTypes || allowedFileTypes.trim() === "*") return undefined;

    const categories = parseBucketAllowedTypes(allowedFileTypes);
    if (categories.length === 0) return undefined;

    const extensions: string[] = [];
    for (const cat of categories) {
        const exts = CATEGORY_EXTENSIONS[cat];
        if (exts) {
            extensions.push(...exts.map((ext) => `.${ext}`));
        }
    }

    return extensions.length > 0 ? extensions.join(",") : undefined;
};

/**
 * Given a file's extension (without dot), return its bucket category.
 * Returns `"other"` if the extension is not recognized.
 */
export const getFileCategoryFromExtension = (
    extension: string,
): BucketAllowedType => {
    const normalized = extension.trim().toLowerCase().replace(/^\./, "");
    return LEGACY_EXTENSION_MAP[normalized] ?? "other";
};

/**
 * Validate a list of files against a bucket's allowed_file_types.
 * Returns an array of rejected file names (empty if all files are valid).
 */
export const validateFilesAgainstBucket = (
    files: File[],
    allowedFileTypes?: string | null,
): { valid: boolean; rejectedFiles: string[]; rejectedReason: string } => {
    if (!allowedFileTypes || allowedFileTypes.trim() === "*") {
        return { valid: true, rejectedFiles: [], rejectedReason: "" };
    }

    const allowedCategories = parseBucketAllowedTypes(allowedFileTypes);
    if (allowedCategories.length === 0) {
        return { valid: true, rejectedFiles: [], rejectedReason: "" };
    }

    const rejectedFiles: string[] = [];
    for (const file of files) {
        const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
        const category = getFileCategoryFromExtension(ext);
        if (!allowedCategories.includes(category)) {
            rejectedFiles.push(file.name);
        }
    }

    if (rejectedFiles.length > 0) {
        const allowedLabels = allowedCategories.map(getBucketAllowedTypeLabel).join(", ");
        return {
            valid: false,
            rejectedFiles,
            rejectedReason: `The following files are not allowed: ${rejectedFiles.join(", ")}. This bucket only accepts: ${allowedLabels}.`,
        };
    }

    return { valid: true, rejectedFiles: [], rejectedReason: "" };
};

/**
 * Get a user-friendly label of all accepted extensions for a bucket.
 * E.g. "PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, CSV, JSON"
 */
export const getAcceptedExtensionLabels = (
    allowedFileTypes?: string | null,
): string => {
    if (!allowedFileTypes || allowedFileTypes.trim() === "*") return "All files";

    const categories = parseBucketAllowedTypes(allowedFileTypes);
    if (categories.length === 0) return "All files";

    const extensions: string[] = [];
    for (const cat of categories) {
        const exts = CATEGORY_EXTENSIONS[cat];
        if (exts) {
            extensions.push(...exts.map((ext) => ext.toUpperCase()));
        }
    }

    return extensions.join(", ");
};

export const normalizeBucketAllowedType = (
    value?: string | null,
): BucketAllowedType | null => {
    if (!value) return null;
    const normalized = value.trim().toLowerCase().replace(/^\./, "");
    return (
        BUCKET_ALLOWED_TYPE_ALIASES[normalized] ??
        LEGACY_EXTENSION_MAP[normalized] ??
        null
    );
};

export const parseBucketAllowedTypes = (
    value?: string | null,
): BucketAllowedType[] => {
    if (!value) return [];

    const found = new Set<BucketAllowedType>();
    for (const token of value.split(",")) {
        const normalized = normalizeBucketAllowedType(token);
        if (normalized) {
            found.add(normalized);
        }
    }

    return BUCKET_ALLOWED_TYPE_ORDER.filter((type) => found.has(type));
};

export const serializeBucketAllowedTypes = (
    values: BucketAllowedType[],
): string => {
    const normalized = values
        .map((value) => normalizeBucketAllowedType(value))
        .filter((value): value is BucketAllowedType => value !== null);

    return BUCKET_ALLOWED_TYPE_ORDER.filter((type, index) => {
        return normalized.includes(type) && BUCKET_ALLOWED_TYPE_ORDER.indexOf(type) === index;
    }).join(",");
};

export const getBucketAllowedTypeLabel = (type: BucketAllowedType): string => {
    return BUCKET_ALLOWED_TYPE_LABELS[type];
};

export const formatBucketAllowedTypes = (value?: string | null): string => {
    const parsed = parseBucketAllowedTypes(value);
    if (parsed.length === 0) return "Not configured";
    return parsed.map(getBucketAllowedTypeLabel).join(", ");
};