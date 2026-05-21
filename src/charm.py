#!/usr/bin/env python3
# Copyright 2026 Ubuntu
# See LICENSE file for licensing details.

"""Charm the application."""

import logging

import ops

logger = logging.getLogger(__name__)

CONFIG_KEY_FOR_USER_ID_HEADER_NAME = "user-id-header-name"


class RequestAuthenticationIntegratorCharm(ops.CharmBase):
    """Charm the application."""

    def __init__(self, framework: ops.Framework):
        super().__init__(framework)
        framework.observe(self.on.config_changed, self._on_config_changed)
        framework.observe(self.on.leader_elected, self._on_leader_elected)

    def _on_config_changed(self, event: ops.ConfigChangedEvent):
        """Handle config-changed event."""
        logger.info(
            f"config change detected, new value for '{CONFIG_KEY_FOR_USER_ID_HEADER_NAME}': "
            f"{self.user_id_header_name}"
        )
        self._update_status()

    def _on_leader_elected(self, event: ops.LeaderElectedEvent):
        """Handle leader-elected event."""
        self._update_status()

    def _update_status(self):
        """Update unit and application status."""
        if self.is_user_id_header_name_valid:
            self.unit.status = ops.ActiveStatus()
            if self.unit.is_leader():
                self.app.status = ops.ActiveStatus()
        else:
            message = f"invalid config value for '{CONFIG_KEY_FOR_USER_ID_HEADER_NAME}'"
            self.unit.status = ops.BlockedStatus(message)
            if self.unit.is_leader():
                self.app.status = ops.BlockedStatus(message)

    @property
    def is_user_id_header_name_valid(self) -> bool:
        """Check whether the user ID header name is valid."""
        return self.user_id_header_name != ""

    @property
    def user_id_header_name(self) -> str:
        return self.model.config[CONFIG_KEY_FOR_USER_ID_HEADER_NAME]


if __name__ == "__main__":  # pragma: nocover
    ops.main(RequestAuthenticationIntegratorCharm)
