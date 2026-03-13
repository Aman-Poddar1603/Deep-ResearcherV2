import axios, { AxiosError } from "axios";

const backendUrl =
  (import.meta.env.VITE_BACKEND_URL as string | undefined) ??
  "http://localhost:8000";

/**
 * Core axios instance used by all helpers.
 * - baseURL is set from env or defaults to localhost
 * - you can add interceptors here for auth, logging, etc.
 */
const api = axios.create({
  baseURL: backendUrl,
  // Optionally tune timeouts or other axios defaults here
  // timeout: 15000,
});

/**
 * Simple request wrapper to normalize errors and return typed data.
 */
async function handleRequest<T>(promise: Promise<any>): Promise<T> {
  try {
    const res = await promise;
    return res.data as T;
  } catch (err) {
    if (axios.isAxiosError(err)) {
      const axiosErr = err as AxiosError<any>;
      // Try to extract useful server-side error message
      const serverMessage =
        axiosErr.response?.data?.detail ||
        axiosErr.response?.data?.message ||
        axiosErr.response?.data ||
        axiosErr.message;
      throw new Error(String(serverMessage));
    }
    // Fallback
    throw err;
  }
}

/**
 * Workspace-related types.
 * These are lightweight client-side representations that match what the backend exposes.
 * Adjust these types if your backend models differ.
 */
export interface WorkspaceCreate {
  name: string;
  description?: string;
  // optional "icon" identifier (string name key) used by the UI
  icon?: string | null;
  // optional accent color identifier
  accentColor?: string | null;
  aiMode?: string;
  enableResearch?: boolean;
  enableChat?: boolean;
  // NOTE: bannerImage and resources (files) are handled specially by createWorkspace when present
}

export interface WorkspacePatch {
  name?: string;
  description?: string;
  icon?: string | null;
  accentColor?: string | null;
  aiMode?: string;
  enableResearch?: boolean;
  enableChat?: boolean;
}

export interface WorkspaceOut {
  id: string;
  name: string;
  description?: string;
  icon?: string | null;
  accentColor?: string | null;
  aiMode?: string;
  enableResearch?: boolean;
  enableChat?: boolean;
  bannerUrl?: string | null;
  // backend may return created/updated timestamps or other metadata
  createdAt?: string;
  updatedAt?: string;
}

/**
 * Option bag accepted by the UI when creating a workspace.
 * It includes files (banner + resources) in addition to the workspace JSON payload.
 */
export interface CreateWorkspacePayload extends WorkspaceCreate {
  bannerImage?: File | null;
  resources?: File[]; // optional array of files
}

/**
 * Get all workspaces.
 */
export const getAllWorkspaces = async (): Promise<WorkspaceOut[]> => {
  return handleRequest<WorkspaceOut[]>(api.get("/workspace"));
};

/**
 * Get a single workspace by id.
 */
export const getWorkspaceById = async (id: string): Promise<WorkspaceOut> => {
  return handleRequest<WorkspaceOut>(
    api.get(`/workspace/${encodeURIComponent(id)}`),
  );
};

/**
 * Create a workspace.
 *
 * If `bannerImage` or `resources` are provided this helper will send a multipart/form-data request so files can be uploaded.
 * Otherwise a standard JSON POST is used.
 *
 * The backend's create endpoint expects a `WorkspaceCreate` body; when files are sent we append fields to FormData as strings.
 */
export const createWorkspace = async (
  payload: CreateWorkspacePayload,
): Promise<WorkspaceOut> => {
  const { bannerImage, resources, ...jsonFields } = payload;

  // If there are files, send multipart/form-data
  const hasFiles = Boolean(bannerImage) || (resources && resources.length > 0);

  if (hasFiles) {
    const form = new FormData();

    // Append scalar fields
    Object.entries(jsonFields).forEach(([key, value]) => {
      // Only append defined values
      if (value !== undefined && value !== null) {
        // Convert booleans/numbers to strings as FormData only supports string/blob
        form.append(key, String(value));
      }
    });

    // Append banner image if present
    if (bannerImage) {
      // Backend must accept this field name — adjust if your backend expects a different key
      form.append("bannerImage", bannerImage, bannerImage.name);
    }

    // Append resource files (multiple)
    if (resources && resources.length > 0) {
      resources.forEach((file) => {
        // Backend must accept repeated 'resources' fields for multiple files
        form.append("resources", file, file.name);
      });
    }

    // axios will set the correct Content-Type with boundary when sending FormData
    return handleRequest<WorkspaceOut>(
      api.post("/workspace", form, {
        headers: {
          // Let the browser/axios set the multipart boundary content-type
        },
      }),
    );
  }

  // Otherwise send JSON body
  return handleRequest<WorkspaceOut>(api.post("/workspace", jsonFields));
};

/**
 * Replace (PUT) a workspace by id. Sends a JSON body.
 */
export const updateWorkspace = async (
  id: string,
  payload: WorkspaceCreate,
): Promise<WorkspaceOut> => {
  return handleRequest<WorkspaceOut>(
    api.put(`/workspace/${encodeURIComponent(id)}`, payload),
  );
};

/**
 * Patch (partial update) a workspace by id.
 */
export const patchWorkspace = async (
  id: string,
  payload: WorkspacePatch,
): Promise<WorkspaceOut> => {
  return handleRequest<WorkspaceOut>(
    api.patch(`/workspace/${encodeURIComponent(id)}`, payload),
  );
};

/**
 * Delete a workspace by id.
 */
export const deleteWorkspace = async (id: string): Promise<void> => {
  await handleRequest<void>(api.delete(`/workspace/${encodeURIComponent(id)}`));
};

/**
 * Optional: simple helper to set auth token for subsequent requests.
 * The UI can call setAuthToken(token) after login.
 */
export const setAuthToken = (token: string | null) => {
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common["Authorization"];
  }
};

export default api;
