import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function resolveApiAssetUrl(path?: string | null) {
  if (!path) return null
  if (/^https?:\/\//i.test(path)) return path

  const baseUrl =
    (import.meta.env.VITE_BACKEND_URL as string | undefined) ??
    'http://localhost:8000'
  const normalizedBase = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${normalizedBase}${normalizedPath}`
}

export interface LinkMetadata {
  title?: string
  description?: string
  ogImage?: string
}

// In-memory cache for metadata
const metadataCache = new Map<string, LinkMetadata>()
const CACHE_KEY = 'link_metadata_cache'

// Load cache from localStorage on initialization
try {
  const cachedData = localStorage.getItem(CACHE_KEY)
  if (cachedData) {
    const parsed = JSON.parse(cachedData)
    Object.entries(parsed).forEach(([url, metadata]) => {
      metadataCache.set(url, metadata as LinkMetadata)
    })
  }
} catch (error) {
  console.error('Failed to load metadata cache:', error)
}

// Save cache to localStorage
function saveCache() {
  try {
    const cacheObject = Object.fromEntries(metadataCache.entries())
    localStorage.setItem(CACHE_KEY, JSON.stringify(cacheObject))
  } catch (error) {
    console.error('Failed to save metadata cache:', error)
  }
}

/**
 * Converts an image URL to a base64 data URI for caching
 * @param imageUrl - The image URL to convert
 * @returns Promise with base64 data URI or empty string if failed
 */
async function imageToBase64(imageUrl: string): Promise<string> {
  try {
    // Use CORS proxy to fetch the image
    const proxyUrl = `https://api.allorigins.win/raw?url=${encodeURIComponent(imageUrl)}`
    const response = await fetch(proxyUrl)
    const blob = await response.blob()

    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onloadend = () => resolve(reader.result as string)
      reader.onerror = reject
      reader.readAsDataURL(blob)
    })
  } catch (error) {
    console.error('Failed to convert image to base64:', error)
    return ''
  }
}

/**
 * Fetches metadata from a URL including title, description, and OG image
 * Uses a CORS proxy to bypass browser restrictions
 * Results are cached in memory and localStorage (including images as base64)
 * @param url - The URL to fetch metadata from
 * @returns Promise with the extracted metadata
 */
export async function fetchLinkMetadata(url: string): Promise<LinkMetadata> {
  // Check cache first
  if (metadataCache.has(url)) {
    console.log('📦 Using cached metadata for:', url)
    return metadataCache.get(url)!
  }

  try {
    console.log('🌐 Fetching metadata for:', url)

    // Use AllOrigins CORS proxy
    const proxyUrl = `https://api.allorigins.win/get?url=${encodeURIComponent(url)}`
    const response = await fetch(proxyUrl)
    const data = await response.json()

    // Parse the HTML
    const parser = new DOMParser()
    const doc = parser.parseFromString(data.contents, 'text/html')

    // Extract metadata with fallbacks
    const title =
      doc.querySelector('meta[property="og:title"]')?.getAttribute('content') ||
      doc.querySelector('meta[name="twitter:title"]')?.getAttribute('content') ||
      doc.querySelector('title')?.textContent ||
      new URL(url).hostname

    const description =
      doc.querySelector('meta[property="og:description"]')?.getAttribute('content') ||
      doc.querySelector('meta[name="twitter:description"]')?.getAttribute('content') ||
      doc.querySelector('meta[name="description"]')?.getAttribute('content') ||
      ''

    let ogImage =
      doc.querySelector('meta[property="og:image"]')?.getAttribute('content') ||
      doc.querySelector('meta[name="twitter:image"]')?.getAttribute('content') ||
      ''

    // Convert image to base64 for caching if it exists
    if (ogImage) {
      console.log('🖼️ Caching image for:', url)
      const base64Image = await imageToBase64(ogImage)
      if (base64Image) {
        ogImage = base64Image // Replace URL with base64 data URI
      }
    }

    const metadata: LinkMetadata = {
      title: title.trim(),
      description: description.trim(),
      ogImage: ogImage.trim()
    }

    // Cache the result
    metadataCache.set(url, metadata)
    saveCache()

    return metadata
  } catch (error) {
    console.error('Failed to fetch metadata:', error)
    const fallback = { title: new URL(url).hostname, description: '', ogImage: '' }

    // Cache the fallback to avoid repeated failures
    metadataCache.set(url, fallback)
    saveCache()

    return fallback
  }
}



export const getVersion = () => {
  return "2.0.3"
}

/**
 * Formats a date string or Date object into a readable format like "Jan 14, 2024"
 */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return "—";
  const d = new Date(date);
  if (isNaN(d.getTime())) return String(date);

  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Formats a date string or Date object into a relative time string like "2 mins ago"
 */
export function formatRelativeTime(date: string | Date | null | undefined): string {
  if (!date) return "—";
  const d = new Date(date);
  if (isNaN(d.getTime())) return String(date);

  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - d.getTime()) / 1000);

  // For future dates or just now
  if (diffInSeconds < 0) return "just now";
  if (diffInSeconds < 60) return `${diffInSeconds} sec ago`;

  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) return `${diffInMinutes} min${diffInMinutes !== 1 ? "s" : ""} ago`;

  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) return `${diffInHours} hour${diffInHours !== 1 ? "s" : ""} ago`;

  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays < 30) return `${diffInDays} day${diffInDays !== 1 ? "s" : ""} ago`;

  const diffInMonths = Math.floor(diffInDays / 30);
  if (diffInMonths < 12) return `${diffInMonths} month${diffInMonths !== 1 ? "s" : ""} ago`;

  const diffInYears = Math.floor(diffInMonths / 12);
  return `${diffInYears} year${diffInYears !== 1 ? "s" : ""} ago`;
}

/**
 * Truncates a filename after a certain number of characters while preserving the extension
 */
export function truncateFileName(name: string, maxLength: number = 18): string {
  if (name.length <= maxLength) return name;

  const lastDotIndex = name.lastIndexOf('.');
  if (lastDotIndex === -1) return `${name.slice(0, maxLength)}...`;

  const ext = name.slice(lastDotIndex);
  const baseName = name.slice(0, lastDotIndex);

  if (baseName.length <= maxLength) return name;

  return `${baseName.slice(0, maxLength)}...${ext}`;
}

/**
 * Formats bytes into a human-readable string (KB, MB, GB, etc.)
 */
export function formatBytes(bytes: number): string {
  if (bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let unitIndex = 0

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }

  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
}