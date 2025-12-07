
import unittest
from unittest.mock import MagicMock, patch
import sys

class TestKubernetesInterface(unittest.TestCase):
    def setUp(self):
        # Patch kubernetes module in k8s_interface
        self.k8s_patcher = patch("fyodoros.kernel.cloud.k8s_interface.client")
        self.mock_client_module = self.k8s_patcher.start()

        self.config_patcher = patch("fyodoros.kernel.cloud.k8s_interface.config")
        self.mock_config_module = self.config_patcher.start()

        # Setup mocks
        self.mock_apps_v1 = MagicMock()
        self.mock_core_v1 = MagicMock()
        self.mock_client_module.AppsV1Api.return_value = self.mock_apps_v1
        self.mock_client_module.CoreV1Api.return_value = self.mock_core_v1

        # Import class after patching
        from fyodoros.kernel.cloud.k8s_interface import KubernetesInterface
        self.KubernetesInterface = KubernetesInterface

        # Initialize
        self.k8s = self.KubernetesInterface()

    def tearDown(self):
        self.k8s_patcher.stop()
        self.config_patcher.stop()

    def test_availability(self):
        self.assertTrue(self.k8s.check_availability())

    def test_create_deployment(self):
        mock_resp = MagicMock()
        mock_resp.metadata.name = "my-dep"
        self.mock_apps_v1.create_namespaced_deployment.return_value = mock_resp

        res = self.k8s.create_deployment("my-dep", "nginx")
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["name"], "my-dep")

        self.mock_apps_v1.create_namespaced_deployment.assert_called_once()

    def test_scale_deployment(self):
        mock_resp = MagicMock()
        mock_resp.spec.replicas = 3
        self.mock_apps_v1.patch_namespaced_deployment.return_value = mock_resp

        res = self.k8s.scale_deployment("my-dep", 3)
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["replicas"], 3)

    def test_get_pods(self):
        pod = MagicMock()
        pod.metadata.name = "pod-1"
        pod.status.phase = "Running"
        pod.status.pod_ip = "1.2.3.4"
        pod.spec.node_name = "node-1"

        mock_list = MagicMock()
        mock_list.items = [pod]
        self.mock_core_v1.list_namespaced_pod.return_value = mock_list

        res = self.k8s.get_pods()
        self.assertTrue(res["success"])
        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["name"], "pod-1")


class TestKubernetesSyscalls(unittest.TestCase):
    def setUp(self):
        self.ki_patcher = patch("fyodoros.kernel.syscalls.KubernetesInterface")
        self.MockKubernetesInterface = self.ki_patcher.start()

        # We also need to patch DockerInterface since it's instantiated in syscalls init
        self.di_patcher = patch("fyodoros.kernel.syscalls.DockerInterface")
        self.di_patcher.start()

        from fyodoros.kernel.syscalls import SyscallHandler

        self.user_manager = MagicMock()
        self.syscalls = SyscallHandler(user_manager=self.user_manager)

        self.mock_k8s = self.syscalls.k8s_interface

        self.syscalls.scheduler = MagicMock()
        self.syscalls.scheduler.current_process.uid = "user1"

    def tearDown(self):
        self.ki_patcher.stop()
        self.di_patcher.stop()

    def test_permission_denied(self):
        self.user_manager.has_permission.return_value = False
        res = self.syscalls.sys_k8s_get_pods()
        self.assertFalse(res["success"])
        self.assertIn("Permission Denied", res["error"])

    def test_permission_granted(self):
        self.user_manager.has_permission.return_value = True
        self.mock_k8s.get_pods.return_value = {"success": True, "data": []}

        res = self.syscalls.sys_k8s_get_pods()
        self.assertTrue(res["success"])

if __name__ == "__main__":
    unittest.main()
