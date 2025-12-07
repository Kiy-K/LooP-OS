
import unittest
from unittest.mock import MagicMock, patch
import sys

# We need to ensure fyodoros is importable
# Assuming PYTHONPATH is set or we are running from root

class TestDockerInterface(unittest.TestCase):
    def setUp(self):
        # Patch the docker module where it is used in docker_interface
        self.docker_patcher = patch("fyodoros.kernel.cloud.docker_interface.docker")
        self.mock_docker_module = self.docker_patcher.start()

        # Setup mock client
        self.mock_client = MagicMock()
        self.mock_docker_module.from_env.return_value = self.mock_client

        # Import class after patching
        from fyodoros.kernel.cloud.docker_interface import DockerInterface
        self.DockerInterface = DockerInterface

        # Initialize interface
        self.docker = self.DockerInterface()

    def tearDown(self):
        self.docker_patcher.stop()

    def test_availability(self):
        self.assertTrue(self.docker.check_availability())

    def test_build_image(self):
        # Mock build response
        mock_image = MagicMock()
        mock_image.id = "sha256:123"
        mock_image.tags = ["test:latest"]
        self.mock_client.images.build.return_value = (mock_image, [{"stream": "Step 1/1"}])

        res = self.docker.build_image(".", "test:latest")
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["image_id"], "sha256:123")

    def test_run_container(self):
        mock_container = MagicMock()
        mock_container.id = "12345"
        mock_container.name = "test_cont"
        mock_container.status = "running"
        self.mock_client.containers.run.return_value = mock_container

        res = self.docker.run_container("test:latest", name="test_cont")
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["container_id"], "12345")

    def test_list_containers(self):
        c1 = MagicMock()
        c1.id = "123"
        c1.name = "c1"
        c1.image.tags = ["img:1"]
        c1.status = "running"
        c1.ports = {}

        self.mock_client.containers.list.return_value = [c1]

        res = self.docker.list_containers()
        self.assertTrue(res["success"])
        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["id"], "123")

class TestDockerSyscalls(unittest.TestCase):
    def setUp(self):
        # We need to patch DockerInterface in syscalls to avoid real instantiation
        self.di_patcher = patch("fyodoros.kernel.syscalls.DockerInterface")
        self.MockDockerInterface = self.di_patcher.start()

        from fyodoros.kernel.syscalls import SyscallHandler

        self.user_manager = MagicMock()
        self.syscalls = SyscallHandler(user_manager=self.user_manager)

        # The mock instance created inside SyscallHandler
        self.mock_docker = self.syscalls.docker_interface

        # Mock scheduler/process for current uid
        self.syscalls.scheduler = MagicMock()
        self.syscalls.scheduler.current_process.uid = "user1"

    def tearDown(self):
        self.di_patcher.stop()

    def test_permission_denied(self):
        # User without manage_docker
        self.user_manager.has_permission.return_value = False

        res = self.syscalls.sys_docker_ps()
        self.assertFalse(res["success"])
        self.assertIn("Permission Denied", res["error"])

    def test_permission_granted(self):
        # User with manage_docker
        self.user_manager.has_permission.return_value = True
        self.mock_docker.list_containers.return_value = {"success": True, "data": []}

        res = self.syscalls.sys_docker_ps()
        self.assertTrue(res["success"])

    def test_root_access(self):
        # Root user
        self.syscalls.scheduler.current_process.uid = "root"
        self.mock_docker.list_containers.return_value = {"success": True, "data": []}

        res = self.syscalls.sys_docker_ps()
        self.assertTrue(res["success"])

    def test_json_parsing(self):
        # User with manage_docker
        self.user_manager.has_permission.return_value = True
        self.mock_docker.run_container.return_value = {"success": True, "data": {}}

        # Pass JSON strings
        ports_str = '{"80/tcp": 8080}'
        env_str = '{"KEY": "VALUE"}'

        res = self.syscalls.sys_docker_run("img", ports=ports_str, env=env_str)
        self.assertTrue(res["success"])

        # Verify call args were parsed dicts
        self.mock_docker.run_container.assert_called_with(
            "img", None, {"80/tcp": 8080}, {"KEY": "VALUE"}
        )

    def test_json_parsing_error(self):
        self.user_manager.has_permission.return_value = True
        res = self.syscalls.sys_docker_run("img", ports="{invalid json")
        self.assertFalse(res["success"])
        self.assertIn("Invalid JSON", res["error"])

if __name__ == "__main__":
    unittest.main()
