# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.
#
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

from itertools import product
from unittest.mock import MagicMock, patch

import pytest
from ops import testing

from charm import RequestAuthenticationIntegratorCharm

BLOCKED_STATUS_MESSAGE_FOR_MISSING_REQ_AUTH_INTEGRATION = (
    "[{missing_integration_name}] Integration {missing_integration_name} not established"
)
CONFIG_KEY_FOR_USER_ID_HEADER_NAME = "user-id-header-name"
REQ_AUTH_INTEGRATION_NAME_FOR_M2M = "m2m-request-auth"
REQ_AUTH_INTEGRATION_NAME_FOR_UI = "ui-request-auth"
SOME_VALID_USERID_HEADER_NAME = "kubeflow-userid"


def compose_charm_configs(user_id_header_name: str) -> dict[str, str]:
    """Compose the charm configs given the user ID header name."""
    return {CONFIG_KEY_FOR_USER_ID_HEADER_NAME: user_id_header_name}


def compose_request_auth_integrations(
    is_m2m_integration_established: bool, is_ui_integration_established: bool
) -> list[testing.Relation]:
    """Compose the RequestAuthentication integrations to include in the test state."""
    relations = []
    if is_m2m_integration_established:
        relations.append(testing.Relation(endpoint=REQ_AUTH_INTEGRATION_NAME_FOR_M2M))
    if is_ui_integration_established:
        relations.append(testing.Relation(endpoint=REQ_AUTH_INTEGRATION_NAME_FOR_UI))
    return relations


@pytest.mark.parametrize("is_unit_leader", [True, False])
@patch("components.config_validation.ConfigValidationComponent.get_status")
@patch("components.oauth_integration.OauthRequirerComponent.get_status")
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
    ctx = testing.Context(RequestAuthenticationIntegratorCharm, config=None)

    # Act:
    state_in = testing.State(
        leader=is_unit_leader,
        config=compose_charm_configs(SOME_VALID_USERID_HEADER_NAME)
    )
    state_out = ctx.run(ctx.on.config_changed(), state_in)

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
        ("", False),
        ("invalid:", False),
        ("not a valid one", False),
        ("kubeflow:userid", False),
    ],
)
@patch("charmed_kubeflow_chisme.components.LeadershipGateComponent.get_status")
@patch("components.oauth_integration.OauthRequirerComponent.get_status")
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
    ctx = testing.Context(RequestAuthenticationIntegratorCharm, config=None)

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


@pytest.mark.parametrize(
    "is_unit_leader, is_m2m_integration_established, is_ui_integration_established",
    list(product([False, True], repeat=3)),  # all permutations (possible tuples) of three booleans
)
@patch("charmed_kubeflow_chisme.components.LeadershipGateComponent.get_status")
@patch("components.config_validation.ConfigValidationComponent.get_status")
@patch("components.oauth_integration.OauthRequirerComponent.get_status")
@patch("components.request_auth_integration.RequestAuthRequirerComponent.jwt_issuer")
def test_integrations_for_request_authentication(  # noqa: C901
    mock_oauth_integration_jwt_issuer: MagicMock,
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
    mock_oauth_integration_jwt_issuer.return_value = "https://auth.example.com"

    m2m_request_auth_mock = MagicMock(name="m2m_request_auth")
    ui_request_auth_mock = MagicMock(name="ui_request_auth")

    def request_auth_requirer_factory(_, relation_name: str):
        if relation_name == REQ_AUTH_INTEGRATION_NAME_FOR_M2M:
            return m2m_request_auth_mock
        if relation_name == REQ_AUTH_INTEGRATION_NAME_FOR_UI:
            return ui_request_auth_mock
        raise AssertionError(f"Unexpected relation name: {relation_name}")

    ctx = testing.Context(RequestAuthenticationIntegratorCharm, config=None)

    # Act:

    with patch(
        "components.request_auth_integration.IstioRequestAuthRequirer"
    ) as mock_istio_request_auth_requirer:
        mock_istio_request_auth_requirer.side_effect = request_auth_requirer_factory
        state_in = testing.State(
            config=compose_charm_configs(user_id_header_name),
            relations=compose_request_auth_integrations(
                is_m2m_integration_established=is_m2m_integration_established,
                is_ui_integration_established=is_ui_integration_established,
            ),
            leader=is_unit_leader,
        )

        with ctx(ctx.on.config_changed(), state_in) as mgr:
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
            BLOCKED_STATUS_MESSAGE_FOR_MISSING_REQ_AUTH_INTEGRATION.format(
                missing_integration_name=REQ_AUTH_INTEGRATION_NAME_FOR_UI
            )
        )
    elif is_ui_integration_established:
        assert state_out.unit_status == testing.BlockedStatus(
            BLOCKED_STATUS_MESSAGE_FOR_MISSING_REQ_AUTH_INTEGRATION.format(
                missing_integration_name=REQ_AUTH_INTEGRATION_NAME_FOR_M2M
            )
        )
    else:
        assert state_out.unit_status == testing.BlockedStatus(
            BLOCKED_STATUS_MESSAGE_FOR_MISSING_REQ_AUTH_INTEGRATION.format(
                missing_integration_name=REQ_AUTH_INTEGRATION_NAME_FOR_M2M
            )
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
