# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.
#
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

from itertools import product
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from ops import testing

from charm import RequestAuthenticationConfiguratorCharm

# isort: off
from charms.hydra.v0.oauth import OAuthRequirer
# isort: off

CONFIG_KEY_FOR_USER_ID_HEADER_NAME = "user-id-header-name"
JWT_ISSUER = "https://auth.example.com"
REQ_AUTH_INTEGRATION_NAME_FOR_M2M = "request-auth-m2m"
REQ_AUTH_INTEGRATION_NAME_FOR_UI = "request-auth-ui"
OAUTH_INTEGRATION_NAME = "oauth"
SOME_VALID_USERID_HEADER_NAME = "kubeflow-userid"


def compose_charm_configs(user_id_header_name: str) -> dict[str, str]:
    """Compose the charm configs given the user ID header name."""
    return {CONFIG_KEY_FOR_USER_ID_HEADER_NAME: user_id_header_name}


def compose_integrations(
    is_m2m_integration_established: bool,
    is_ui_integration_established: bool,
    is_oauth_integration_established: bool = True,
) -> list[testing.Relation]:
    """Compose the RequestAuthentication integrations to include in the test state."""
    relations = []
    if is_m2m_integration_established:
        relations.append(testing.Relation(endpoint=REQ_AUTH_INTEGRATION_NAME_FOR_M2M))
    if is_ui_integration_established:
        relations.append(testing.Relation(endpoint=REQ_AUTH_INTEGRATION_NAME_FOR_UI))
    if is_oauth_integration_established:
        relations.append(testing.Relation(endpoint=OAUTH_INTEGRATION_NAME))
    return relations


@pytest.mark.parametrize("is_unit_leader", [True, False])
@patch("components.config_validation.ConfigValidationComponent.get_status")
@patch("components.oauth_integration.OAuthRequirerComponent.get_status")
@patch("components.request_auth_integration.RequestAuthRequirerComponent.get_status")
@patch("components.request_auth_integration.RequestAuthRequirerComponent._configure_app_leader")
def test_unit_status_based_on_leadership(
    _: MagicMock,
    mock_request_auth_integration_get_status: MagicMock,
    mock_oauth_integration_get_status: MagicMock,
    mock_config_validation_get_status: MagicMock,
    is_unit_leader,
):
    """Test that the charm has the correct unit status based on leadership."""
    # Arrange:
    mock_config_validation_get_status.return_value = testing.ActiveStatus()
    mock_oauth_integration_get_status.return_value = testing.ActiveStatus()
    mock_request_auth_integration_get_status.return_value = testing.ActiveStatus()
    ctx = testing.Context(RequestAuthenticationConfiguratorCharm, config=None)

    # Act:
    state_in = testing.State(
        leader=is_unit_leader, config=compose_charm_configs(SOME_VALID_USERID_HEADER_NAME)
    )
    state_out = ctx.run(ctx.on.update_status(), state_in)

    # Assert:
    if is_unit_leader:
        assert state_out.unit_status == testing.ActiveStatus()
    else:
        assert state_out.unit_status == testing.WaitingStatus(
            "[leadership-gate] Waiting for leadership"
        )


@pytest.mark.parametrize(
    "user_id_header_name_config_value, are_new_configs_expected_to_be_valid",
    [
        (SOME_VALID_USERID_HEADER_NAME, True),
        ("mlflow-userid", True),
        ("invalid:", False),
        ("not a valid one", False),
        ("kubeflow:userid", False),
    ],
)
@patch("charmed_kubeflow_chisme.components.LeadershipGateComponent.get_status")
@patch("components.oauth_integration.OAuthRequirerComponent.get_status")
@patch("components.request_auth_integration.RequestAuthRequirerComponent.get_status")
@patch("components.request_auth_integration.RequestAuthRequirerComponent._configure_app_leader")
def test_unit_status_based_on_whether_config_change_valid(
    _: MagicMock,
    mock_request_auth_integration_get_status: MagicMock,
    mock_oauth_integration_get_status: MagicMock,
    mock_leadership_gate_get_status: MagicMock,
    user_id_header_name_config_value,
    are_new_configs_expected_to_be_valid,
):
    """Test that the charm has the correct unit status after config-changed events."""
    # Arrange:
    mock_leadership_gate_get_status.return_value = testing.ActiveStatus()
    mock_oauth_integration_get_status.return_value = testing.ActiveStatus()
    mock_request_auth_integration_get_status.return_value = testing.ActiveStatus()
    ctx = testing.Context(RequestAuthenticationConfiguratorCharm, config=None)

    # Act:
    new_charm_configs = compose_charm_configs(user_id_header_name_config_value)
    state_in = testing.State(config=new_charm_configs)
    state_out = ctx.run(ctx.on.config_changed(), state_in)

    # Assert:
    if are_new_configs_expected_to_be_valid:
        assert state_out.unit_status == testing.ActiveStatus()
    else:
        assert state_out.unit_status == testing.BlockedStatus(
            f"[config-validation] invalid config change, '{CONFIG_KEY_FOR_USER_ID_HEADER_NAME}' "
            f"config value: '{user_id_header_name_config_value}'"
        )


@pytest.mark.parametrize("config", [{}, {CONFIG_KEY_FOR_USER_ID_HEADER_NAME: ""}])
@patch("charmed_kubeflow_chisme.components.LeadershipGateComponent.get_status")
@patch("components.oauth_integration.OAuthRequirerComponent.get_status")
@patch("components.request_auth_integration.RequestAuthRequirerComponent.get_status")
@patch("components.request_auth_integration.RequestAuthRequirerComponent._configure_app_leader")
def test_unit_status_when_config_missing(
    _: MagicMock,
    mock_request_auth_integration_get_status: MagicMock,
    mock_oauth_integration_get_status: MagicMock,
    mock_leadership_gate_get_status: MagicMock,
    config,
):
    """Test that the charm is blocked when the required config is unset (it has no default)."""
    # Arrange:
    mock_leadership_gate_get_status.return_value = testing.ActiveStatus()
    mock_oauth_integration_get_status.return_value = testing.ActiveStatus()
    mock_request_auth_integration_get_status.return_value = testing.ActiveStatus()
    ctx = testing.Context(RequestAuthenticationConfiguratorCharm, config=None)

    # Act:
    state_in = testing.State(config=config)
    state_out = ctx.run(ctx.on.config_changed(), state_in)

    # Assert:
    assert state_out.unit_status == testing.BlockedStatus(
        f"[config-validation] missing required config: '{CONFIG_KEY_FOR_USER_ID_HEADER_NAME}'"
    )


@pytest.mark.parametrize(
    "is_unit_leader, is_oauth_integration_established, is_provider_info_retrieved_successfully",
    list(product([False, True], repeat=3)),  # all permutations (possible tuples) of three booleans
)
@patch("charmed_kubeflow_chisme.components.LeadershipGateComponent.get_status")
@patch("components.config_validation.ConfigValidationComponent.get_status")
@patch("components.request_auth_integration.RequestAuthRequirerComponent.get_status")
@patch("components.request_auth_integration.RequestAuthRequirerComponent._configure_app_leader")
def test_integration_for_oauth(  # noqa: C901
    _: MagicMock,
    mock_request_auth_integration_get_status: MagicMock,
    mock_config_validation_get_status: MagicMock,
    mock_leadership_gate_get_status: MagicMock,
    is_unit_leader,
    is_oauth_integration_established,
    is_provider_info_retrieved_successfully,
):
    """Test that the charm behaves according to established OAuth integration."""
    # Arrange:

    user_id_header_name = SOME_VALID_USERID_HEADER_NAME

    mock_leadership_gate_get_status.return_value = testing.ActiveStatus()
    mock_config_validation_get_status.return_value = testing.ActiveStatus()
    mock_request_auth_integration_get_status.return_value = testing.ActiveStatus()

    ctx = testing.Context(RequestAuthenticationConfiguratorCharm, config=None)

    # Act:

    if is_provider_info_retrieved_successfully:
        provider_info_mock = MagicMock()
        provider_info_mock.issuer_url = JWT_ISSUER
        get_provider_info_return_value = provider_info_mock
    else:
        get_provider_info_return_value = None

    with patch.object(
        OAuthRequirer, "get_provider_info", return_value=get_provider_info_return_value
    ) as mock_get_provider_info:
        state_in = testing.State(
            config=compose_charm_configs(user_id_header_name),
            relations=compose_integrations(
                is_m2m_integration_established=False,  # irrelevant because mocked
                is_ui_integration_established=False,  # irrelevant because mocked
                is_oauth_integration_established=is_oauth_integration_established,
            ),
            leader=is_unit_leader,
        )
        with ctx(ctx.on.update_status(), state_in) as mgr:
            state_out = mgr.run()

            actual_jwt_issuer = None
            if is_oauth_integration_established and is_provider_info_retrieved_successfully:
                actual_jwt_issuer = mgr.charm.oauth.component.jwt_issuer

    # Assert:

    # unit status:
    if is_oauth_integration_established:
        if is_provider_info_retrieved_successfully:
            assert state_out.unit_status == testing.ActiveStatus()
        else:
            assert state_out.unit_status == testing.BlockedStatus(
                f"[{OAUTH_INTEGRATION_NAME}] Integration {OAUTH_INTEGRATION_NAME} established "
                "but provider information (including JWT issuer) not available yet"
            )
    else:
        assert state_out.unit_status == testing.BlockedStatus(
            f"[{OAUTH_INTEGRATION_NAME}] Integration {OAUTH_INTEGRATION_NAME} not established"
        )

    # calls to get JWT issuer:
    if is_oauth_integration_established:
        mock_get_provider_info.assert_called()
        if is_provider_info_retrieved_successfully:
            assert actual_jwt_issuer == JWT_ISSUER
    else:
        mock_get_provider_info.assert_not_called()


@pytest.mark.parametrize(
    "is_unit_leader, is_m2m_integration_established, is_ui_integration_established",
    list(product([False, True], repeat=3)),  # all permutations (possible tuples) of three booleans
)
@patch("charmed_kubeflow_chisme.components.LeadershipGateComponent.get_status")
@patch("components.config_validation.ConfigValidationComponent.get_status")
@patch("components.oauth_integration.OAuthRequirerComponent.get_status")
@patch(
    "components.oauth_integration.OAuthRequirerComponent.jwt_issuer",
    new_callable=PropertyMock,
    return_value=JWT_ISSUER,
)
def test_integrations_for_request_authentication(  # noqa: C901
    _: PropertyMock,
    mock_oauth_integration_get_status: MagicMock,
    mock_config_validation_get_status: MagicMock,
    mock_leadership_gate_get_status: MagicMock,
    is_unit_leader,
    is_m2m_integration_established,
    is_ui_integration_established,
):
    """Test that the charm behaves according to established RequestAuthentication integrations."""
    # Arrange:

    user_id_header_name = SOME_VALID_USERID_HEADER_NAME

    mock_leadership_gate_get_status.return_value = testing.ActiveStatus()
    mock_config_validation_get_status.return_value = testing.ActiveStatus()
    mock_oauth_integration_get_status.return_value = testing.ActiveStatus()

    m2m_request_auth_mock = MagicMock(name="m2m_request_auth")
    ui_request_auth_mock = MagicMock(name="ui_request_auth")

    integrations_to_mocks = {
        REQ_AUTH_INTEGRATION_NAME_FOR_M2M: m2m_request_auth_mock,
        REQ_AUTH_INTEGRATION_NAME_FOR_UI: ui_request_auth_mock,
    }

    ctx = testing.Context(RequestAuthenticationConfiguratorCharm, config=None)

    # Act:

    with patch(
        "components.request_auth_integration.IstioRequestAuthRequirer"
    ) as mock_istio_request_auth_requirer:
        mock_istio_request_auth_requirer.side_effect = (
            lambda _, relation_name: integrations_to_mocks[relation_name]
        )

        state_in = testing.State(
            config=compose_charm_configs(user_id_header_name),
            relations=compose_integrations(
                is_m2m_integration_established=is_m2m_integration_established,
                is_ui_integration_established=is_ui_integration_established,
                is_oauth_integration_established=False,  # irrelevant because mocked
            ),
            leader=is_unit_leader,
        )
        with ctx(ctx.on.update_status(), state_in) as mgr:
            state_out = mgr.run()

            # just to ensure that tests themselves are defined correctly:
            if is_unit_leader and is_m2m_integration_established:
                assert mgr.charm.m2m_request_auth.component.request_auth is m2m_request_auth_mock
            if is_unit_leader and is_ui_integration_established:
                assert mgr.charm.ui_request_auth.component.request_auth is ui_request_auth_mock

    # Assert:

    # unit status:
    if is_m2m_integration_established and is_ui_integration_established:
        assert state_out.unit_status == testing.ActiveStatus()
    elif is_m2m_integration_established:
        assert state_out.unit_status == testing.BlockedStatus(
            f"[{REQ_AUTH_INTEGRATION_NAME_FOR_UI}] Integration "
            f"{REQ_AUTH_INTEGRATION_NAME_FOR_UI} not established"
        )
    elif is_ui_integration_established:
        assert state_out.unit_status == testing.BlockedStatus(
            f"[{REQ_AUTH_INTEGRATION_NAME_FOR_M2M}] Integration "
            f"{REQ_AUTH_INTEGRATION_NAME_FOR_M2M} not established"
        )
    else:
        assert state_out.unit_status == testing.BlockedStatus(
            f"[{REQ_AUTH_INTEGRATION_NAME_FOR_M2M}] Integration "
            f"{REQ_AUTH_INTEGRATION_NAME_FOR_M2M} not established"
        )

    # calls to update RequestAuthentication data:
    if is_unit_leader and is_m2m_integration_established:
        m2m_request_auth_mock.publish_data.assert_called_once()
    else:
        m2m_request_auth_mock.publish_data.assert_not_called()
    if is_unit_leader and is_ui_integration_established:
        ui_request_auth_mock.publish_data.assert_called_once()
    else:
        ui_request_auth_mock.publish_data.assert_not_called()
