# kernel/dom.py
"""
System DOM Representation.

This module provides the `SystemDOM` class, which converts the current
operating system state (filesystem, processes, users) into a structured
dictionary (DOM-like) format for the AI agent to consume.
"""

class SystemDOM:
    """
    Represents the Operating System state as a Document Object Model (DOM) tree.

    Used by the Agent to understand the environment.

    Attributes:
        sys (SyscallHandler): The system call handler to access kernel state.
    """
    def __init__(self, syscall_handler):
        """
        Initialize the SystemDOM.

        Args:
            syscall_handler (SyscallHandler): The kernel syscall handler.
        """
        self.sys = syscall_handler

    def get_state(self):
        """
        Returns the full state of the OS as a dictionary.

        Returns:
            dict: A dictionary containing 'filesystem', 'processes', 'users', and 'docker'.
        """
        # Get docker state
        docker_state = []
        try:
            res = self.sys.sys_docker_ps()
            if res.get("success"):
                docker_state = res.get("data", [])
        except Exception:
            pass

        # Get K8s state
        k8s_state = []
        try:
            res = self.sys.sys_k8s_get_pods()
            if res.get("success"):
                k8s_state = res.get("data", [])
        except Exception:
            pass

        return {
            "filesystem": self._get_fs_tree(self.sys.fs.root),
            "processes": self.sys.sys_proc_list(),
            "users": self.sys.user_manager.list_users(),
            "docker": docker_state,
            "k8s_pods": k8s_state
        }

    def _get_fs_tree(self, node, path="/"):
        """
        Recursively builds the filesystem tree.

        Args:
            node (FileNode or DirectoryNode): The current filesystem node.
            path (str, optional): The current path. Defaults to "/".

        Returns:
            dict: A dictionary representation of the node and its children (if any).
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
