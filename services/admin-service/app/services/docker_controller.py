import logging
from typing import Optional

import docker
from docker.errors import NotFound, APIError

from app.services.infra_controller import ActionResult, InfraController, ServiceStatus

logger = logging.getLogger("docker_controller")

# Map logical service names to Docker container names
CONTAINER_NAME_MAP = {
    "service-a": "service-a",
    "service-b": "service-b",
    "service-c": "service-c",
    "admin-service": "admin-service",
}


class DockerController(InfraController):
    """
    Docker-based implementation of InfraController.
    Uses the Docker SDK to manage containers.
    """

    def __init__(self) -> None:
        try:
            self._client = docker.from_env()
            logger.info("DockerController initialized — connected to Docker daemon")
        except Exception as exc:
            logger.error(f"Failed to connect to Docker daemon: {exc}")
            self._client = None

    def _get_container_name(self, service_name: str) -> str:
        return CONTAINER_NAME_MAP.get(service_name, service_name)

    def _get_container(self, service_name: str):
        if self._client is None:
            return None
        container_name = self._get_container_name(service_name)
        try:
            return self._client.containers.get(container_name)
        except NotFound:
            logger.warning(f"Container '{container_name}' not found")
            return None
        except APIError as exc:
            logger.error(f"Docker API error for '{container_name}': {exc}")
            return None

    def restart_service(self, service_name: str) -> ActionResult:
        container = self._get_container(service_name)
        if container is None:
            return ActionResult(
                success=False,
                service_name=service_name,
                action="restart",
                message=f"Container for {service_name} not found",
            )

        try:
            container.restart(timeout=10)
            logger.info(f"Container '{service_name}' restarted successfully")
            return ActionResult(
                success=True,
                service_name=service_name,
                action="restart",
                message=f"{service_name} restarted successfully",
                details=f"Container ID: {container.short_id}",
            )
        except APIError as exc:
            logger.error(f"Failed to restart '{service_name}': {exc}")
            return ActionResult(
                success=False,
                service_name=service_name,
                action="restart",
                message=f"Failed to restart {service_name}: {exc}",
            )

    def stop_service(self, service_name: str) -> ActionResult:
        """Stop a Docker container (simulate service down)."""
        container = self._get_container(service_name)
        if container is None:
            return ActionResult(
                success=False,
                service_name=service_name,
                action="stop",
                message=f"Container for {service_name} not found",
            )

        try:
            container.stop(timeout=5)
            logger.info(f"Container '{service_name}' stopped successfully")
            return ActionResult(
                success=True,
                service_name=service_name,
                action="stop",
                message=f"{service_name} stopped successfully",
                details=f"Container ID: {container.short_id}",
            )
        except APIError as exc:
            logger.error(f"Failed to stop '{service_name}': {exc}")
            return ActionResult(
                success=False,
                service_name=service_name,
                action="stop",
                message=f"Failed to stop {service_name}: {exc}",
            )
    def scale_service(self, service_name: str, replicas: int) -> ActionResult:
        """
        Scale a service. In plain Docker (non-Swarm), we simulate scaling
        by reporting the intent. In a real docker-compose setup, use
        `docker-compose up --scale <service>=<n>`.
        For demo purposes, we restart the container and report the scale action.
        """
        container = self._get_container(service_name)
        if container is None:
            return ActionResult(
                success=False,
                service_name=service_name,
                action="scale",
                message=f"Container for {service_name} not found",
            )

        try:
            # In plain Docker, true scaling requires Swarm or compose --scale.
            # We simulate by restarting and acknowledging the scale request.
            container.restart(timeout=10)
            logger.info(f"Container '{service_name}' scaled to {replicas} (simulated — restarted)")
            return ActionResult(
                success=True,
                service_name=service_name,
                action="scale",
                message=f"{service_name} scaled to {replicas} replicas (simulated)",
                details=f"Container ID: {container.short_id}. Note: true horizontal scaling requires Docker Swarm or Kubernetes.",
            )
        except APIError as exc:
            logger.error(f"Failed to scale '{service_name}': {exc}")
            return ActionResult(
                success=False,
                service_name=service_name,
                action="scale",
                message=f"Failed to scale {service_name}: {exc}",
            )

    def get_status(self, service_name: str) -> ServiceStatus:
        container = self._get_container(service_name)
        if container is None:
            return ServiceStatus(
                service_name=service_name,
                status="stopped",
                replicas=0,
                details="Container not found",
            )

        try:
            container.reload()
            state = container.status  # "running", "exited", "paused", etc.
            return ServiceStatus(
                service_name=service_name,
                status=state,
                replicas=1 if state == "running" else 0,
                details=f"Container ID: {container.short_id}, Image: {container.image.tags}",
            )
        except Exception as exc:
            return ServiceStatus(
                service_name=service_name,
                status="unknown",
                replicas=0,
                details=str(exc),
            )

    def get_all_statuses(self) -> list[ServiceStatus]:
        statuses = []
        for service_name in CONTAINER_NAME_MAP:
            statuses.append(self.get_status(service_name))
        return statuses