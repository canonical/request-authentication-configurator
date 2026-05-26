# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.
#
# The integration tests use the Jubilant library. See https://documentation.ubuntu.com/jubilant/
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

import logging
import pathlib

import jubilant
import yaml

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(pathlib.Path("metadata.yaml").read_text())
CHARM_NAME = METADATA["name"]
APPLICATION_NAME = "-".join(("my", CHARM_NAME))
CONFIG_KEY_FOR_USER_ID_HEADER_NAME = "user-id-header-name"
INVALID_HEADER_NAME = "an invalid: header name"
VALID_HEADER_NAME = "kubeflow-userid"


def test_deploy(charm: pathlib.Path, juju: jubilant.Juju):
    """Deploy the charm under test."""
    juju.deploy(
        charm.resolve(),
        app=APPLICATION_NAME,
        resources={},
        config={CONFIG_KEY_FOR_USER_ID_HEADER_NAME: VALID_HEADER_NAME},
    )
    juju.wait(lambda status: status.apps[APPLICATION_NAME].is_active)


def test_update_config(juju: jubilant.Juju):
    """Verify charm config changes for the user-ID header name are validated correctly."""
    juju.config(APPLICATION_NAME, {CONFIG_KEY_FOR_USER_ID_HEADER_NAME: INVALID_HEADER_NAME})
    expected_invalid_config_message = (
        f"[config-validation] invalid config change, '{CONFIG_KEY_FOR_USER_ID_HEADER_NAME}' "
        f"config value: '{INVALID_HEADER_NAME}'"
    )
    juju.wait(
        lambda status: status.apps[APPLICATION_NAME].is_blocked
        and status.apps[APPLICATION_NAME].app_status.message == expected_invalid_config_message
    )

    juju.config(APPLICATION_NAME, {CONFIG_KEY_FOR_USER_ID_HEADER_NAME: VALID_HEADER_NAME})
    juju.wait(lambda status: status.apps[APPLICATION_NAME].is_active)
