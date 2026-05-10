# Instructions for Claude Code

Build the RubricIQ project as specified in `SPEC.md` in this repository root.

## Operating rules

1. **Read `SPEC.md` first and treat it as the source of truth.** Do not deviate from the stack, data model, or contracts. If something is genuinely missing or ambiguous, ask before inventing it.

2. **Follow the build order in SPEC.md section "Build order".** Complete each step end-to-end (code + tests + manual verification instructions) before moving to the next. Do not jump ahead.

3. **Plan mode first.** Before writing any code, produce a plan: list the files you will create or modify in this step, the key design decisions, and any open questions. Wait for my approval before writing code.

4. **Style preferences:**
   - Use regular hyphens or parentheses, not em dashes
   - Concise prose in docs and comments
   - Type hints everywhere in Python (3.12 syntax: `str | None`, not `Optional[str]`)
   - TypeScript strict mode in the frontend

5. **Testing:**
   - pytest for backend, with a real Postgres (use `pytest-postgresql` or a docker-compose test DB)
   - Vitest + React Testing Library for frontend
   - Each feature gets at least one happy-path test and one auth/permission test
   - Do not stub n8n in tests; mock the HTTP client at the boundary

6. **Security and correctness over cleverness.** When in doubt, pick the boring, well-understood option (bcrypt, HS256 JWTs, SQLAlchemy ORM, FastAPI dependencies for auth). No exotic patterns.

7. **Commits:**
   - One commit per logical step
   - Conventional Commits format (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`, `infra:`)
   - Never commit secrets, `.env`, `terraform.tfvars`, or `__pycache__`

8. **When uncertain, stop and ask.** Especially around: data model changes, API contract changes, deployment configuration, anything touching secrets. Better to pause for a question than to silently make a choice I have to undo.

## Starting point

Begin with Step 1 of the build order: backend skeleton.

Produce the plan for Step 1 only. Wait for approval.
