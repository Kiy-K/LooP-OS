from fyodoros.plugins import Plugin
from fyodoros.kernel.users import UserManager

class TeamCollaborationPlugin(Plugin):
    """
    Team Collaboration plugin.
    Features: Role-Based Access Control (RBAC).
    """
    def setup(self, kernel):
        self.kernel = kernel
        # Monkeypatch UserManager.has_permission
        self.original_has_permission = UserManager.has_permission
        # Bind the method to the class effectively, but it's a bit tricky with instance methods.
        # Since UserManager.has_permission is a standard method (self, user, action),
        # and self._check_permission expects (self, user_manager_instance, user, action)
        # We need to make sure we replace it correctly.

        # When called as um.has_permission(user, action), 'um' is passed as first arg.
        # So we can just assign the function.
        # However, `self` in _check_permission refers to the Plugin instance, not the UserManager instance
        # if we assign it as a bound method of the plugin instance.
        # But we are assigning it to the UserManager CLASS.
        # So when um.has_permission is called, `um` is passed as the first argument.
        # But `_check_permission` is an instance method of `TeamCollaborationPlugin`.
        # So we need to wrap it.

        def wrapped_check_permission(um_instance, user, action):
             return self._check_permission(um_instance, user, action)

        UserManager.has_permission = wrapped_check_permission
        print("[TeamCollaboration] RBAC enabled.")

    def _check_permission(self, user_manager_instance, user, action):
        # Root is god
        if user == "root":
            return True

        roles = user_manager_instance.get_roles(user)

        # Policy Definition
        # Admin: everything
        if "admin" in roles:
            return True

        # User: restricted
        # Actions to restrict: create_user, delete_user, maybe system changes
        restricted_actions = ["create_user", "delete_user", "system_config"]
        if action in restricted_actions:
            return False

        return True

    def add_role(self, target_user, role):
        um = UserManager()
        return um.add_role(target_user, role)

    def remove_role(self, target_user, role):
        um = UserManager()
        return um.remove_role(target_user, role)

    def list_roles(self, target_user):
        um = UserManager()
        return um.get_roles(target_user)

    def get_shell_commands(self):
        return {
            "team_add_role": self.add_role,
            "team_remove_role": self.remove_role,
            "team_list_roles": self.list_roles
        }

    def get_agent_tools(self):
        return [
            {
                "name": "team_add_role",
                "description": "Add a role to a user. Args: user, role",
                "func": self.add_role
            },
            {
                "name": "team_remove_role",
                "description": "Remove a role from a user. Args: user, role",
                "func": self.remove_role
            },
            {
                "name": "team_list_roles",
                "description": "List roles for a user. Args: user",
                "func": self.list_roles
            }
        ]
