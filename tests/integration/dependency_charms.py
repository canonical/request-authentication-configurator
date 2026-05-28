"""Dependency charms for integration tests."""

from charmed_kubeflow_chisme.testing import CharmSpec

HYDRA = CharmSpec(charm="hydra", channel="latest/stable", trust=True)
ISTIO_INGRESS_K8S = CharmSpec(charm="istio-ingress-k8s", channel="dev/edge", trust=True)
ISTIO_K8S = CharmSpec(charm="istio-k8s", channel="dev/edge", trust=True, config={"platform": ""})
