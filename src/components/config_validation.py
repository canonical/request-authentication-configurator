"""Chisme components to validate config changes."""

import logging

import ops
from charmed_kubeflow_chisme.components import Component

logger = logging.getLogger(__name__)


class ConfigValidationComponent(Component):
    """Component to manage config-changed events."""

    def __init__(self, *args, config_key_for_user_id_header_name, **kwargs):
        super().__init__(*args, **kwargs)
        self._events_to_observe.append(getattr(self._charm.on, "config_changed"))

        self._component_status = ops.UnknownStatus()
        self._config_key_for_user_id_header_name = config_key_for_user_id_header_name

    @staticmethod
    def is_user_id_header_name_valid(user_id_header_name) -> bool:
        """Check whether the user ID header name is valid."""
        return user_id_header_name != ""

    @property
    def ready_for_execution(self) -> bool:
        """Return whether the component is ready for execution."""
        return self._charm.unit.is_leader()

    def _configure_app_leader(self, _):
        """Validate the provided config value for the user-ID header name."""
        user_id_header_name = str(
            self._charm.model.config[self._config_key_for_user_id_header_name]
        )

        message = (
            f"'{self._config_key_for_user_id_header_name}' config value: '{user_id_header_name}'"
        )

        logger.info(f"config change detected, {message}")

        if self.is_user_id_header_name_valid(user_id_header_name):
            self._component_status = ops.ActiveStatus()
        else:
            self._component_status = ops.BlockedStatus(f"invalid config change, {message}")

    def get_status(self):
        """Return the status."""
        return self._component_status
