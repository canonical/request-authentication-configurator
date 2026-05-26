"""Chisme components to validate config changes."""

import logging
import re

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

    _VALID_HEADER_NAME_RE = re.compile(r"^[!#$%&'*+\-.^_`|~A-Za-z0-9]+$")

    @staticmethod
    def is_valid_http_header_field(header_name: str) -> bool:
        """Check whether the given string is a valid HTTP header field name.

        Per RFC 7230, a header field name is a "token", defined as one or more "tchar" characters:

            tchar = "!" / "#" / "$" / "%" / "&" / "'" / "*" / "+"
                  / "-" / "." / "^" / "_" / "`" / "|" / "~" / DIGIT / ALPHA

        This means the name must be non-empty and consist only of visible ASCII characters
        excluding delimiters (spaces, tabs, and other separators are not allowed).

        References:
            https://httpwg.org/specs/rfc7230.html#rule.token.separators
            https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers
        """
        return bool(ConfigValidationComponent._VALID_HEADER_NAME_RE.match(header_name))

    @property
    def ready_for_execution(self) -> bool:
        """Return whether the component is ready for execution."""
        return self._charm.unit.is_leader()

    def _configure_app_leader(self, event):
        """Validate the provided config value for the user-ID header name."""
        user_id_header_name = str(
            self._charm.model.config[self._config_key_for_user_id_header_name]
        )

        message = (
            f"'{self._config_key_for_user_id_header_name}' config value: '{user_id_header_name}'"
        )

        logger.info(f"config change detected, {message}")

        if self.is_valid_http_header_field(user_id_header_name):
            self._component_status = ops.ActiveStatus()
        else:
            self._component_status = ops.BlockedStatus(f"invalid config change, {message}")

        # NOTE: Chisme only sets unit status - via `self.get_status()` - on its own, so it is
        # required to explicitly set the app status for it not to be left unknown:
        self._charm.app.status = self._component_status

    def get_status(self):
        """Return the status."""
        return self._component_status
