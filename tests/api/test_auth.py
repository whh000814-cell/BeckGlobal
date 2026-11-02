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
