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


def test_deploy(charm: pathlib.Path, juju: jubilant.Juju):
    """Deploy the charm under test."""
    juju.deploy(
        charm.resolve(),
        app=APPLICATION_NAME,
        resources={},
        config={CONFIG_KEY_FOR_USER_ID_HEADER_NAME: "kubeflow-userid"},
    )
    juju.wait(jubilant.all_active)
