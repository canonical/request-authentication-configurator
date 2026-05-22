# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.
#
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

import pytest
from ops import testing

from charm import RequestAuthenticationIntegratorCharm

CONFIG_KEY_FOR_USER_ID_HEADER_NAME = "user-id-header-name"


def compose_charm_configs(user_id_header_name: str) -> dict[str, str]:
    """Compose the charm configs given the user ID header name."""
    return {CONFIG_KEY_FOR_USER_ID_HEADER_NAME: user_id_header_name}


@pytest.mark.parametrize(
    "new_configs, are_new_configs_expected_to_be_valid, is_unit_leader",
    [
        (compose_charm_configs("kubeflow-userid"), True, True),
        (compose_charm_configs("mlflow-userid"), True, True),
        (compose_charm_configs(""), False, True),
        (compose_charm_configs("kubeflow-userid"), True, False),
        (compose_charm_configs("mlflow-userid"), True, False),
        (compose_charm_configs(""), False, False),
    ],
)
def test_app_and_unit_status_based_on_leadership_and_whether_config_change_valid(
    new_configs, are_new_configs_expected_to_be_valid, is_unit_leader
):
    """Test that the charm has the correct unit and app statuses after config-changed events."""
    # Arrange:
    ctx = testing.Context(RequestAuthenticationIntegratorCharm, config=None)

    # Act:
    state_in = testing.State(config=new_configs, leader=is_unit_leader)
    state_out = ctx.run(ctx.on.config_changed(), state_in)

    # Assert:
    if are_new_configs_expected_to_be_valid:
        assert state_out.unit_status == testing.ActiveStatus()
        assert state_out.app_status == (
            testing.ActiveStatus() if is_unit_leader else testing.UnknownStatus()
        )
    else:
        expected_message = f"invalid config value for '{CONFIG_KEY_FOR_USER_ID_HEADER_NAME}'"
        assert state_out.unit_status == testing.BlockedStatus(expected_message)
        assert state_out.app_status == (
            testing.BlockedStatus(expected_message) if is_unit_leader else testing.UnknownStatus()
        )
