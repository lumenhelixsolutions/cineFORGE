const BASE_URL = "http://127.0.0.1:8765";

type JsonValue = Record<string, unknown> | Array<unknown> | string | number | boolean | null;

async function request<T = any>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function uploadFile<T = any>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  return (await response.json()) as T;
}

export const api = {
  diagnostics: () => request("/diagnostics"),
  capabilities: () => request("/capabilities"),
  prefabs: {
    stylePacks: () => request("/prefabs/style-packs"),
  },
  projects: {
    list: () => request("/projects"),
    get: (projectId: string) => request(`/projects/${projectId}`),
    create: (payload: JsonValue) =>
      request("/projects", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    update: (projectId: string, payload: JsonValue) =>
      request(`/projects/${projectId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    delete: (projectId: string) =>
      request(`/projects/${projectId}`, {
        method: "DELETE",
      }),
  },
  sources: {
    upload: (projectId: string, file: File) => uploadFile(`/projects/${projectId}/sources`, file),
  },
  director: {
    treatment: (projectId: string, payload: JsonValue = {}) =>
      request(`/projects/${projectId}/treatment`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    storyboard: (projectId: string, payload: JsonValue = {}) =>
      request(`/projects/${projectId}/storyboard`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
  render: {
    shots: (projectId: string, shotIds?: string[]) =>
      request(`/projects/${projectId}/render`, {
        method: "POST",
        body: JSON.stringify({ shot_ids: shotIds }),
      }),
    stitch: (projectId: string, outputName?: string) =>
      request(`/projects/${projectId}/stitch`, {
        method: "POST",
        body: JSON.stringify({ output_name: outputName ?? "master" }),
      }),
  },
  shots: {
    update: (projectId: string, shotId: string, payload: JsonValue) =>
      request(`/projects/${projectId}/shots/${shotId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
  },
  stackbuilder: {
    recommend: (payload: JsonValue) =>
      request("/stackbuilder/recommend", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
  trailer: {
    generate: (projectId: string) =>
      request(`/api/projects/${projectId}/generate-trailer`, { method: "POST" }),
    status: (projectId: string) =>
      request(`/api/projects/${projectId}/trailer-status`),
    download: (projectId: string) =>
      request(`/api/projects/${projectId}/trailer-download`),
  },
  broll: {
    generate: (sceneId: string) =>
      request(`/api/scenes/${sceneId}/generate-broll`, { method: "POST" }),
    generateAll: (projectId: string) =>
      request(`/api/projects/${projectId}/generate-all-broll`, { method: "POST" }),
    list: (sceneId: string) =>
      request(`/api/scenes/${sceneId}/broll`),
    download: (clipId: string) =>
      `${BASE_URL}/api/broll/${clipId}/download`,
  },
};
