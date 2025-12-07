"""
Kubernetes Interface for FyodorOS.

This module provides a wrapper around the kubernetes-client to manage
Kubernetes resources.
"""

from kubernetes import client, config
from kubernetes.client.rest import ApiException
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
        try:
            if kubeconfig:
                config.load_kube_config(config_file=kubeconfig)
            else:
                # Try to load from default location or in-cluster
                try:
                    config.load_kube_config()
                except config.ConfigException:
                    try:
                        config.load_incluster_config()
                    except config.ConfigException:
                        # Fail silently, check_availability will return False
                        pass

            self.apps_v1 = client.AppsV1Api()
            self.core_v1 = client.CoreV1Api()
            self.available = True
        except Exception:
            self.available = False

    def _response(self, success: bool, data: Any = None, error: str = None) -> Dict[str, Any]:
        """
        Helper to format the response.
        """
        return {"success": success, "data": data, "error": error}

    def check_availability(self) -> bool:
        """
        Check if Kubernetes is reachable.
        """
        try:
            # If not initialized, try to load config
            if not self.available:
                try:
                    config.load_kube_config()
                except config.ConfigException:
                    try:
                        config.load_incluster_config()
                    except config.ConfigException:
                        pass

                # Re-initialize APIs if they were not set (or just to be safe)
                self.apps_v1 = client.AppsV1Api()
                self.core_v1 = client.CoreV1Api()

            self.core_v1.get_api_resources()
            self.available = True
            return True
        except Exception:
            self.available = False
            return False

    def create_deployment(self, name: str, image: str, replicas: int = 1, namespace: str = "default") -> Dict[str, Any]:
        """
        Create a Kubernetes Deployment.
        """
        if not self.check_availability():
            return self._response(False, error="Kubernetes not available")

        deployment = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(name=name),
            spec=client.V1DeploymentSpec(
                replicas=replicas,
                selector=client.V1LabelSelector(
                    match_labels={"app": name}
                ),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": name}),
                    spec=client.V1PodSpec(
                        containers=[
                            client.V1Container(
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
        except ApiException as e:
            return self._response(False, error=str(e))
        except Exception as e:
            return self._response(False, error=str(e))

    def scale_deployment(self, name: str, replicas: int, namespace: str = "default") -> Dict[str, Any]:
        """
        Scale a Deployment.
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
        except ApiException as e:
            return self._response(False, error=str(e))

    def delete_deployment(self, name: str, namespace: str = "default") -> Dict[str, Any]:
        """
        Delete a Deployment.
        """
        if not self.check_availability():
            return self._response(False, error="Kubernetes not available")

        try:
            self.apps_v1.delete_namespaced_deployment(
                name=name,
                namespace=namespace
            )
            return self._response(True, data=f"Deployment {name} deleted")
        except ApiException as e:
            return self._response(False, error=str(e))

    def get_pods(self, namespace: str = "default") -> Dict[str, Any]:
        """
        List Pods in a namespace.
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
        except ApiException as e:
            return self._response(False, error=str(e))

    def get_pod_logs(self, pod_name: str, namespace: str = "default", tail: int = 100) -> Dict[str, Any]:
        """
        Get logs from a Pod.
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
        except ApiException as e:
            return self._response(False, error=str(e))
