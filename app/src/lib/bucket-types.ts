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
    zip: "other",
    rar: "other",
    xml: "other",
    yaml: "other",
    yml: "other",
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