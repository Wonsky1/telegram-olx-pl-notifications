"""
Dependency injection container for services.
Provides singleton access to services throughout the application.
"""

from typing import Optional

from repositories.monitoring import MonitoringRepository
from services.monitoring import MonitoringService
from services.validator import UrlValidator


class ServiceContainer:
    """Singleton container for application services."""

    _instance: Optional["ServiceContainer"] = None
    _monitoring_service: Optional[MonitoringService] = None
    _repository: Optional[MonitoringRepository] = None

    def __new__(cls) -> "ServiceContainer":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self) -> None:
        """Initialize all services."""
        if self._monitoring_service is None:
            self._repository = MonitoringRepository()
            validator = UrlValidator()
            self._monitoring_service = MonitoringService(self._repository, validator)

    def get_monitoring_service(self) -> MonitoringService:
        """Get the monitoring service instance."""
        if self._monitoring_service is None:
            self.initialize()
        return self._monitoring_service

    def get_repository(self) -> MonitoringRepository:
        """Get the repository instance."""
        if self._repository is None:
            self.initialize()
        return self._repository


# Global service container instance
_container = ServiceContainer()


def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    return _container.get_monitoring_service()


def get_repository() -> MonitoringRepository:
    """Get the global repository instance."""
    return _container.get_repository()
