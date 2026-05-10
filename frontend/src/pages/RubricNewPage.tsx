import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { z } from "zod";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { extractErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  createRubric,
  rubricsKey,
  type RubricCreatePayload,
  UNIQUE_NAME_REGEX,
} from "@/lib/rubrics";

const schema = z.object({
  unique_name: z
    .string()
    .min(1, "Required")
    .max(100, "Must be 100 characters or fewer")
    .regex(UNIQUE_NAME_REGEX, "Lowercase letters, digits, and hyphens only (no spaces)"),
  display_name: z
    .string()
    .min(1, "Required")
    .max(200, "Must be 200 characters or fewer"),
  description: z
    .string()
    .max(2000, "Must be 2000 characters or fewer")
    .optional()
    .or(z.literal("")),
  google_sheet_id: z
    .string()
    .max(200, "Must be 200 characters or fewer")
    .optional()
    .or(z.literal("")),
  google_drive_folder_path: z
    .string()
    .max(500, "Must be 500 characters or fewer")
    .optional()
    .or(z.literal("")),
});

type FormValues = z.infer<typeof schema>;

function isAdminRole(role: string): boolean {
  return role === "admin" || role === "superadmin";
}

export function RubricNewPage(): JSX.Element {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      unique_name: "",
      display_name: "",
      description: "",
      google_sheet_id: "",
      google_drive_folder_path: "",
    },
  });

  const mutation = useMutation({
    mutationFn: (payload: RubricCreatePayload) => createRubric(payload),
    onSuccess: async (rubric) => {
      await queryClient.invalidateQueries({ queryKey: rubricsKey });
      navigate(`/rubrics/${rubric.id}`, { replace: true });
    },
    onError: (err) => {
      setSubmitError(extractErrorMessage(err, "Failed to create rubric."));
    },
  });

  if (!user || !isAdminRole(user.role)) {
    return <Navigate to="/rubrics" replace />;
  }

  const onSubmit = (values: FormValues): void => {
    setSubmitError(null);
    const payload: RubricCreatePayload = {
      unique_name: values.unique_name,
      display_name: values.display_name,
      ...(values.description ? { description: values.description } : {}),
      ...(values.google_sheet_id ? { google_sheet_id: values.google_sheet_id } : {}),
      ...(values.google_drive_folder_path
        ? { google_drive_folder_path: values.google_drive_folder_path }
        : {}),
    };
    mutation.mutate(payload);
  };

  const busy = isSubmitting || mutation.isPending;

  return (
    <div className="container flex justify-center py-12">
      <Card className="w-full max-w-xl">
        <CardHeader>
          <CardTitle>New rubric</CardTitle>
          <CardDescription>
            The unique name is used by n8n to match incoming results, so it cannot
            be changed later.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <CardContent className="space-y-4">
            {submitError ? (
              <Alert variant="destructive" data-testid="rubric-new-error">
                <AlertDescription>{submitError}</AlertDescription>
              </Alert>
            ) : null}
            <div className="space-y-2">
              <Label htmlFor="unique_name">Unique name</Label>
              <Input
                id="unique_name"
                placeholder="e.g. fall-2026-cohort-a"
                {...register("unique_name")}
                aria-invalid={errors.unique_name ? "true" : "false"}
              />
              {errors.unique_name ? (
                <p className="text-xs text-destructive">{errors.unique_name.message}</p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Lowercase letters, digits, and hyphens. Cannot be changed later.
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="display_name">Display name</Label>
              <Input
                id="display_name"
                {...register("display_name")}
                aria-invalid={errors.display_name ? "true" : "false"}
              />
              {errors.display_name ? (
                <p className="text-xs text-destructive">{errors.display_name.message}</p>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Textarea id="description" rows={3} {...register("description")} />
              {errors.description ? (
                <p className="text-xs text-destructive">{errors.description.message}</p>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="google_sheet_id">Google Sheet ID (optional)</Label>
              <Input id="google_sheet_id" {...register("google_sheet_id")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="google_drive_folder_path">
                Google Drive folder path (optional)
              </Label>
              <Input
                id="google_drive_folder_path"
                {...register("google_drive_folder_path")}
              />
            </div>
          </CardContent>
          <CardFooter className="flex items-center justify-between">
            <Button variant="outline" type="button" asChild>
              <Link to="/rubrics">Cancel</Link>
            </Button>
            <Button type="submit" disabled={busy}>
              {busy ? "Creating..." : "Create rubric"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
