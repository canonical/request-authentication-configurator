"""Chisme components to manage ingress integration for RequestAuthentication custom resource."""

import logging

import ops
from charmed_kubeflow_chisme.components import Component
from charmlibs.interfaces.istio_request_auth import (
    ClaimToHeader,
    FromHeader,
    IstioRequestAuthRequirer,
    JWTRule,
)

logger = logging.getLogger(__name__)

JWT_HEADER_NAME = "Authorization"
JWT_HEADER_VALUE_PREFIX = "Bearer "


class RequestAuthRequirerComponent(Component):
    """Component to manage ingress integration for RequestAuthentication custom resource."""

    def __init__(
        self,
        *args,
        claim_to_header_mapping: dict[str, str],
        integration_name: str,
        jwt_issuer: str,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.claim_to_header_mapping = claim_to_header_mapping
        self.integration_name = integration_name
        self.jwt_issuer = jwt_issuer

        self._events_to_observe.append(
            getattr(self._charm.on, f"{self.integration_name.replace('-', '_')}_relation_changed")
        )

        self.request_auth = IstioRequestAuthRequirer(
            self._charm, relation_name=self.integration_name
        )

    def _configure_app_leader(self, event):
        """Update the integration data to have the RequestAuthentication up to date."""
        if self.is_integration_established:
            self.request_auth.publish_data([self.jwt_rule])

    def get_status(self):
        """Validate the integration for RequestAuthentication."""
        if not self.is_integration_established:
            message = f"Integration {self.integration_name} not established"
            logger.warning(message)
            return ops.BlockedStatus(message)
        return ops.ActiveStatus()

    @property
    def is_integration_established(self) -> bool:
        """Check if the integration is established."""
        return self._charm.model.get_relation(self.integration_name) is not None

    @property
    def jwt_rule(self) -> JWTRule:
        """Compose the JWT rule mapping the desired claim to the desired header."""
        return JWTRule(
            issuer=self.jwt_issuer,
            forward_original_token=True,
            claim_to_headers=[
                ClaimToHeader(header=header, claim=claim)
                for claim, header in self.claim_to_header_mapping.items()
            ],
            from_headers=[FromHeader(name=JWT_HEADER_NAME, prefix=JWT_HEADER_VALUE_PREFIX)],
        )

    @property
    def ready_for_execution(self) -> bool:
        """Return whether the component is ready for execution."""
        return self._charm.unit.is_leader()
