import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import { z } from "zod";

import { ArtifactPanel } from "@/components/ArtifactPanel";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { extractErrorMessage } from "@/lib/api";
import {
  createLearner,
  learnerKey,
  learnersByRubricKey,
  type Learner,
  type LearnerCreatePayload,
} from "@/lib/learners";
import {
  createSubmission,
  evaluateSubmission,
  getSubmission,
  submissionKey,
} from "@/lib/submissions";

const schema = z.object({
  full_name: z
    .string()
    .min(1, "Full name is required")
    .max(200, "Must be 200 characters or fewer"),
  email: z.string().email("Enter a valid email").optional().or(z.literal("")),
  cohort: z.string().max(100, "Must be 100 characters or fewer").optional().or(z.literal("")),
});

type FormValues = z.infer<typeof schema>;

interface WizardState {
  learner: Learner;
  submissionId: string;
}

export function LearnerNewPage(): JSX.Element {
  const params = useParams<{ rubricId: string }>();
  const rubricId = params.rubricId ?? "";
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [wizard, setWizard] = useState<WizardState | null>(null);
  const [phaseAError, setPhaseAError] = useState<string | null>(null);
  const [evaluateError, setEvaluateError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: "", email: "", cohort: "" },
  });

  const phaseAMutation = useMutation({
    mutationFn: async (payload: LearnerCreatePayload): Promise<WizardState> => {
      const learner = await createLearner(rubricId, payload);
      const submission = await createSubmission(learner.id);
      return { learner, submissionId: submission.id };
    },
    onSuccess: async (state) => {
      setPhaseAError(null);
      setWizard(state);
      await queryClient.invalidateQueries({ queryKey: learnersByRubricKey(rubricId) });
    },
    onError: (err) => {
      setPhaseAError(extractErrorMessage(err, "Failed to create learner."));
    },
  });

  const submissionQuery = useQuery({
    queryKey: wizard ? submissionKey(wizard.submissionId) : ["submissions", "none"],
    queryFn: () => getSubmission(wizard!.submissionId),
    enabled: wizard !== null,
  });

  const evaluateMutation = useMutation({
    mutationFn: () => evaluateSubmission(wizard!.submissionId),
    onSuccess: async () => {
      if (!wizard) return;
      await queryClient.invalidateQueries({ queryKey: learnerKey(wizard.learner.id) });
      await queryClient.invalidateQueries({
        queryKey: submissionKey(wizard.submissionId),
      });
      navigate(`/learners/${wizard.learner.id}`, { replace: true });
    },
    onError: (err) => {
      setEvaluateError(extractErrorMessage(err, "Failed to start evaluation."));
    },
  });

  const onPhaseASubmit = (values: FormValues): void => {
    setPhaseAError(null);
    const payload: LearnerCreatePayload = {
      full_name: values.full_name,
      ...(values.email ? { email: values.email } : {}),
      ...(values.cohort ? { cohort: values.cohort } : {}),
    };
    phaseAMutation.mutate(payload);
  };

  if (!rubricId) {
    return (
      <div className="container py-8">
        <Alert variant="destructive">
          <AlertDescription>Missing rubric.</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (wizard === null) {
    return (
      <div className="container flex justify-center py-12">
        <Card className="w-full max-w-xl">
          <CardHeader>
            <CardTitle>Add learner</CardTitle>
            <CardDescription>
              Create a learner and then attach artifacts before evaluating.
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit(onPhaseASubmit)} noValidate>
            <CardContent className="space-y-4">
              {phaseAError ? (
                <Alert variant="destructive" data-testid="phase-a-error">
                  <AlertDescription>{phaseAError}</AlertDescription>
                </Alert>
              ) : null}
              <div className="space-y-2">
                <Label htmlFor="full_name">Full name</Label>
                <Input
                  id="full_name"
                  {...register("full_name")}
                  aria-invalid={errors.full_name ? "true" : "false"}
                />
                {errors.full_name ? (
                  <p className="text-xs text-destructive">{errors.full_name.message}</p>
                ) : null}
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email (optional)</Label>
                <Input id="email" type="email" {...register("email")} />
                {errors.email ? (
                  <p className="text-xs text-destructive">{errors.email.message}</p>
                ) : null}
              </div>
              <div className="space-y-2">
                <Label htmlFor="cohort">Cohort (optional)</Label>
                <Input id="cohort" {...register("cohort")} />
              </div>
            </CardContent>
            <CardFooter className="flex items-center justify-between">
              <Button variant="outline" type="button" asChild>
                <Link to={`/rubrics/${rubricId}`}>Cancel</Link>
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting || phaseAMutation.isPending}
                data-testid="phase-a-submit"
              >
                {phaseAMutation.isPending ? "Creating..." : "Continue"}
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    );
  }

  const artifacts = submissionQuery.data?.artifacts ?? [];
  const canEvaluate = artifacts.length > 0 && !evaluateMutation.isPending;

  return (
    <div className="container py-8">
      <div className="mb-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to={`/rubrics/${rubricId}`}>&larr; Back to rubric</Link>
        </Button>
      </div>
      <Alert className="mb-6" data-testid="phase-b-banner">
        <AlertTitle>Learner created</AlertTitle>
        <AlertDescription>
          <strong>{wizard.learner.full_name}</strong> was added to this rubric. Add
          artifacts below and start the evaluation when you are ready.
        </AlertDescription>
      </Alert>

      <ArtifactPanel
        submissionId={wizard.submissionId}
        artifacts={artifacts}
      />

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Evaluate</CardTitle>
          <CardDescription>
            Sends artifacts to n8n. The submission moves to processing and you will
            see the result on the learner page.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {evaluateError ? (
            <Alert variant="destructive" data-testid="evaluate-error">
              <AlertDescription>{evaluateError}</AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
        <CardFooter className="flex items-center justify-between">
          <Button variant="ghost" asChild>
            <Link to={`/learners/${wizard.learner.id}`}>Done for now</Link>
          </Button>
          <Button
            onClick={() => {
              setEvaluateError(null);
              evaluateMutation.mutate();
            }}
            disabled={!canEvaluate}
            data-testid="evaluate-button"
          >
            {evaluateMutation.isPending ? "Starting..." : "Start evaluation"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
