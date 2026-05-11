import axios, { AxiosHeaders, type AxiosResponse } from "axios";

import { api, getStoredToken } from "@/lib/api";

export type ArtifactType = "loom" | "gdrive_video" | "github" | "screenshot" | "text";
export type FileArtifactType = "screenshot";
export type LinkArtifactType = "loom" | "gdrive_video" | "github";

export interface Artifact {
  id: string;
  submission_id: string;
  type: ArtifactType;
  filename: string | null;
  external_url: string | null;
  text_value: string | null;
  size_bytes: number | null;
  created_at: string;
}

export const FILE_ACCEPT: Record<FileArtifactType, string> = {
  screenshot: ".png,.jpg,.jpeg",
};

export async function uploadFiles(
  submissionId: string,
  type: FileArtifactType,
  files: File[],
): Promise<Artifact[]> {
  // axios + FormData hangs under jsdom test envs, so multipart uploads go
  // through fetch directly. We still reuse the axios baseURL and bearer
  // token so behaviour matches the rest of the app, and shape the failure
  // path as an AxiosError so callers can use extractErrorMessage.
  const fd = new FormData();
  fd.append("type", type);
  for (const f of files) fd.append("files", f);

  const baseURL = (api.defaults.baseURL ?? "").replace(/\/$/, "");
  const url = `${baseURL}/submissions/${submissionId}/artifacts`;
  const token = getStoredToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  const resp = await fetch(url, { method: "POST", body: fd, headers });
  if (!resp.ok) {
    let detail: unknown = undefined;
    try {
      detail = await resp.json();
    } catch {
      // ignore non-JSON error bodies
    }
    const config = { headers: new AxiosHeaders() };
    const response: AxiosResponse = {
      data: detail,
      status: resp.status,
      statusText: resp.statusText,
      headers: {},
      config,
    };
    throw new axios.AxiosError(
      `Request failed with status code ${resp.status}`,
      String(resp.status),
      config,
      undefined,
      response,
    );
  }
  return (await resp.json()) as Artifact[];
}

export interface ArtifactLinkPayload {
  type: LinkArtifactType;
  url: string;
}

export async function addLinks(
  submissionId: string,
  links: ArtifactLinkPayload[],
): Promise<Artifact[]> {
  const resp = await api.post<Artifact[]>(
    `/submissions/${submissionId}/artifacts/links`,
    { links },
  );
  return resp.data;
}

export async function addText(
  submissionId: string,
  value: string,
): Promise<Artifact> {
  const resp = await api.post<Artifact>(
    `/submissions/${submissionId}/artifacts/text`,
    { value },
  );
  return resp.data;
}

export async function deleteArtifact(
  submissionId: string,
  artifactId: string,
): Promise<void> {
  await api.delete(`/submissions/${submissionId}/artifacts/${artifactId}`);
}
