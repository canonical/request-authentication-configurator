# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.
#
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

from unittest.mock import MagicMock, patch

import pytest
from ops import testing

from charm import RequestAuthenticationIntegratorCharm

CONFIG_KEY_FOR_USER_ID_HEADER_NAME = "user-id-header-name"


def compose_charm_configs(user_id_header_name: str) -> dict[str, str]:
    """Compose the charm configs given the user ID header name."""
    return {CONFIG_KEY_FOR_USER_ID_HEADER_NAME: user_id_header_name}


@pytest.mark.parametrize("is_unit_leader", [True, False])
@patch("components.config_validation.ConfigValidationComponent.get_status")
@patch("components.request_auth_integration.RequestAuthRequirerComponent.get_status")
@patch("components.request_auth_integration.RequestAuthRequirerComponent._configure_app_leader")
def test_unit_status_based_on_leadership(
    _: MagicMock,
    mock_request_auth_integration_get_status: MagicMock,
    mock_config_validation_get_status: MagicMock,
    is_unit_leader,
):
    """Test that the charm has the correct unit status based on leadership."""
    # Arrange:
    mock_config_validation_get_status.return_value = testing.ActiveStatus()
    mock_request_auth_integration_get_status.return_value = testing.ActiveStatus()
    ctx = testing.Context(RequestAuthenticationIntegratorCharm, config=None)

    # Act:
    state_in = testing.State(leader=is_unit_leader)
    state_out = ctx.run(ctx.on.config_changed(), state_in)

    # Assert:
    if is_unit_leader:
        assert state_out.unit_status == testing.ActiveStatus()
    else:
        expected_message = "[leadership-gate] Waiting for leadership"
        assert state_out.unit_status == testing.WaitingStatus(expected_message)


@pytest.mark.parametrize(
    "user_id_header_name_config_value, are_new_configs_expected_to_be_valid",
    [
        ("kubeflow-userid", True),
        ("mlflow-userid", True),
        ("", False),
        ("invalid:", False),
        ("not a valid one", False),
        ("kubeflow:userid", False),
    ],
)
@patch("components.request_auth_integration.RequestAuthRequirerComponent.get_status")
@patch("components.request_auth_integration.RequestAuthRequirerComponent._configure_app_leader")
def test_unit_status_based_on_whether_config_change_valid(
    _: MagicMock,
    mock_request_auth_integration_get_status: MagicMock,
    user_id_header_name_config_value,
    are_new_configs_expected_to_be_valid,
):
    """Test that the charm has the correct unit status after config-changed events."""
    # Arrange:
    mock_request_auth_integration_get_status.return_value = testing.ActiveStatus()
    ctx = testing.Context(RequestAuthenticationIntegratorCharm, config=None)

    # Act:
    new_charm_configs = compose_charm_configs(user_id_header_name_config_value)
    state_in = testing.State(config=new_charm_configs, leader=True)
    state_out = ctx.run(ctx.on.config_changed(), state_in)

    # Assert:
    if are_new_configs_expected_to_be_valid:
        assert state_out.unit_status == testing.ActiveStatus()
    else:
        expected_message = (
            f"invalid config change, '{CONFIG_KEY_FOR_USER_ID_HEADER_NAME}' config value: "
            f"'{user_id_header_name_config_value}'"
        )
        assert state_out.unit_status == testing.BlockedStatus(
            f"[config-validation] {expected_message}"
        )
