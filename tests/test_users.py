import pytest
from unittest.mock import Mock, patch
from loop.kernel.users import UserManager

@pytest.fixture
def user_manager():
    # Use patch context managers properly with yield
    with patch("builtins.open", new_callable=Mock) as mock_open:
        with patch("os.path.exists", return_value=False):
            with patch.object(UserManager, "_load", return_value=None):
                with patch.object(UserManager, "_save", return_value=None):
                    um = UserManager()
                    um.users = {"root": {"password": "hashed_root", "roles": ["admin"]}}
                    yield um

def test_create_user(user_manager):
    success = user_manager.add_user("testuser", "password123")
    assert success
    assert "testuser" in user_manager.users

def test_authenticate(user_manager):
    user_manager.add_user("alice", "secret")
    assert user_manager.authenticate("alice", "secret")
    assert not user_manager.authenticate("alice", "wrong")
    assert not user_manager.authenticate("bob", "secret")

def test_roles_and_permissions(user_manager):
    user_manager.users["admin"] = {"roles": ["admin"]}
    user_manager.users["guest"] = {"roles": ["user"]}

    assert user_manager.has_permission("admin", "sys_reboot")
    assert not user_manager.has_permission("guest", "sys_reboot")
    assert not user_manager.has_permission("guest", "manage_network")
    assert user_manager.has_permission("guest", "use_network")

def test_role_management(user_manager):
    user_manager.add_user("u1", "p1")
    assert user_manager.get_roles("u1") == ["user"]

    user_manager.add_role("u1", "tester")
    assert "tester" in user_manager.get_roles("u1")

    user_manager.remove_role("u1", "tester")
    assert "tester" not in user_manager.get_roles("u1")

def test_duplicate_user(user_manager):
    user_manager.add_user("u1", "p1")
    assert user_manager.add_user("u1", "p2") is False

def test_delete_user(user_manager):
    user_manager.add_user("u2", "p2")
    assert user_manager.delete_user("u2")
    assert "u2" not in user_manager.users

    assert not user_manager.delete_user("u2")
    assert not user_manager.delete_user("root")

def test_permission_denied_actions(user_manager):
    user_manager.users["regular"] = {"roles": ["user"], "password": "x"}
    assert not user_manager.add_user("new", "pass", requestor="regular")

    user_manager.add_user("target", "pass")
    assert not user_manager.delete_user("target", requestor="regular")
