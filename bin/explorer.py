# bin/explorer.py
import json

def main(args, sys):
    """
    File Explorer App.
    Usage:
      run explorer list <path>
      run explorer search <path> <query>
      run explorer copy <src> <dst>
      run explorer move <src> <dst>
    """
    if not args:
        return json.dumps({"error": "No command provided."})

    cmd = args[0]

    if cmd == "list":
        path = args[1] if len(args) > 1 else "/"
        try:
            items = sys.sys_ls(path)
            # Enhance with metadata if possible, but sys_ls returns strings
            # To be DOM compliant, we should maybe return a tree?
            # Let's return a detailed list.
            details = []
            for item in items:
                # Naive check if directory: try list it?
                # Or we rely on naming convention?
                # Actually SyscallHandler.sys_read raises error on dir.

                # Check type via syscall or just return name
                # In a real OS we'd stat. Here we have limited syscalls.
                details.append({"name": item, "path": f"{path}/{item}".replace("//", "/")})

            return json.dumps({"current_path": path, "items": details}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    elif cmd == "search":
        # Recursive search mock
        return json.dumps({"error": "Search not implemented yet"})

    elif cmd == "copy":
        if len(args) < 3: return json.dumps({"error": "Usage: copy <src> <dst>"})
        src, dst = args[1], args[2]
        try:
            data = sys.sys_read(src)
            sys.sys_write(dst, data)
            return json.dumps({"status": "copied", "src": src, "dst": dst})
        except Exception as e:
            return json.dumps({"error": str(e)})

    elif cmd == "move":
        # Read write delete (not impl)
        return json.dumps({"error": "Move requires delete syscall"})

    return json.dumps({"error": f"Unknown command: {cmd}"})
