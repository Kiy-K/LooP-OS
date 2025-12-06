# kernel/dom.py

class SystemDOM:
    """
    Represents the Operating System state as a Document Object Model (DOM) tree.
    Used by the Agent to understand the environment.
    """
    def __init__(self, syscall_handler):
        self.sys = syscall_handler

    def get_state(self):
        """
        Returns the full state of the OS as a dictionary.
        """
        return {
            "filesystem": self._get_fs_tree(self.sys.fs.root),
            "processes": self.sys.sys_proc_list(),
            "users": self.sys.user_manager.list_users()
        }

    def _get_fs_tree(self, node, path="/"):
        """
        Recursively builds the filesystem tree.
        """
        # Avoid recursion depth issues or huge output by limiting depth or content?
        # For now, simple recursion.

        # We need to import the types to check instance
        # But we can check class name or duck type to avoid circular imports if strictly needed.
        # However, importing FileSystem classes is safe here.

        node_type = type(node).__name__

        if node_type == "FileNode":
            return {
                "type": "file",
                "permissions": node.permissions.mode,
                "owner": node.permissions.owner,
                # "size": len(node.data) # Optional
            }
        elif node_type == "DirectoryNode":
            children = {}
            for name, child in node.children.items():
                child_path = path + name + "/" if path == "/" else path + "/" + name
                children[name] = self._get_fs_tree(child, child_path)
            return {
                "type": "directory",
                "permissions": node.permissions.mode,
                "owner": node.permissions.owner,
                "children": children
            }
        return {"type": "unknown"}
