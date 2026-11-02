import pytest
from fastapi import status
from fastapi.testclient import TestClient


def register_user(client: TestClient) -> dict:
    response = client.post(
        '/users/',
        json={
            'name': 'Taylor Smith',
            'email': 'taylor@example.com',
            'password': 'correct-horse-battery-staple',
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def login_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        '/auth/token',
        json={
            'email': 'taylor@example.com',
            'password': 'correct-horse-battery-staple',
        },
    )
    assert response.status_code == status.HTTP_200_OK
    return {'Authorization': f'Bearer {response.json()["access_token"]}'}


@pytest.mark.parametrize(
    ('method', 'path', 'json_body'),
    [
        ('get', '/users/', None),
        ('get', '/users/1', None),
        ('put', '/users/1', {'name': 'Updated Name'}),
        ('delete', '/users/1', None),
    ],
)
def test_user_management_routes_reject_anonymous_requests(
    client: TestClient,
    method: str,
    path: str,
    json_body: dict | None,
):
    register_user(client)

    response = client.request(method, path, json=json_body)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_registration_remains_public(client: TestClient):
    response = client.post(
        '/users/',
        json={
            'name': 'Public Registration',
            'email': 'public@example.com',
            'password': 'registration-password',
        },
    )

    assert response.status_code == status.HTTP_201_CREATED


def test_authenticated_user_can_list_and_read_users(client: TestClient):
    user = register_user(client)
    headers = login_headers(client)

    list_response = client.get('/users/', headers=headers)
    detail_response = client.get(f'/users/{user["id"]}', headers=headers)

    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.json() == [user]
    assert detail_response.status_code == status.HTTP_200_OK
    assert detail_response.json() == user
