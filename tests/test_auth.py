"""
Tests for app.routes.auth -- registration and login endpoints.
"""


def test_register_new_user_succeeds(client):
    response = client.post(
        "/auth/register", json={"username": "alice", "password": "supersecret123"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice"
    assert "id" in body
    assert "password" not in body  # never echo the password back


def test_register_duplicate_username_fails(client):
    client.post("/auth/register", json={"username": "bob", "password": "supersecret123"})
    response = client.post(
        "/auth/register", json={"username": "bob", "password": "anotherpassword456"}
    )
    assert response.status_code == 409


def test_register_short_password_fails_validation(client):
    response = client.post("/auth/register", json={"username": "carol", "password": "short"})
    assert response.status_code == 422


def test_login_with_correct_credentials_returns_token(client):
    client.post("/auth/register", json={"username": "dave", "password": "supersecret123"})
    response = client.post(
        "/auth/login", json={"username": "dave", "password": "supersecret123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_with_wrong_password_fails(client):
    client.post("/auth/register", json={"username": "erin", "password": "supersecret123"})
    response = client.post("/auth/login", json={"username": "erin", "password": "wrongpassword"})
    assert response.status_code == 401


def test_login_with_nonexistent_user_fails(client):
    response = client.post(
        "/auth/login", json={"username": "doesnotexist", "password": "whatever123"}
    )
    assert response.status_code == 401


def test_login_error_message_does_not_distinguish_user_existence(client):
    """Both 'wrong password' and 'user doesn't exist' should return the same
    generic error, so the API doesn't leak which usernames are registered."""
    client.post("/auth/register", json={"username": "frank", "password": "supersecret123"})

    wrong_password_response = client.post(
        "/auth/login", json={"username": "frank", "password": "wrongpassword"}
    )
    nonexistent_user_response = client.post(
        "/auth/login", json={"username": "ghost", "password": "whatever123"}
    )

    assert wrong_password_response.json()["detail"] == nonexistent_user_response.json()["detail"]
