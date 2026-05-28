# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.
#
# The integration tests use the Jubilant library. See https://documentation.ubuntu.com/jubilant/
# To learn more about testing, see https://documentation.ubuntu.com/ops/latest/explanation/testing/

import logging
import pathlib

import jubilant
import lightkube
import pytest
import yaml

from .dependency_charms import HYDRA, ISTIO_INGRESS_K8S, ISTIO_K8S, LOGIN_UI, POSTGRESQL, TRAEFIK

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(pathlib.Path("metadata.yaml").read_text())

APPLICATION_NAME_FOR_CHARM_UNDER_TEST = "-".join(("my", METADATA["name"]))
APPLICATION_NAME_FOR_HYDRA = "hydra"
APPLICATION_NAME_FOR_IDENTITY_DATABASE = "identity-database"
APPLICATION_NAME_FOR_INGRESS_FOR_M2M = "istio-ingress-m2m"
APPLICATION_NAME_FOR_INGRESS_FOR_UI = "istio-ingress-ui"
APPLICATION_NAME_FOR_ISTIO = "istio"
APPLICATION_NAME_FOR_LOGIN_UI = "login-ui"
APPLICATION_NAME_FOR_TRAEFIK = "traefik"

INTEGRATION_ENDPOINT_FOR_DATABASE_BY_HYDRA = "pg-database"
INTEGRATION_ENDPOINT_FOR_DATABASE_BY_POSTGRESQL = "database"
INTEGRATION_ENDPOINT_FOR_INGRESS_CONFIG = "istio-ingress-config"
INTEGRATION_ENDPOINT_FOR_UI_INFO = "ui-endpoint-info"
INTEGRATION_ENDPOINT_FOR_OAUTH_BY_HYDRA = "oauth"
INTEGRATION_ENDPOINT_FOR_OAUTH_BY_CHARM_UNDER_TEST = "oauth-jwt-issuer"
INTEGRATION_ENDPOINT_FOR_REQUEST_AUTH_BY_INGRESS = "istio-request-auth"
INTEGRATION_ENDPOINT_FOR_REQUEST_AUTH_BY_CHARM_UNDER_TEST_FOR_M2M = "request-auth-m2m"
INTEGRATION_ENDPOINT_FOR_REQUEST_AUTH_BY_CHARM_UNDER_TEST_FOR_UI = "request-auth-ui"
INTEGRATION_ENDPOINT_FOR_ROUTE_BY_HYDRA = "public-route"
INTEGRATION_ENDPOINT_FOR_ROUTE_BY_TRAEFIK = "traefik-route"

CONFIG_KEY_FOR_USER_ID_HEADER_NAME = "user-id-header-name"
INVALID_HEADER_NAME = "an invalid: header name"
VALID_HEADER_NAME_BEFORE_CONFIG_CHANGE = "kubeflow-userid"
VALID_HEADER_NAME_AFTER_CONFIG_CHANGE = "mlflow-userid"

EXPECTED_JWT_CLAIM_BY_INGRESS = {
    APPLICATION_NAME_FOR_INGRESS_FOR_M2M: "sub",
    APPLICATION_NAME_FOR_INGRESS_FOR_UI: "email",
}

REQUEST_AUTHENTICATION_CUSTOM_RESOURCE = lightkube.generic_resource.create_namespaced_resource(  # pyright: ignore [reportAttributeAccessIssue] noqa: E501
    group="security.istio.io",
    version="v1",
    kind="RequestAuthentication",
    plural="requestauthentications",
)


@pytest.fixture(scope="session")
def juju_model_namespace(juju: jubilant.Juju) -> str:
    return juju.model.split(":")[-1] if juju.model else juju.show_model().short_name


@pytest.fixture(scope="session")
def lightkube_client() -> lightkube.Client:
    client = lightkube.Client()
    return client


def verify_request_authentication_resources_as_expected(
    expected_header_name: str,
    request_authentication_resources: list,
) -> None:
    """Verify the two RequestAuthentication resources are created as expected."""
    claims_left_to_verify = set(EXPECTED_JWT_CLAIM_BY_INGRESS.values())

    for req_auth in request_authentication_resources:
        req_auth_name = req_auth.metadata.name
        # TODO: check `claimToHeaders` is not relied on

        jwt_rules = req_auth.get("spec", {}).get("jwtRules", [])
        assert len(jwt_rules) == 1, (
            f"Expected one jwtRules entry for RequestAuthentication '{req_auth_name}', "
            f"but found {len(jwt_rules)}"
        )

        claim_to_header_mapping = jwt_rules[0].get("outputClaimToHeaders")
        assert claim_to_header_mapping is not None, (
            "Expected one claim-to-header mapping in RequestAuthentication "
            f"'{req_auth_name}', but none was found"
        )
        assert len(claim_to_header_mapping) == 1, (
            "Expected exactly one claim-to-header mapping in RequestAuthentication "
            f"'{req_auth_name}', but found {len(claim_to_header_mapping)}"
        )

        only_mapping = claim_to_header_mapping[0]
        actual_claim_name = only_mapping.get("claim")
        actual_header_name = only_mapping.get("header")

        assert actual_header_name == expected_header_name, (
            "Expected claim-to-header mapping to use header "
            f"'{expected_header_name}' in RequestAuthentication '{req_auth_name}', "
            f"but found '{actual_header_name}'"
        )

        target_refs = req_auth.get("spec", {}).get("targetRefs", [])
        assert len(target_refs) == 1, (
            f"Expected exactly one targetRef in RequestAuthentication '{req_auth_name}', "
            f"but found {len(target_refs)}"
        )
        target_ref = target_refs[0]
        associated_ingress = str(target_ref.get("name", ""))
        assert associated_ingress in EXPECTED_JWT_CLAIM_BY_INGRESS, (
            "Unable to recognize/determine associated ingress for RequestAuthentication "
            f"'{req_auth_name}': '{associated_ingress}'"
        )

        expected_claim_name = EXPECTED_JWT_CLAIM_BY_INGRESS[associated_ingress]
        assert expected_claim_name == actual_claim_name, (
            "Unexpected claim in claim-to-header mapping for RequestAuthentication "
            f"'{req_auth_name}' associated to ingress {associated_ingress}: "
            f"expected '{expected_claim_name}', found '{actual_claim_name}'"
        )

        claims_left_to_verify.remove(expected_claim_name)

    assert not claims_left_to_verify, "Ill-conceived test."


def test_deploy_charm_under_test(charm: pathlib.Path, juju: jubilant.Juju):
    """Deploy the charm under test and verify it gets blocked."""
    logger.info("Deploying the charm under test...")
    juju.deploy(
        charm.resolve(),
        app=APPLICATION_NAME_FOR_CHARM_UNDER_TEST,
        resources={},
        config={CONFIG_KEY_FOR_USER_ID_HEADER_NAME: VALID_HEADER_NAME_BEFORE_CONFIG_CHANGE},
        # trust=True,  # TODO: understand if necessary
    )

    logger.info("Waiting for the charm under test to reach blocked status...")
    juju.wait(lambda status: status.apps[APPLICATION_NAME_FOR_CHARM_UNDER_TEST].is_blocked)


def test_deploy_istio_and_its_ingresses(juju: jubilant.Juju):
    """Deploy Istio and its K8s Gateway-based ingresses and verify they are active."""
    logger.info("Deploying Istio and its ingresses...")
    for charm, application_name in (
        (ISTIO_INGRESS_K8S, APPLICATION_NAME_FOR_INGRESS_FOR_M2M),
        (ISTIO_INGRESS_K8S, APPLICATION_NAME_FOR_INGRESS_FOR_UI),
        (ISTIO_K8S, APPLICATION_NAME_FOR_ISTIO),
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


def test_deploy_identity_provider_charms(juju: jubilant.Juju):
    """Deploy the identity provider charms and verify they are active."""
    logger.info("Deploying the identity provider charms...")
    for charm, application_name in (
        (HYDRA, APPLICATION_NAME_FOR_HYDRA),
        (LOGIN_UI, APPLICATION_NAME_FOR_LOGIN_UI),
        (POSTGRESQL, APPLICATION_NAME_FOR_IDENTITY_DATABASE),
        (TRAEFIK, APPLICATION_NAME_FOR_TRAEFIK),
    ):
        juju.deploy(
            app=application_name,
            charm=charm.charm,
            channel=charm.channel,
            config=charm.config,
            trust=charm.trust,
        )

    logger.info("Integrating the identity provider charms...")
    juju.integrate(
        f"{APPLICATION_NAME_FOR_HYDRA}:{INTEGRATION_ENDPOINT_FOR_DATABASE_BY_HYDRA}",
        f"{APPLICATION_NAME_FOR_IDENTITY_DATABASE}:{INTEGRATION_ENDPOINT_FOR_DATABASE_BY_POSTGRESQL}",
    )
    juju.integrate(
        f"{APPLICATION_NAME_FOR_HYDRA}:{INTEGRATION_ENDPOINT_FOR_ROUTE_BY_HYDRA}",
        f"{APPLICATION_NAME_FOR_TRAEFIK}:{INTEGRATION_ENDPOINT_FOR_ROUTE_BY_TRAEFIK}",
    )
    juju.integrate(
        f"{APPLICATION_NAME_FOR_HYDRA}:{INTEGRATION_ENDPOINT_FOR_UI_INFO}",
        f"{APPLICATION_NAME_FOR_LOGIN_UI}:{INTEGRATION_ENDPOINT_FOR_UI_INFO}",
    )

    logger.info("Waiting for the identity provider charms to be active...")
    juju.wait(
        lambda status: (
            status.apps[APPLICATION_NAME_FOR_HYDRA].is_active
            and status.apps[APPLICATION_NAME_FOR_IDENTITY_DATABASE].is_active
            and status.apps[APPLICATION_NAME_FOR_LOGIN_UI].is_active
            and status.apps[APPLICATION_NAME_FOR_TRAEFIK].is_active
        )
    )


def test_no_request_authentication_resources_before_integrations(
    juju_model_namespace: str,
    lightkube_client: lightkube.Client,
):
    """Verify no RequestAuthentication resources are created so far (before integrations)."""
    req_auth_resources = list(
        lightkube_client.list(
            REQUEST_AUTHENTICATION_CUSTOM_RESOURCE,
            namespace=juju_model_namespace,
        )
    )

    assert len(req_auth_resources) == 0, (
        f"Expected no RequestAuthentication resources in namespace '{juju_model_namespace}' "
        f"before integrations, but found: {[item.metadata.name for item in req_auth_resources]}"
    )


def test_integrate_charm_under_test(juju: jubilant.Juju):
    """Verify the charm under test can integrate with the OAuth provider and the ingresses."""
    logger.info("Integrating the charm under test...")
    juju.integrate(
        f"{APPLICATION_NAME_FOR_CHARM_UNDER_TEST}:{INTEGRATION_ENDPOINT_FOR_OAUTH_BY_CHARM_UNDER_TEST}",
        f"{APPLICATION_NAME_FOR_HYDRA}:{INTEGRATION_ENDPOINT_FOR_OAUTH_BY_HYDRA}",
    )
    juju.integrate(
        f"{APPLICATION_NAME_FOR_CHARM_UNDER_TEST}:{INTEGRATION_ENDPOINT_FOR_REQUEST_AUTH_BY_CHARM_UNDER_TEST_FOR_M2M}",
        f"{APPLICATION_NAME_FOR_INGRESS_FOR_M2M}:{INTEGRATION_ENDPOINT_FOR_REQUEST_AUTH_BY_INGRESS}",
    )
    juju.integrate(
        f"{APPLICATION_NAME_FOR_CHARM_UNDER_TEST}:{INTEGRATION_ENDPOINT_FOR_REQUEST_AUTH_BY_CHARM_UNDER_TEST_FOR_UI}",
        f"{APPLICATION_NAME_FOR_INGRESS_FOR_UI}:{INTEGRATION_ENDPOINT_FOR_REQUEST_AUTH_BY_INGRESS}",
    )

    logger.info("Waiting for the charm under test to be active...")
    juju.wait(lambda status: status.apps[APPLICATION_NAME_FOR_CHARM_UNDER_TEST].is_active)


def test_create_request_authentication_resources_after_integrations(
    juju_model_namespace: str,
    lightkube_client: lightkube.Client,
):
    """Verify the expected RequestAuthentication resources are created after integrations."""
    req_auth_resources = list(
        lightkube_client.list(
            REQUEST_AUTHENTICATION_CUSTOM_RESOURCE,
            namespace=juju_model_namespace,
        )
    )

    assert len(req_auth_resources) == 2, (
        f"Expected two RequestAuthentication resources in namespace '{juju_model_namespace}' "
        f"after integrations, but found: {[item.metadata.name for item in req_auth_resources]}"
    )

    verify_request_authentication_resources_as_expected(
        expected_header_name=VALID_HEADER_NAME_BEFORE_CONFIG_CHANGE,
        request_authentication_resources=req_auth_resources,
    )


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
        {CONFIG_KEY_FOR_USER_ID_HEADER_NAME: VALID_HEADER_NAME_AFTER_CONFIG_CHANGE},
    )
    juju.wait(lambda status: status.apps[APPLICATION_NAME_FOR_CHARM_UNDER_TEST].is_active)


def test_update_request_authentication_resources_after_config_changes(
    juju_model_namespace: str,
    lightkube_client: lightkube.Client,
):
    """Verify RequestAuthentication resources are updated after config changes."""
    req_auth_resources = list(
        lightkube_client.list(
            REQUEST_AUTHENTICATION_CUSTOM_RESOURCE,
            namespace=juju_model_namespace,
        )
    )

    assert len(req_auth_resources) == 2, (
        f"Expected two RequestAuthentication resources in namespace '{juju_model_namespace}' "
        f"after integrations, but found: {[item.metadata.name for item in req_auth_resources]}"
    )

    verify_request_authentication_resources_as_expected(
        expected_header_name=VALID_HEADER_NAME_AFTER_CONFIG_CHANGE,
        request_authentication_resources=req_auth_resources,
    )
