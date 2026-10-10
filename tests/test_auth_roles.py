"""Test authentication, login, logout, and role access security."""
from app.models.user import User


def test_user_password_hashing(app):
    with app.app_context():
        u = User(username="test_hash", email="test_hash@example.com", full_name="Hash User")
        u.set_password("secret_pass")
        assert u.password_hash != "secret_pass"
        assert u.check_password("secret_pass") is True
        assert u.check_password("wrong_pass") is False


def test_login_and_logout(client):
    # Valid login
    resp = client.post('/auth/login', data={'username': 'rec_test', 'password': 'password123'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Operations Overview" in resp.data

    # Logout
    resp_out = client.get('/auth/logout', follow_redirects=True)
    assert resp_out.status_code == 200
    assert b"Sign In" in resp_out.data


def test_invalid_login(client):
    resp = client.post('/auth/login', data={'username': 'rec_test', 'password': 'wrongpassword'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Invalid username or password" in resp.data


def test_unauthenticated_redirect(app):
    client = app.test_client()
    unauth_resp = client.get('/settings/', follow_redirects=False)
    assert unauth_resp.status_code == 302
    assert '/auth/login' in unauth_resp.headers['Location']


def test_receptionist_forbidden_admin_access(auth_client):
    # Receptionist accessing Admin-only users management should be 403 Forbidden
    resp = auth_client.get('/settings/users')
    assert resp.status_code == 403


def test_admin_access_allowed(admin_client):
    # Admin accessing settings users should succeed (200 OK)
    admin_resp = admin_client.get('/settings/users')
    assert admin_resp.status_code == 200
    assert b"Staff Accounts" in admin_resp.data
