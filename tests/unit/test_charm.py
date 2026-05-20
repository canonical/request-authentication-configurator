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
    "new_configs, is_expected_to_be_valid",
    [
        (compose_charm_configs("kubeflow-userid"), True),
        (compose_charm_configs(""), False),
        (compose_charm_configs("mlflow-userid"), True),
    ]
)
def test_unit_status_based_on_whether_config_change_valid(new_configs, is_expected_to_be_valid):
    """Test that the charm has the correct state after handling the config-changed event."""
    # Arrange:
    ctx = testing.Context(RequestAuthenticationIntegratorCharm)
    state_in = testing.State(containers={})

    # Act:
    state_out = ctx.run(ctx.on.config_changed(new_configs), state_in)

    # Assert:
    assert state_out.unit_status == (
        testing.ActiveStatus()
        if is_expected_to_be_valid else
        testing.BlockedStatus(f"invalid config value for '{CONFIG_KEY_FOR_USER_ID_HEADER_NAME}'")
    )
