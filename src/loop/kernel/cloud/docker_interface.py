"""
Docker Interface for LooP.

This module provides a wrapper around the docker-py SDK to manage
Docker containers and images.
"""

from typing import Dict, List, Optional, Any


class DockerInterface:
    """
    Wrapper for Docker operations.
    """
    def __init__(self):
        """
        Initialize the Docker client lazily.
        """
        self.client = None
        self.available = False
        self._docker_module = None # Cache for the module

    def _ensure_module(self):
        """Lazy load docker module"""
        if self._docker_module is None:
            try:
                import docker
                import docker.errors
                self._docker_module = docker
                self._docker_errors = docker.errors
            except ImportError:
                self._docker_module = False

    def _response(self, success: bool, data: Any = None, error: str = None) -> Dict[str, Any]:
        """
        Helper to format the response.

        Args:
            success (bool): Whether the operation was successful.
            data (Any, optional): Data returned by the operation.
            error (str, optional): Error message if failed.

        Returns:
            Dict[str, Any]: Formatted response.
        """
        return {"success": success, "data": data, "error": error}

    def check_availability(self) -> bool:
        """
        Check if Docker is available.

        Returns:
            bool: True if Docker is available, False otherwise.
        """
        self._ensure_module()
        if not self._docker_module:
            self.available = False
            return False

        if not self.client:
            try:
                self.client = self._docker_module.from_env()
                self.available = True
            except self._docker_errors.DockerException:
                self.available = False
        return self.available

    def login(self, username, password, registry="https://index.docker.io/v1/"):
        """
        Login to a Docker registry.

        Args:
            username (str): The registry username.
            password (str): The registry password.
            registry (str, optional): The registry URL. Defaults to Docker Hub.

        Returns:
            Dict[str, Any]: Operation result.
        """
        if not self.check_availability():
            return self._response(False, error="Docker daemon not available")

        try:
            result = self.client.login(username=username, password=password, registry=registry)
            return self._response(True, data=result)
        except Exception as e:
            return self._response(False, error=str(e))

    def logout(self, registry="https://index.docker.io/v1/"):
        """
        Logout from a Docker registry.

        Args:
            registry (str, optional): The registry URL.

        Returns:
            Dict[str, Any]: Operation result.
        """
        return self._response(True, data="Logout successful (session cleared)")

    def build_image(self, path: str, tag: str, dockerfile: str = "Dockerfile") -> Dict[str, Any]:
        """
        Build a Docker image.

        Args:
            path (str): The path to the directory containing the Dockerfile.
            tag (str): The tag to assign to the image.
            dockerfile (str, optional): The name of the Dockerfile. Defaults to "Dockerfile".

        Returns:
            Dict[str, Any]: Operation result containing image ID and logs.
        """
        if not self.check_availability():
            return self._response(False, error="Docker daemon not available")

        try:
            # build returns tuple (image, logs)
            image, logs = self.client.images.build(path=path, tag=tag, dockerfile=dockerfile)

            # Parse logs for display
            log_output = []
            for chunk in logs:
                if 'stream' in chunk:
                    log_output.append(chunk['stream'])

            return self._response(True, data={"image_id": image.id, "tags": image.tags, "logs": "".join(log_output)})
        except Exception as e:
            return self._response(False, error=str(e))

    def run_container(self, image: str, name: str = None, ports: Dict = None, env: Dict = None, detach: bool = True) -> Dict[str, Any]:
        """
        Run a Docker container.

        Args:
            image (str): The image to run.
            name (str, optional): The name for the container.
            ports (Dict, optional): Dictionary mapping container ports to host ports.
            env (Dict, optional): Dictionary of environment variables.
            detach (bool, optional): Whether to run in detached mode. Defaults to True.

        Returns:
            Dict[str, Any]: Operation result containing container details.
        """
        if not self.check_availability():
            return self._response(False, error="Docker daemon not available")

        try:
            container = self.client.containers.run(
                image,
                name=name,
                ports=ports,
                environment=env,
                detach=detach
            )
            return self._response(True, data={"container_id": container.id, "name": container.name, "status": container.status})
        except Exception as e:
            return self._response(False, error=str(e))

    def list_containers(self, all: bool = False) -> Dict[str, Any]:
        """
        List Docker containers.

        Args:
            all (bool, optional): Whether to show all containers (including stopped). Defaults to False.

        Returns:
            Dict[str, Any]: Operation result containing list of containers.
        """
        if not self.check_availability():
            return self._response(False, error="Docker daemon not available")

        try:
            containers = self.client.containers.list(all=all)
            data = []
            for c in containers:
                data.append({
                    "id": c.id[:12],
                    "name": c.name,
                    "image": c.image.tags[0] if c.image.tags else c.image.id[:12],
                    "status": c.status,
                    "ports": c.ports
                })
            return self._response(True, data=data)
        except Exception as e:
            return self._response(False, error=str(e))

    def stop_container(self, container_id: str) -> Dict[str, Any]:
        """
        Stop a container.

        Args:
            container_id (str): The ID or name of the container.

        Returns:
            Dict[str, Any]: Operation result.
        """
        if not self.check_availability():
            return self._response(False, error="Docker daemon not available")

        try:
            container = self.client.containers.get(container_id)
            container.stop()
            return self._response(True, data=f"Container {container_id} stopped")
        except self._docker_errors.NotFound:
            return self._response(False, error=f"Container {container_id} not found")
        except Exception as e:
            return self._response(False, error=str(e))

    def remove_container(self, container_id: str, force: bool = False) -> Dict[str, Any]:
        """
        Remove a container.

        Args:
            container_id (str): The ID or name of the container.
            force (bool, optional): Whether to force removal. Defaults to False.

        Returns:
            Dict[str, Any]: Operation result.
        """
        if not self.check_availability():
            return self._response(False, error="Docker daemon not available")

        try:
            container = self.client.containers.get(container_id)
            container.remove(force=force)
            return self._response(True, data=f"Container {container_id} removed")
        except self._docker_errors.NotFound:
            return self._response(False, error=f"Container {container_id} not found")
        except Exception as e:
            return self._response(False, error=str(e))

    def get_logs(self, container_id: str, tail: int = 100) -> Dict[str, Any]:
        """
        Get container logs.

        Args:
            container_id (str): The ID or name of the container.
            tail (int, optional): Number of lines to tail. Defaults to 100.

        Returns:
            Dict[str, Any]: Operation result containing logs.
        """
        if not self.check_availability():
            return self._response(False, error="Docker daemon not available")

        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=tail).decode('utf-8')
            return self._response(True, data=logs)
        except self._docker_errors.NotFound:
            return self._response(False, error=f"Container {container_id} not found")
        except Exception as e:
            return self._response(False, error=str(e))
