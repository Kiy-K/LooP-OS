# bin/user.py
import json

def main(args, sys):
    """
    User Management App.
    Usage:
      run user list
      run user add <username> <password>
      run user delete <username>
    """
    if not args:
        return json.dumps({"error": "No command provided."})

    cmd = args[0]

    # We need to access UserManager. SyscallHandler handles authentication but not management directly in current API.
    # We need to extend SyscallHandler or access UserManager via sys?
    # sys is SyscallHandler instance.

    # Check if SyscallHandler has user management exposed?
    # Not yet. We need to add sys_add_user / sys_delete_user to SyscallHandler first.
    # Or, if we are 'root' (checked by kernel), we can perhaps access internals?
    # No, we must use syscalls.

    # Let's assume syscalls will be added.
    if cmd == "list":
        # We can use dom state or add sys_user_list
        # sys.sys_get_state includes users list? Yes.
        # But let's ask for specific list syscall if we want to follow pattern.
        # For now, rely on sys_get_state() or the one we added in UserManager.
        # Wait, sys_get_state calls user_manager.list_users()
        try:
             # This is a bit of a hack: re-using get_state to list users
             state = sys.sys_get_state()
             # Wait, sys_get_state isn't returning users in my implementation yet?
             # I need to check kernel/dom.py or syscalls.py

             # In syscalls.py:
             # def sys_get_state(self): ... returns processes, cwd.
             # In dom.py it was adding users.

             # Let's assume we update syscalls.py to expose user management.
             if hasattr(sys, "sys_user_list"):
                 return json.dumps({"users": sys.sys_user_list()})
             else:
                 # Fallback
                 return json.dumps({"error": "User listing not supported by kernel yet."})

        except Exception as e:
             return json.dumps({"error": str(e)})

    elif cmd == "add":
        if len(args) < 3: return json.dumps({"error": "Usage: user add <name> <pass>"})
        u, p = args[1], args[2]
        if hasattr(sys, "sys_user_add"):
            if sys.sys_user_add(u, p):
                return json.dumps({"status": "success", "user": u})
            return json.dumps({"error": "Failed to add user (exists?)"})
        return json.dumps({"error": "Kernel does not support adding users."})

    elif cmd == "delete":
        if len(args) < 2: return json.dumps({"error": "Usage: user delete <name>"})
        u = args[1]
        if hasattr(sys, "sys_user_delete"):
            if sys.sys_user_delete(u):
                return json.dumps({"status": "deleted", "user": u})
            return json.dumps({"error": "Failed to delete user."})
        return json.dumps({"error": "Kernel does not support deleting users."})

    return json.dumps({"error": f"Unknown command: {cmd}"})
