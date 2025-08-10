import importlib
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock, patch


class TestDependencies(IsolatedAsyncioTestCase):
    async def test_singleton_and_init_paths(self):
        import core.dependencies as deps

        # Ensure clean singleton state
        importlib.reload(deps)

        # Fresh container for isolation
        container = deps.ServiceContainer()
        deps._container = container

        with patch.object(deps, "MonitoringRepository", autospec=True) as Repo:
            with patch.object(deps, "UrlValidator", autospec=True) as Validator:
                with patch.object(deps, "MonitoringService", autospec=True) as Service:
                    # Lazy initialize via accessor
                    svc = deps.get_monitoring_service()

                    # Constructed exactly once and wired together
                    Repo.assert_called_once_with()
                    Validator.assert_called_once_with()
                    Service.assert_called_once()
                    repo_inst = Repo.return_value
                    validator_inst = Validator.return_value
                    Service.assert_called_with(repo_inst, validator_inst)

                    # Cached instance returned on subsequent calls
                    self.assertIs(svc, deps.get_monitoring_service())

                    # Repository accessor returns the same repo
                    self.assertIs(deps.get_repository(), repo_inst)

    async def test_global_getters_return_from_container(self):
        import importlib

        import core.dependencies as deps

        # Ensure module is reloaded to reset singletons for this test
        importlib.reload(deps)

        fake_repo = MagicMock(name="Repo")
        fake_svc = MagicMock(name="Svc")

        # Swap container to a fake one exposing same API
        class FakeContainer:
            def get_monitoring_service(self):
                return fake_svc

            def get_repository(self):
                return fake_repo

        deps._container = FakeContainer()

        self.assertIs(deps.get_monitoring_service(), fake_svc)
        self.assertIs(deps.get_repository(), fake_repo)
