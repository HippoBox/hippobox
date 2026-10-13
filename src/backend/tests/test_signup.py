import pytest


@pytest.mark.parametrize("field,code", [("name", "NAME_ALREADY_EXISTS"), ("email", "EMAIL_ALREADY_EXISTS")])
def test_signup_conflict_and_retry(client, field, code):
    original = {"name": "original", "email": "original@example.com", "password": "Strong!123"}
    assert client.post("/api/v1/auth/signup", json=original).status_code == 200
    form = {**original, "name": "another", "email": "another@example.com"}
    form[field] = original[field]
    response = client.post("/api/v1/auth/signup", json=form)
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == code
    assert "SQL" not in response.text
    assert "example.com" not in response.text
    form.update(name="another", email="another@example.com")
    assert client.post("/api/v1/auth/signup", json=form).status_code == 200
    assert client.post("/api/v1/auth/login", json=form).status_code == 200


def test_signup_rolls_back_partial_account(client):
    from sqlalchemy import event

    from hippobox.core.database import get_engine

    engine = get_engine().sync_engine

    def fail_auth_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO auth_identities "):
            raise RuntimeError("simulated authentication storage failure")

    form = {"name": "retry", "email": "retry@example.com", "password": "Strong!123"}
    event.listen(engine, "before_cursor_execute", fail_auth_insert)
    try:
        response = client.post("/api/v1/auth/signup", json=form)
        assert response.status_code == 500
        assert response.json()["detail"] == {"error": "SIGNUP_FAILED", "message": "Failed to create the user account."}
    finally:
        event.remove(engine, "before_cursor_execute", fail_auth_insert)
    assert client.post("/api/v1/auth/signup", json=form).status_code == 200
    assert client.post("/api/v1/auth/login", json=form).status_code == 200


@pytest.mark.parametrize(
    "message,code",
    [
        ('duplicate key value violates unique constraint "user_email_key"', "EMAIL_ALREADY_EXISTS"),
        ('duplicate key value violates unique constraint "user_name_key"', "NAME_ALREADY_EXISTS"),
        ("NOT NULL constraint failed: user.email", "CREATE_FAILED"),
    ],
)
def test_integrity_error_mapping(message, code):
    from sqlalchemy.exc import IntegrityError

    from hippobox.errors.auth import user_integrity_exception

    error = user_integrity_exception(IntegrityError("private SQL", {"email": "private"}, Exception(message)))
    assert error.code.code == code
    assert "private" not in error.message
    assert message not in error.message


@pytest.mark.parametrize(
    "message,status,code",
    [
        ("UNIQUE constraint failed: user.name", 409, "NAME_ALREADY_EXISTS"),
        ("UNIQUE constraint failed: user.email", 409, "EMAIL_ALREADY_EXISTS"),
        ("unknown database constraint", 500, "SIGNUP_FAILED"),
    ],
)
def test_signup_service_translates_commit_conflicts(client, monkeypatch, message, status, code):
    from sqlalchemy.exc import IntegrityError

    from hippobox.platform.models.user import Users

    async def fail_commit(**kwargs):
        raise IntegrityError("private SQL", {"email": "private@example.com"}, Exception(message))

    monkeypatch.setattr(Users, "create_signup_user", fail_commit)
    response = client.post(
        "/api/v1/auth/signup", json={"name": "race", "email": "race@example.com", "password": "Strong!123"}
    )
    assert response.status_code == status
    assert response.json()["detail"]["error"] == code
    assert "private" not in response.text
    assert message not in response.text
