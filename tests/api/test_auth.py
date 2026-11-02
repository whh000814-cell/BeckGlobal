from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User


def register_user(client: TestClient) -> dict:
    response = client.post(
        '/users/',
        json={
            'name': 'Taylor Smith',
            'email': 'taylor@example.com',
            'password': 'correct-horse-battery-staple',
        },
    )
    assert response.status_code == 201
    return response.json()


def login_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        '/auth/token',
        json={
            'email': 'taylor@example.com',
            'password': 'correct-horse-battery-staple',
        },
    )
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def test_login_returns_bearer_token_and_registration_hashes_password(
    client: TestClient,
    db_session: Session,
):
    user = register_user(client)

    stored_user = db_session.query(User).filter(User.id == user['id']).one()
    assert stored_user.password != 'correct-horse-battery-staple'

    response = client.post(
        '/auth/token',
        json={
            'email': 'taylor@example.com',
            'password': 'correct-horse-battery-staple',
        },
    )

    assert response.status_code == 200
    assert response.json()['token_type'] == 'bearer'
    payload = jwt.decode(
        response.json()['access_token'],
        settings.secret_key,
        algorithms=[settings.algorithm],
    )
    assert payload['sub'] == str(user['id'])


@pytest.mark.parametrize(
    ('email', 'password'),
    [
        ('unknown@example.com', 'correct-horse-battery-staple'),
        ('taylor@example.com', 'wrong-password'),
    ],
)
def test_login_rejects_invalid_credentials_without_disclosing_which_failed(
    client: TestClient,
    email: str,
    password: str,
):
    register_user(client)

    response = client.post(
        '/auth/token',
        json={'email': email, 'password': password},
    )

    assert response.status_code == 401
    assert response.json() == {'detail': 'Invalid email or password'}
    assert response.headers['www-authenticate'] == 'Bearer'


def test_current_user_returns_database_user(client: TestClient):
    user = register_user(client)

    response = client.get('/users/me', headers=login_headers(client))

    assert response.status_code == 200
    assert response.json() == {
        'id': user['id'],
        'name': 'Taylor Smith',
        'email': 'taylor@example.com',
    }


@pytest.mark.parametrize(
    'token',
    [
        'not-a-jwt',
        jwt.encode(
            {
                'sub': '1',
                'exp': datetime.now(timezone.utc) - timedelta(minutes=1),
            },
            'test-secret-key',
            algorithm='HS256',
        ),
        jwt.encode(
            {
                'sub': '999999',
                'exp': datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            'test-secret-key',
            algorithm='HS256',
        ),
    ],
    ids=['invalid_token', 'expired_token', 'missing_user'],
)
def test_current_user_rejects_unresolvable_identity(
    client: TestClient,
    token: str,
):
    response = client.get(
        '/users/me',
        headers={'Authorization': f'Bearer {token}'},
    )

    assert response.status_code == 401
    assert response.json() == {'detail': 'Could not validate credentials'}
    assert response.headers['www-authenticate'] == 'Bearer'
