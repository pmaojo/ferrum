import pytest
from unittest.mock import Mock

from domain.entities import GraphAccessPolicy, UserRole
from application.ports import AuthorizationServicePort, TracingPort
from importlib import util
from pathlib import Path
import asyncio
import sys

ROOT = Path(__file__).resolve().parents[1]

def _load_module(name: str, path: Path):
    spec = util.spec_from_file_location(name, path)
    module = util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

create_mod = _load_module(
    "application.use_cases.graph_access_policy.create_graph_access_policy_use_case",
    ROOT / "application" / "use_cases" / "graph_access_policy" / "create_graph_access_policy_use_case.py",
)
update_mod = _load_module(
    "application.use_cases.graph_access_policy.update_graph_access_policy_use_case",
    ROOT / "application" / "use_cases" / "graph_access_policy" / "update_graph_access_policy_use_case.py",
)
delete_mod = _load_module(
    "application.use_cases.graph_access_policy.delete_graph_access_policy_use_case",
    ROOT / "application" / "use_cases" / "graph_access_policy" / "delete_graph_access_policy_use_case.py",
)
list_mod = _load_module(
    "application.use_cases.graph_access_policy.list_graph_access_policies_use_case",
    ROOT / "application" / "use_cases" / "graph_access_policy" / "list_graph_access_policies_use_case.py",
)

CreateGraphAccessPolicyUseCase = create_mod.CreateGraphAccessPolicyUseCase
CreateGraphAccessPolicyRequest = create_mod.CreateGraphAccessPolicyRequest
GraphAccessPolicyRepositoryPort = create_mod.GraphAccessPolicyRepositoryPort
UpdateGraphAccessPolicyUseCase = update_mod.UpdateGraphAccessPolicyUseCase
UpdateGraphAccessPolicyRequest = update_mod.UpdateGraphAccessPolicyRequest
DeleteGraphAccessPolicyUseCase = delete_mod.DeleteGraphAccessPolicyUseCase
DeleteGraphAccessPolicyRequest = delete_mod.DeleteGraphAccessPolicyRequest
ListGraphAccessPoliciesUseCase = list_mod.ListGraphAccessPoliciesUseCase
ListGraphAccessPoliciesRequest = list_mod.ListGraphAccessPoliciesRequest


class TestGraphAccessPolicyUseCases:
    @pytest.fixture
    def mock_repository(self):
        return Mock(spec=GraphAccessPolicyRepositoryPort)

    @pytest.fixture
    def mock_authorization_service(self):
        return Mock(spec=AuthorizationServicePort)

    @pytest.fixture
    def mock_tracer(self):
        tracer = Mock(spec=TracingPort)
        tracer.start_span.return_value.__enter__ = Mock()
        tracer.start_span.return_value.__exit__ = Mock()
        return tracer

    @pytest.fixture
    def create_use_case(self, mock_repository, mock_authorization_service, mock_tracer):
        return CreateGraphAccessPolicyUseCase(mock_repository, mock_authorization_service, mock_tracer)

    @pytest.fixture
    def sample_policy(self):
        return GraphAccessPolicy(
            kg_id="kg1",
            tenant_id="t1",
            user_id="u2",
            role=UserRole.EDITOR,
            permissions=["read", "update"],
        )

    def test_create_policy_success(self, create_use_case, mock_repository, mock_authorization_service, sample_policy):
        mock_authorization_service.get_graph_access_policy.return_value = None
        mock_repository.create.return_value = sample_policy

        request = CreateGraphAccessPolicyRequest(
            kg_id="kg1",
            tenant_id="t1",
            user_id="admin",
            target_user_id="u2",
            role="editor",
            permissions=["read", "update"],
        )

        response = asyncio.run(create_use_case.execute(request))

        assert response.success is True
        assert response.policy is not None
        assert response.policy.role == "editor"
        mock_authorization_service.check_permission.assert_called_once_with(
            user_id="admin", resource_id="kg1", action="manage_access"
        )
        mock_authorization_service.get_graph_access_policy.assert_called_once_with(
            kg_id="kg1", tenant_id="t1", user_id="u2"
        )
        mock_repository.create.assert_called_once()

    def test_create_policy_already_exists(self, create_use_case, mock_authorization_service, sample_policy):
        mock_authorization_service.get_graph_access_policy.return_value = sample_policy

        request = CreateGraphAccessPolicyRequest(
            kg_id="kg1",
            tenant_id="t1",
            user_id="admin",
            target_user_id="u2",
            role="editor",
            permissions=["read"],
        )

        response = asyncio.run(create_use_case.execute(request))

        assert response.success is False
        assert "Policy already exists" in response.error_message

    @pytest.fixture
    def update_use_case(self, mock_repository, mock_authorization_service, mock_tracer):
        return UpdateGraphAccessPolicyUseCase(mock_repository, mock_authorization_service, mock_tracer)

    @pytest.fixture
    def delete_use_case(self, mock_repository, mock_authorization_service, mock_tracer):
        return DeleteGraphAccessPolicyUseCase(mock_repository, mock_authorization_service, mock_tracer)

    @pytest.fixture
    def list_use_case(self, mock_repository, mock_authorization_service, mock_tracer):
        return ListGraphAccessPoliciesUseCase(mock_repository, mock_authorization_service, mock_tracer)

    def test_update_policy_not_found(self, update_use_case, mock_repository, mock_authorization_service):
        mock_authorization_service.check_permission.return_value = None
        mock_repository.get.return_value = None
        request = UpdateGraphAccessPolicyRequest(
            kg_id="kg1",
            tenant_id="t1",
            user_id="admin",
            target_user_id="u2",
            role="viewer",
        )
        response = asyncio.run(update_use_case.execute(request))
        assert response.success is False
        assert "Policy not found" in response.error_message

    def test_delete_policy_success(self, delete_use_case, mock_repository, mock_authorization_service):
        mock_authorization_service.check_permission.return_value = None
        mock_repository.delete.return_value = True
        request = DeleteGraphAccessPolicyRequest(
            kg_id="kg1",
            tenant_id="t1",
            user_id="admin",
            target_user_id="u2",
        )
        response = asyncio.run(delete_use_case.execute(request))
        assert response.success is True
        assert response.deleted is True
        mock_repository.delete.assert_called_once_with("kg1", "t1", "u2")

    def test_list_policies(self, list_use_case, mock_repository, mock_authorization_service, sample_policy):
        mock_authorization_service.check_permission.return_value = None
        mock_repository.list_for_kg.return_value = [sample_policy]
        request = ListGraphAccessPoliciesRequest(
            kg_id="kg1",
            tenant_id="t1",
            user_id="admin",
        )
        response = asyncio.run(list_use_case.execute(request))
        assert response.success is True
        assert len(response.policies) == 1
        assert response.policies[0].user_id == "u2"
