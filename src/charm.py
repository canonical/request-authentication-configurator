#!/usr/bin/env python3
# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.

"""Charm the application."""

import logging

import ops
from charmed_kubeflow_chisme.components import CharmReconciler, LeadershipGateComponent

from components.config_validation import ConfigValidationComponent
from components.request_auth_integration import RequestAuthRequirerComponent

logger = logging.getLogger(__name__)

CONFIG_KEY_FOR_USER_ID_HEADER_NAME = "user-id-header-name"
INTEGRATION_NAME_FOR_M2M_REQUEST_AUTH = "m2m-request-auth"
INTEGRATION_NAME_FOR_UI_REQUEST_AUTH = "ui-request-auth"


class RequestAuthenticationIntegratorCharm(ops.CharmBase):
    """Charm the application."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)

        self.jwt_issuer = ""  # TODO

        self.charm_reconciler = CharmReconciler(self)

        self.leadership_gate = self.charm_reconciler.add(
            component=LeadershipGateComponent(charm=self, name="leadership-gate"),
            depends_on=[],
        )

        self.config_validation = self.charm_reconciler.add(
            component=ConfigValidationComponent(
                charm=self,
                name="config-validation",
                config_key_for_user_id_header_name=CONFIG_KEY_FOR_USER_ID_HEADER_NAME,
            ),
            depends_on=[self.leadership_gate],
        )

        self.m2m_request_auth = self.charm_reconciler.add(
            component=RequestAuthRequirerComponent(
                charm=self,
                name="m2m-request-auth",
                claim_mapped_to_header="sub",
                integration_name=INTEGRATION_NAME_FOR_M2M_REQUEST_AUTH,
                jwt_issuer=self.jwt_issuer,
            ),
            depends_on=[self.leadership_gate, self.config_validation],  # keep both explicit
        )

        self.ui_request_auth = self.charm_reconciler.add(
            component=RequestAuthRequirerComponent(
                charm=self,
                name="ui-request-auth",
                claim_mapped_to_header="email",
                integration_name=INTEGRATION_NAME_FOR_UI_REQUEST_AUTH,
                jwt_issuer=self.jwt_issuer,
            ),
            depends_on=[self.leadership_gate, self.config_validation],  # keep both explicit
        )

        self.charm_reconciler.install_default_event_handlers()

    @property
    def user_id_header_name(self) -> str:
        """Get the user ID header name from the respective charm config."""
        return str(self.model.config[CONFIG_KEY_FOR_USER_ID_HEADER_NAME])


if __name__ == "__main__":  # pragma: nocover
    ops.main(RequestAuthenticationIntegratorCharm)
