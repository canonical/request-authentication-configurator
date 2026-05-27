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

    def __init__(self, *args, claim_mapped_to_header, integration_name, jwt_issuer, **kwargs):
        super().__init__(*args, **kwargs)

        self.claim_mapped_to_header = claim_mapped_to_header
        self.integration_name = integration_name
        self.jwt_issuer = jwt_issuer

        self._events_to_observe.append(
            getattr(self._charm.on, f"{self.integration_name.replace('-', '_')}_relation_changed")
        )

    def _configure_app_leader(self, event):
        """Update the integration data to have the RequestAuthentication up to date."""
        self.request_auth = IstioRequestAuthRequirer(self, relation_name=self.integration_name)
        self.request_auth.publish_data([self.jwt_rule])

    def get_status(self):
        """Validate the integration for RequestAuthentication."""
        if self._charm.model.get_relation(self.integration_name) is None:
            message = f"Integration {self.integration_name} not established"
            logger.info(message)
            return ops.BlockedStatus(message)
        return ops.ActiveStatus()

    @property
    def jwt_rule(self) -> JWTRule:
        """Compose the JWT rule mapping the desired claim to the desired header."""
        return JWTRule(
            issuer=self.jwt_issuer,
            forward_original_token=True,
            claim_to_headers=[
                ClaimToHeader(header=self.user_id_header_name, claim=self.claim_mapped_to_header)
            ],
            from_headers=[FromHeader(name=JWT_HEADER_NAME, prefix=JWT_HEADER_VALUE_PREFIX)],
        )

    @property
    def ready_for_execution(self) -> bool:
        """Return whether the component is ready for execution."""
        return self._charm.unit.is_leader()
