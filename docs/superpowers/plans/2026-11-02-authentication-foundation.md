# Authentication Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tested email/password login flow, database-backed current-user resolution, and bearer-token protection for user-management routes.

**Architecture:** A focused `/auth` router authenticates credentials and issues the existing JWT token shape. A shared FastAPI dependency validates bearer tokens and loads a real `User`; user routes reuse that dependency. API tests replace the production database dependency with an isolated in-memory SQLite database.

**Tech Stack:** Python 3.12, FastAPI 0.139, SQLAlchemy 2, Pydantic 2, bcrypt, PyJWT, pytest, FastAPI TestClient.

## Global Constraints

- Keep `POST /users/` public.
- Use a JSON request containing `email` and `password` for `POST /auth/token`.
- Keep access tokens short-lived using the existing 30-minute setting.
- Use one generic 401 response for unknown email and incorrect password.
- Do not add refresh tokens, logout revocation, roles, password reset, email verification, or TradeQuote business entities.
- Tests must not change `dev.db` or the PostgreSQL database.

---

### Task 1: Isolated API Test Foundation and Login Contract

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/api/test_auth.py`
- Modify: `app/api/schemas.py`
- Create: `app/api/routes/auth.py`
- Modify: `app/api/router.py`

**Interfaces:**
- Produces: `LoginRequest(email: EmailStr, password: str)`.
- Produces: `POST /auth/token -> Token` with `{access_token, token_type}`.
- Consumes: `verify_password(plain_password: str, hashed_password: str) -> bool` and `create_access_token(data: dict) -> str`.

- [ ] **Step 1: Create an isolated database fixture**

Create an in-memory SQLite engine using `StaticPool`, create all metadata, override `get_db`, and return a `TestClient`. Import `app.models.user` before `Base.metadata.create_all()` so the users table is registered. Set `settings.secret_key` to a non-empty test value for deterministic JWT tests.

- [ ] **Step 2: Write failing login tests**

Add tests that register a user, confirm the stored password is not plaintext, log in successfully, decode the returned token, and assert `sub` equals the registered ID as a string. Add parametrized invalid-credential cases for unknown email and incorrect password; both must return `401`, `{"detail": "Invalid email or password"}`, and `WWW-Authenticate: Bearer`.

- [ ] **Step 3: Run the login tests and verify RED**

Run: `poetry run pytest tests/api/test_auth.py -vv`

Expected: failures because `/auth/token` does not exist.

- [ ] **Step 4: Implement the minimal login endpoint**

Add `LoginRequest` and explicit `ConfigDict(from_attributes=True)` support to `UserPublic`. Create an auth router that queries `User.email`, checks bcrypt, raises the generic 401 response for either invalid case, and returns `Token(access_token=create_access_token({'sub': str(user.id)}))`. Register the auth router.

- [ ] **Step 5: Run the login tests and verify GREEN**

Run: `poetry run pytest tests/api/test_auth.py -vv`

Expected: all login tests pass.

- [ ] **Step 6: Commit the login slice**

Run:

```text
git add tests/conftest.py tests/api/test_auth.py app/api/schemas.py app/api/routes/auth.py app/api/router.py
git commit -m "feat: add email login endpoint"
```

---

### Task 2: Database-Backed Current User

**Files:**
- Modify: `tests/api/test_auth.py`
- Modify: `app/api/dependencies.py`
- Modify: `app/api/routes/users.py`

**Interfaces:**
- Produces: `get_current_user(...) -> User`.
- Produces: `GET /users/me -> UserPublic`.
- Consumes: JWT `sub` as a string representation of an integer user ID.

- [ ] **Step 1: Write failing current-user tests**

Add a helper that registers and logs in a user. Test that its bearer token returns the correct ID, name, and email from `GET /users/me`. Add cases for a malformed token, an expired token, and a valid token whose `sub` references a missing user; each must return `401`, `{"detail": "Could not validate credentials"}`, and `WWW-Authenticate: Bearer`.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `poetry run pytest tests/api/test_auth.py -k "current_user or invalid_token or expired_token or missing_user" -vv`

Expected: failures because `/users/me` does not exist and the dependency does not load users.

- [ ] **Step 3: Implement database-backed identity resolution**

Change `get_current_user` to decode the token, require an integer-compatible `sub`, query `User.id`, and return the model. Map decode, subject, and lookup failures to the standard bearer 401 response. Add `GET /users/me` before `GET /users/{user_id}` so `me` is not parsed as an integer path parameter.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `poetry run pytest tests/api/test_auth.py -vv`

Expected: all authentication and current-user tests pass.

- [ ] **Step 5: Commit current-user resolution**

Run:

```text
git add tests/api/test_auth.py app/api/dependencies.py app/api/routes/users.py
git commit -m "feat: resolve authenticated users"
```

---

### Task 3: Protect Existing User-Management Routes

**Files:**
- Create: `tests/api/test_users.py`
- Modify: `app/api/routes/users.py`

**Interfaces:**
- Consumes: `get_current_user(...) -> User` as a route dependency.
- Preserves: public `POST /users/` registration.
- Protects: `GET /users/`, `GET /users/{user_id}`, `PUT /users/{user_id}`, and `DELETE /users/{user_id}`.

- [ ] **Step 1: Write failing route-protection tests**

Parametrize anonymous requests across list, detail, update, and delete operations and assert each returns `401`. Also assert anonymous registration still succeeds and authenticated list/detail access succeeds.

- [ ] **Step 2: Run protection tests and verify RED**

Run: `poetry run pytest tests/api/test_users.py -vv`

Expected: existing management routes accept anonymous requests, so the protection assertions fail.

- [ ] **Step 3: Add the authentication dependency**

Add `Depends(get_current_user)` to each existing management route without changing its response or database behavior. Do not add it to registration.

- [ ] **Step 4: Run protection tests and verify GREEN**

Run: `poetry run pytest tests/api/test_users.py -vv`

Expected: all user route tests pass.

- [ ] **Step 5: Commit route protection**

Run:

```text
git add tests/api/test_users.py app/api/routes/users.py
git commit -m "feat: protect user management routes"
```

---

### Task 4: Full Verification

**Files:**
- Modify only if verification reveals an authentication-scope defect; any fix must begin with a failing regression test.

**Interfaces:**
- Verifies every interface produced by Tasks 1-3.

- [ ] **Step 1: Run the complete test suite**

Run: `poetry run pytest -vv`

Expected: all tests pass with zero failures.

- [ ] **Step 2: Run lint checks**

Run: `poetry run ruff check app tests`

Expected: exit code 0 with no lint errors.

- [ ] **Step 3: Run format verification**

Run: `poetry run ruff format --check app tests`

Expected: exit code 0 with all files already formatted.

- [ ] **Step 4: Review the final diff and repository status**

Run: `git diff HEAD~3 --check` and `git status --short`.

Expected: no whitespace errors and no unintended files.

- [ ] **Step 5: Record verified boundaries in the handoff**

Report test and lint counts, changed files, and the explicit boundary that authenticated users are not yet separated by roles or ownership rules.
