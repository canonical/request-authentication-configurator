"""Chisme components to manage OAuth integration to obtain JWT issuer."""

import logging

import ops
from charmed_kubeflow_chisme.components import Component
from charms.hydra.v0.oauth import OAuthRequirer

logger = logging.getLogger(__name__)


class OAuthRequirerComponent(Component):
    """Component to manage OAuth integration to obtain JWT issuer."""

    def __init__(self, *args, integration_name: str = "oauth", **kwargs):
        super().__init__(*args, **kwargs)

        self.integration_name = integration_name

        self.oauth = OAuthRequirer(
            self._charm, client_config=None, relation_name=self.integration_name
        )

        self._events_to_observe.extend(
            [
                getattr(
                    self._charm.on, f"{self.integration_name.replace('-', '_')}_relation_changed"
                ),
                self.oauth.on.oauth_info_changed,
            ]
        )

    def get_status(self):
        """Validate the integration for the JWT issuer."""
        if not self.is_integration_established:
            message = f"Integration {self.integration_name} not established"
            logger.warning(message)
            return ops.BlockedStatus(message)

        if self.jwt_issuer is None:
            message = (
                f"Integration {self.integration_name} established but provider information"
                " (including JWT issuer) not available yet"
            )
            logger.info(message)
            return ops.BlockedStatus(message)

        return ops.ActiveStatus()

    @property
    def is_integration_established(self) -> bool:
        """Check if the integration is established."""
        return self._charm.model.get_relation(self.integration_name) is not None

    @property
    def jwt_issuer(self) -> str | None:
        """Obtain the up-to-date JWT issuer from the integration data."""
        if self.is_integration_established:
            provider_info = self.oauth.get_provider_info()

            if provider_info is not None:
                return provider_info.issuer_url

        return None

    @property
    def ready_for_execution(self) -> bool:
        """Return whether the component is ready for execution."""
        return self._charm.unit.is_leader()
