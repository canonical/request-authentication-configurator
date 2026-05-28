# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.
#
# The integration tests use the Jubilant library. See https://documentation.ubuntu.com/jubilant/
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

import logging
import pathlib

import jubilant
import yaml

from .dependency_charms import HYDRA, ISTIO_INGRESS_K8S, ISTIO_K8S

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(pathlib.Path("metadata.yaml").read_text())

APPLICATION_NAME_FOR_CHARM_UNDER_TEST = "-".join(("my", METADATA["name"]))
APPLICATION_NAME_FOR_HYDRA = "hydra"
APPLICATION_NAME_FOR_INGRESS_FOR_M2M = "istio-ingress-m2m"
APPLICATION_NAME_FOR_INGRESS_FOR_UI = "istio-ingress-ui"
APPLICATION_NAME_FOR_ISTIO = "istio"

INTEGRATION_ENDPOINT_FOR_INGRESS_CONFIG = "istio-ingress-config"
INTEGRATION_ENDPOINT_FOR_OAUTH_BY_HYDRA = "oauth"
INTEGRATION_ENDPOINT_FOR_OAUTH_BY_CHARM_UNDER_TEST = "oauth-jwt-issuer"
INTEGRATION_ENDPOINT_FOR_REQUEST_AUTH_BY_INGRESS = "istio-request-auth"
INTEGRATION_ENDPOINT_FOR_REQUEST_AUTH_BY_CHARM_UNDER_TEST_FOR_M2M = "request-auth-m2m"
INTEGRATION_ENDPOINT_FOR_REQUEST_AUTH_BY_CHARM_UNDER_TEST_FOR_UI = "request-auth-ui"

CONFIG_KEY_FOR_USER_ID_HEADER_NAME = "user-id-header-name"
INVALID_HEADER_NAME = "an invalid: header name"
VALID_HEADER_NAME_BEFORE = "kubeflow-userid"
VALID_HEADER_NAME_AFTER = "mlflow-userid"


def test_deploy_charm_under_test(charm: pathlib.Path, juju: jubilant.Juju):
    """Deploy the charm under test and verify it gets blocked."""
    logger.info("Deploying the charm under test...")
    juju.deploy(
        charm.resolve(),
        app=APPLICATION_NAME_FOR_CHARM_UNDER_TEST,
        resources={},
        config={CONFIG_KEY_FOR_USER_ID_HEADER_NAME: VALID_HEADER_NAME_BEFORE},
        # trust=True,  # TODO: undestand if necessary
    )

    logger.info("Waiting for the charm under test to reach blocked status...")
    juju.wait(lambda status: status.apps[APPLICATION_NAME_FOR_CHARM_UNDER_TEST].is_blocked)


def test_deploy_istio_and_its_ingresses(juju: jubilant.Juju):
    """Deploy Istio and its K8s Gateway-based ingresses and verify they are active."""
    logger.info("Deploying Istio and its ingresses...")
    for charm, application_name in (
        (ISTIO_K8S, APPLICATION_NAME_FOR_ISTIO),
        (ISTIO_INGRESS_K8S, APPLICATION_NAME_FOR_INGRESS_FOR_M2M),
        (ISTIO_INGRESS_K8S, APPLICATION_NAME_FOR_INGRESS_FOR_UI),
    ):
        juju.deploy(
            app=application_name,
            charm=charm.charm,
            channel=charm.channel,
            config=charm.config,
            trust=charm.trust,
        )

    logger.info("Integrating Istio with its ingresses...")
    juju.integrate(
        f"{APPLICATION_NAME_FOR_ISTIO}:{INTEGRATION_ENDPOINT_FOR_INGRESS_CONFIG}",
        f"{APPLICATION_NAME_FOR_INGRESS_FOR_M2M}:{INTEGRATION_ENDPOINT_FOR_INGRESS_CONFIG}",
    )
    juju.integrate(
        f"{APPLICATION_NAME_FOR_ISTIO}:{INTEGRATION_ENDPOINT_FOR_INGRESS_CONFIG}",
        f"{APPLICATION_NAME_FOR_INGRESS_FOR_UI}:{INTEGRATION_ENDPOINT_FOR_INGRESS_CONFIG}",
    )

    logger.info("Waiting for Istio and its ingresses to be active...")
    juju.wait(
        lambda status: (
            status.apps[APPLICATION_NAME_FOR_ISTIO].is_active
            and status.apps[APPLICATION_NAME_FOR_INGRESS_FOR_M2M].is_active
            and status.apps[APPLICATION_NAME_FOR_INGRESS_FOR_UI].is_active
        )
    )


def test_deploy_oauth_provider(juju: jubilant.Juju):
    """Deploy the Oauth provider and verify it is active."""
    logger.info("Deploying the identity provider...")
    for charm, application_name in (
        (HYDRA, APPLICATION_NAME_FOR_HYDRA),
        # (..., ...),  # TODO
    ):
        juju.deploy(
            app=application_name,
            charm=charm.charm,
            channel=charm.channel,
            config=charm.config,
            trust=charm.trust,
        )

    logger.info("Waiting for the identity provider to be active...")
    juju.wait(
        lambda status: (
            status.apps[APPLICATION_NAME_FOR_HYDRA].is_active
            # and status.apps[...].is_active  # TODO
        )
    )


def test_no_request_authentication_resources_before_integrations(juju: jubilant.Juju):
    """Verify no RequestAuthentication resources are created so far (before integrations)."""
    ...  # TODO


def test_integrate_charm_under_test(juju: jubilant.Juju):
    """Verify the charm under test can integrate with the Oauth provider and the ingresses."""
    ...  # TODO


def test_create_request_authentication_resources_after_integrations(juju: jubilant.Juju):
    ...  # TODO
    """Verify the expected RequestAuthentication resources are created after integrations."""


def test_update_config(juju: jubilant.Juju):
    """Verify charm config changes for the user-ID header name are validated correctly."""
    # for invalid config changes, the charm gets blocked:
    expected_invalid_config_message = (
        f"[config-validation] invalid config change, '{CONFIG_KEY_FOR_USER_ID_HEADER_NAME}' "
        f"config value: '{INVALID_HEADER_NAME}'"
    )
    juju.config(
        APPLICATION_NAME_FOR_CHARM_UNDER_TEST,
        {CONFIG_KEY_FOR_USER_ID_HEADER_NAME: INVALID_HEADER_NAME},
    )
    juju.wait(
        lambda status: (
            status.apps[APPLICATION_NAME_FOR_CHARM_UNDER_TEST].is_blocked
            and (
                status.apps[APPLICATION_NAME_FOR_CHARM_UNDER_TEST].app_status.message
                == expected_invalid_config_message
            )
        )
    )

    # for valid config changes, the charm gets active:
    juju.config(
        APPLICATION_NAME_FOR_CHARM_UNDER_TEST,
        {CONFIG_KEY_FOR_USER_ID_HEADER_NAME: VALID_HEADER_NAME_AFTER},
    )
    juju.wait(lambda status: status.apps[APPLICATION_NAME_FOR_CHARM_UNDER_TEST].is_active)


def test_update_request_authentication_resources_after_config_changes(juju: jubilant.Juju):
    ...  # TODO
    """Verify RequestAuthentication resources are updated after config changes."""
