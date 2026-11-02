# TradeQuote AI authentication foundation

## Goal

Complete the smallest usable authentication flow before adding customers, inquiries, or quotations.

A user can register, sign in with an email address and password, receive a short-lived JWT, and use that JWT to access authenticated user endpoints.

## Scope

- Keep `POST /users/` public for registration.
- Add `POST /auth/token` with a JSON body containing `email` and `password`.
- Return the existing `Token` response shape on successful authentication.
- Add `GET /users/me` to return the authenticated user.
- Make the existing list, detail, update, and delete user routes require a valid access token.
- Resolve the token subject to a real database user in `get_current_user`.
- Return `401` for missing, invalid, expired, or unknown-user tokens.
- Return the same `401` response for an unknown email and an incorrect password.
- Add focused API tests for registration, login, current-user access, and authentication failures.

## Out of scope

- Refresh tokens and logout revocation.
- Email verification and password reset.
- Administrator and employee roles.
- Fine-grained authorization between authenticated users.
- Customer, inquiry, quotation, product, attachment, and AI extraction features.
- Frontend login screens.

## Components

### Schemas

Add a login request schema with validated email and password fields. Keep the existing public-user and token response schemas. Configure the public-user schema explicitly for SQLAlchemy objects.

### Authentication route

Create an `/auth` router. The token endpoint looks up the user by email, verifies the bcrypt hash, and creates a JWT whose `sub` claim is the user's database ID represented as a string.

### Current-user dependency

Decode the bearer token, validate the `sub` claim, convert it to an integer user ID, and load the user from the database. Return the SQLAlchemy `User` object only when it exists. All authentication failures use HTTP 401 and include the standard `WWW-Authenticate: Bearer` header.

### Protected routes

Registration remains public. `GET /users/me` and the existing list, detail, update, and delete endpoints depend on the resolved current user. This phase establishes authentication only; role and ownership authorization will be designed separately before multi-user production use.

## Data flow

1. The client registers through `POST /users/`; the server stores only a bcrypt hash.
2. The client posts email and password to `POST /auth/token`.
3. The server verifies the credentials and returns a 30-minute JWT.
4. The client sends `Authorization: Bearer <token>`.
5. The dependency decodes the JWT and loads the corresponding user.
6. The protected route runs only after that user has been resolved.

## Error handling

- Duplicate registration email: `400` with the existing message.
- Invalid login credentials: `401 Invalid email or password`.
- Missing, malformed, expired, or unknown-user bearer token: `401 Could not validate credentials`.
- Existing user-not-found behavior remains `404` after authentication succeeds.

## Testing and acceptance

Tests use a temporary SQLite database with FastAPI dependency overrides so they do not change the developer or PostgreSQL databases.

Acceptance criteria:

1. Registration stores a bcrypt hash rather than the plaintext password.
2. Valid credentials return a bearer token.
3. Invalid credentials return 401 without identifying which credential was wrong.
4. A valid token returns the correct user from `GET /users/me`.
5. Missing, invalid, expired, and unknown-user tokens are rejected.
6. Protected user routes reject anonymous requests.
7. The focused test suite and lint checks pass.
