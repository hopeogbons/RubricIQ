import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { extractErrorMessage } from "@/lib/api";
import {
  addLinks,
  addText,
  deleteArtifact,
  FILE_ACCEPT,
  uploadFiles,
  type Artifact,
  type FileArtifactType,
  type LinkArtifactType,
} from "@/lib/artifacts";
import { submissionKey } from "@/lib/submissions";

interface ArtifactPanelProps {
  submissionId: string;
  artifacts: Artifact[];
}

const LINK_TYPES: { value: LinkArtifactType; label: string }[] = [
  { value: "github", label: "GitHub" },
  { value: "loom", label: "Loom" },
  { value: "gdrive_video", label: "Google Drive video" },
];

function describeArtifact(a: Artifact): string {
  if (a.filename) return a.filename;
  if (a.external_url) return a.external_url;
  if (a.text_value) {
    const truncated = a.text_value.length > 80
      ? `${a.text_value.slice(0, 80)}...`
      : a.text_value;
    return truncated;
  }
  return a.id;
}

function typeLabel(type: Artifact["type"]): string {
  switch (type) {
    case "screenshot":
      return "Screenshot";
    case "loom":
      return "Loom";
    case "gdrive_video":
      return "Google Drive video";
    case "github":
      return "GitHub";
    case "text":
      return "Text note";
  }
}

export function ArtifactPanel({
  submissionId,
  artifacts,
}: ArtifactPanelProps): JSX.Element {
  const queryClient = useQueryClient();
  const [opError, setOpError] = useState<string | null>(null);
  const [linkType, setLinkType] = useState<LinkArtifactType>("github");
  const [linkUrl, setLinkUrl] = useState("");
  const [textValue, setTextValue] = useState("");
  const screenshotInputRef = useRef<HTMLInputElement>(null);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: submissionKey(submissionId) });

  const uploadMutation = useMutation({
    mutationFn: ({ type, files }: { type: FileArtifactType; files: File[] }) =>
      uploadFiles(submissionId, type, files),
    onSuccess: async () => {
      setOpError(null);
      await invalidate();
    },
    onError: (err) => setOpError(extractErrorMessage(err, "Upload failed.")),
  });

  const linkMutation = useMutation({
    mutationFn: (payload: { type: LinkArtifactType; url: string }) =>
      addLinks(submissionId, [payload]),
    onSuccess: async () => {
      setOpError(null);
      setLinkUrl("");
      await invalidate();
    },
    onError: (err) => setOpError(extractErrorMessage(err, "Failed to add link.")),
  });

  const textMutation = useMutation({
    mutationFn: (value: string) => addText(submissionId, value),
    onSuccess: async () => {
      setOpError(null);
      setTextValue("");
      await invalidate();
    },
    onError: (err) => setOpError(extractErrorMessage(err, "Failed to add text.")),
  });

  const deleteMutation = useMutation({
    mutationFn: (artifactId: string) => deleteArtifact(submissionId, artifactId),
    onSuccess: async () => {
      setOpError(null);
      await invalidate();
    },
    onError: (err) => setOpError(extractErrorMessage(err, "Delete failed.")),
  });

  const handleFiles = (
    type: FileArtifactType,
    inputRef: React.RefObject<HTMLInputElement>,
    fileList: FileList | null,
  ): void => {
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList);
    setOpError(null);
    uploadMutation.mutate(
      { type, files },
      {
        onSettled: () => {
          if (inputRef.current) inputRef.current.value = "";
        },
      },
    );
  };

  const submitLink = (): void => {
    const trimmed = linkUrl.trim();
    if (!trimmed) {
      setOpError("Enter a URL.");
      return;
    }
    setOpError(null);
    linkMutation.mutate({ type: linkType, url: trimmed });
  };

  const submitText = (): void => {
    const trimmed = textValue.trim();
    if (!trimmed) {
      setOpError("Enter some text.");
      return;
    }
    setOpError(null);
    textMutation.mutate(trimmed);
  };

  return (
    <Card data-testid="artifact-panel">
      <CardHeader>
        <CardTitle>Artifacts</CardTitle>
        <CardDescription>
          Add screenshots, links (Loom, Google Drive video, GitHub), or a text note
          before evaluating. You can change them while the submission is in draft.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {opError ? (
          <Alert variant="destructive" data-testid="artifact-error">
            <AlertDescription>{opError}</AlertDescription>
          </Alert>
        ) : null}

        <div>
          {artifacts.length === 0 ? (
            <p
              className="text-sm text-muted-foreground"
              data-testid="artifact-list-empty"
            >
              No artifacts yet.
            </p>
          ) : (
            <ul className="divide-y rounded-md border" data-testid="artifact-list">
              {artifacts.map((a) => (
                <li
                  key={a.id}
                  className="flex items-center justify-between gap-3 px-3 py-2 text-sm"
                  data-testid={`artifact-${a.id}`}
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{typeLabel(a.type)}</p>
                    <p className="truncate font-mono text-xs text-muted-foreground">
                      {describeArtifact(a)}
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteMutation.mutate(a.id)}
                    disabled={deleteMutation.isPending}
                    data-testid={`delete-artifact-${a.id}`}
                  >
                    Remove
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="upload-screenshot">Screenshots</Label>
          <input
            ref={screenshotInputRef}
            id="upload-screenshot"
            data-testid="upload-screenshot"
            type="file"
            multiple
            accept={FILE_ACCEPT.screenshot}
            className="block w-full text-sm"
            onChange={(e) =>
              handleFiles("screenshot", screenshotInputRef, e.target.files)
            }
            disabled={uploadMutation.isPending}
          />
          <p className="text-xs text-muted-foreground">PNG, JPG, JPEG. Multiple files allowed.</p>
        </div>

        <div className="space-y-2">
          <Label>Add a link</Label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <select
              data-testid="link-type"
              value={linkType}
              onChange={(e) => setLinkType(e.target.value as LinkArtifactType)}
              className="h-9 rounded-md border border-input bg-transparent px-3 text-sm"
            >
              {LINK_TYPES.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <Input
              type="url"
              placeholder="https://..."
              value={linkUrl}
              onChange={(e) => setLinkUrl(e.target.value)}
              data-testid="link-url"
            />
            <Button
              type="button"
              variant="secondary"
              onClick={submitLink}
              disabled={linkMutation.isPending}
              data-testid="add-link-button"
            >
              Add link
            </Button>
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="text-note">Add a text note</Label>
          <Textarea
            id="text-note"
            data-testid="text-note"
            rows={3}
            placeholder="Free-form notes the evaluator should see..."
            value={textValue}
            onChange={(e) => setTextValue(e.target.value)}
          />
          <div className="flex justify-end">
            <Button
              type="button"
              variant="secondary"
              onClick={submitText}
              disabled={textMutation.isPending}
              data-testid="add-text-button"
            >
              Add text
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
