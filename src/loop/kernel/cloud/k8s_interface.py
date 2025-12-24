"""
Kubernetes Interface for LooP.

This module provides a wrapper around the kubernetes-client to manage
Kubernetes resources.
"""

from typing import Dict, List, Optional, Any
import os


class KubernetesInterface:
    """
    Wrapper for Kubernetes operations.
    """
    def __init__(self, kubeconfig: str = None):
        """
        Initialize the Kubernetes client.

        Args:
            kubeconfig (str): Path to kubeconfig file. Defaults to ~/.kube/config or KUBECONFIG env.
        """
        self.available = False
        self.apps_v1 = None
        self.core_v1 = None
        self.kubeconfig = kubeconfig
        self._k8s_module = None

        # Lazy initialization happens in check_availability

    def _ensure_module(self):
        """Lazy load kubernetes module"""
        if self._k8s_module is None:
            try:
                import kubernetes
                import kubernetes.client
                import kubernetes.config
                from kubernetes.client.rest import ApiException
                self._k8s_module = kubernetes
                self._client = kubernetes.client
                self._config = kubernetes.config
                self._api_exception = ApiException
            except ImportError:
                self._k8s_module = False

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
        Check if Kubernetes is reachable.

        Returns:
            bool: True if Kubernetes is available, False otherwise.
        """
        self._ensure_module()
        if not self._k8s_module:
            self.available = False
            return False

        try:
            # If not initialized, try to load config
            if not self.available or not self.core_v1:
                try:
                    if self.kubeconfig:
                        self._config.load_kube_config(config_file=self.kubeconfig)
                    else:
                         self._config.load_kube_config()
                except self._config.ConfigException:
                    try:
                        self._config.load_incluster_config()
                    except self._config.ConfigException:
                        pass # Fail later

                # Re-initialize APIs
                self.apps_v1 = self._client.AppsV1Api()
                self.core_v1 = self._client.CoreV1Api()

            # Verify connection
            self.core_v1.get_api_resources()
            self.available = True
            return True
        except Exception:
            self.available = False
            return False

    def create_deployment(self, name: str, image: str, replicas: int = 1, namespace: str = "default") -> Dict[str, Any]:
        """
        Create a Kubernetes Deployment.

        Args:
            name (str): Name of the deployment.
            image (str): Container image to use.
            replicas (int, optional): Number of replicas. Defaults to 1.
            namespace (str, optional): Target namespace. Defaults to "default".

        Returns:
            Dict[str, Any]: Operation result.
        """
        if not self.check_availability():
            return self._response(False, error="Kubernetes not available")

        deployment = self._client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=self._client.V1ObjectMeta(name=name),
            spec=self._client.V1DeploymentSpec(
                replicas=replicas,
                selector=self._client.V1LabelSelector(
                    match_labels={"app": name}
                ),
                template=self._client.V1PodTemplateSpec(
                    metadata=self._client.V1ObjectMeta(labels={"app": name}),
                    spec=self._client.V1PodSpec(
                        containers=[
                            self._client.V1Container(
                                name=name,
                                image=image
                            )
                        ]
                    )
                )
            )
        )

        try:
            resp = self.apps_v1.create_namespaced_deployment(
                body=deployment,
                namespace=namespace
            )
            return self._response(True, data={"name": resp.metadata.name, "status": "created"})
        except self._api_exception as e:
            return self._response(False, error=str(e))
        except Exception as e:
            return self._response(False, error=str(e))

    def scale_deployment(self, name: str, replicas: int, namespace: str = "default") -> Dict[str, Any]:
        """
        Scale a Deployment.

        Args:
            name (str): Name of the deployment.
            replicas (int): New number of replicas.
            namespace (str, optional): Target namespace. Defaults to "default".

        Returns:
            Dict[str, Any]: Operation result.
        """
        if not self.check_availability():
            return self._response(False, error="Kubernetes not available")

        try:
            # Patch semantics
            body = {"spec": {"replicas": replicas}}
            resp = self.apps_v1.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=body
            )
            return self._response(True, data={"name": name, "replicas": resp.spec.replicas})
        except self._api_exception as e:
            return self._response(False, error=str(e))

    def delete_deployment(self, name: str, namespace: str = "default") -> Dict[str, Any]:
        """
        Delete a Deployment.

        Args:
            name (str): Name of the deployment.
            namespace (str, optional): Target namespace. Defaults to "default".

        Returns:
            Dict[str, Any]: Operation result.
        """
        if not self.check_availability():
            return self._response(False, error="Kubernetes not available")

        try:
            self.apps_v1.delete_namespaced_deployment(
                name=name,
                namespace=namespace
            )
            return self._response(True, data=f"Deployment {name} deleted")
        except self._api_exception as e:
            return self._response(False, error=str(e))

    def get_pods(self, namespace: str = "default") -> Dict[str, Any]:
        """
        List Pods in a namespace.

        Args:
            namespace (str, optional): Target namespace. Defaults to "default".

        Returns:
            Dict[str, Any]: Operation result containing pod list.
        """
        if not self.check_availability():
            return self._response(False, error="Kubernetes not available")

        try:
            pods = self.core_v1.list_namespaced_pod(namespace=namespace)
            data = []
            for pod in pods.items:
                data.append({
                    "name": pod.metadata.name,
                    "status": pod.status.phase,
                    "ip": pod.status.pod_ip,
                    "node": pod.spec.node_name
                })
            return self._response(True, data=data)
        except self._api_exception as e:
            return self._response(False, error=str(e))

    def get_pod_logs(self, pod_name: str, namespace: str = "default", tail: int = 100) -> Dict[str, Any]:
        """
        Get logs from a Pod.

        Args:
            pod_name (str): Name of the pod.
            namespace (str, optional): Target namespace. Defaults to "default".
            tail (int, optional): Number of lines to tail. Defaults to 100.

        Returns:
            Dict[str, Any]: Operation result containing logs.
        """
        if not self.check_availability():
            return self._response(False, error="Kubernetes not available")

        try:
            logs = self.core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=tail
            )
            return self._response(True, data=logs)
        except self._api_exception as e:
            return self._response(False, error=str(e))
