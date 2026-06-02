"""Dependency charms for integration tests."""

from charmed_kubeflow_chisme.testing import CharmSpec

# for the identity provider yielding the JWT issuer:
HYDRA = CharmSpec(charm="hydra", channel="latest/stable", trust=True, config={"dev": True})
LOGIN_UI = CharmSpec(
    charm="identity-platform-login-ui-operator",
    channel="latest/stable",
    trust=True,
)
POSTGRESQL = CharmSpec(
    charm="postgresql-k8s",
    channel="14/stable",
    trust=True,
    config={
        "plugin_btree_gin_enable": True,
        "plugin_pg_trgm_enable": True,
        "profile": "testing",
    },
)
TRAEFIK = CharmSpec(charm="traefik-k8s", channel="latest/stable", trust=True)

# for the two Istio ingresses managing one respective RequestAuthentication resource each:
ISTIO_CHANNEL = "dev/edge"
# NOTE: this is the only channel to provide the necessary "istio-request-auth" integration:
# https://charmhub.io/istio-ingress-k8s/integrations?channel=dev/edge
ISTIO_INGRESS_K8S = CharmSpec(charm="istio-ingress-k8s", channel=ISTIO_CHANNEL, trust=True)
ISTIO_K8S = CharmSpec(charm="istio-k8s", channel=ISTIO_CHANNEL, trust=True, config={"platform": ""})
