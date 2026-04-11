"""Traffic shaper (pipes, queues, rules) methods for OPNsenseClient."""

from collections.abc import MutableMapping
from typing import Any

from ._typing import PyOPNsenseClientProtocol
from .helpers import _LOGGER, _log_errors


class TrafficShaperMixin(PyOPNsenseClientProtocol):
    """Traffic shaper methods for OPNsenseClient."""

    @_log_errors
    async def get_traffic_shaper(self) -> dict[str, Any]:
        """Retrieve all traffic shaper pipes, queues, and rules from OPNsense.

        Returns:
            dict[str, Any]: Normalized data returned by the related OPNsense endpoint.
        """
        shaper: dict[str, Any] = {}
        shaper["pipes"] = await self._get_shaper_pipes()
        shaper["queues"] = await self._get_shaper_queues()
        shaper["rules"] = await self._get_shaper_rules()
        return shaper

    @_log_errors
    async def _get_shaper_pipes(self) -> dict[str, Any]:
        """Retrieve traffic shaper pipes from OPNsense.

        Returns:
            dict[str, Any]: Mapping of pipe UUIDs to pipe details.
        """
        endpoint = "/api/trafficshaper/settings/search_pipes"
        if not await self.is_endpoint_available(endpoint):
            _LOGGER.debug("Traffic shaper pipes endpoint not available")
            return {}

        response = await self._safe_dict_get(endpoint)
        rows: list = response.get("rows", [])
        pipes: dict[str, Any] = {}
        for row in rows:
            if not isinstance(row, MutableMapping):
                continue
            uuid = row.get("uuid")
            if not uuid:
                continue
            pipes[str(uuid)] = dict(row)
        _LOGGER.debug("[_get_shaper_pipes] pipes length: %s", len(pipes))
        return pipes

    @_log_errors
    async def _get_shaper_queues(self) -> dict[str, Any]:
        """Retrieve traffic shaper queues from OPNsense.

        Returns:
            dict[str, Any]: Mapping of queue UUIDs to queue details.
        """
        endpoint = "/api/trafficshaper/settings/search_queues"
        if not await self.is_endpoint_available(endpoint):
            _LOGGER.debug("Traffic shaper queues endpoint not available")
            return {}

        response = await self._safe_dict_get(endpoint)
        rows: list = response.get("rows", [])
        queues: dict[str, Any] = {}
        for row in rows:
            if not isinstance(row, MutableMapping):
                continue
            uuid = row.get("uuid")
            if not uuid:
                continue
            queues[str(uuid)] = dict(row)
        _LOGGER.debug("[_get_shaper_queues] queues length: %s", len(queues))
        return queues

    @_log_errors
    async def _get_shaper_rules(self) -> dict[str, Any]:
        """Retrieve traffic shaper rules from OPNsense.

        Returns:
            dict[str, Any]: Mapping of rule UUIDs to rule details.
        """
        endpoint = "/api/trafficshaper/settings/search_rules"
        if not await self.is_endpoint_available(endpoint):
            _LOGGER.debug("Traffic shaper rules endpoint not available")
            return {}

        response = await self._safe_dict_get(endpoint)
        rows: list = response.get("rows", [])
        rules: dict[str, Any] = {}
        for row in rows:
            if not isinstance(row, MutableMapping):
                continue
            uuid = row.get("uuid")
            if not uuid:
                continue
            rules[str(uuid)] = dict(row)
        _LOGGER.debug("[_get_shaper_rules] rules length: %s", len(rules))
        return rules

    @_log_errors
    async def get_shaper_pipe(self, uuid: str) -> dict[str, Any]:
        """Retrieve the full configuration of a single traffic shaper pipe.

        Args:
            uuid (str): Unique identifier of the target pipe.

        Returns:
            dict[str, Any]: Pipe configuration fields, or an empty dict on failure.
        """
        response = await self._safe_dict_get(f"/api/trafficshaper/settings/get_pipe/{uuid}")
        return dict(response.get("pipe", {}))

    async def set_pipe_bandwidth(
        self,
        uuid: str,
        bandwidth: int | float,
        bandwidthtype: str = "Mbit",
    ) -> bool:
        """Set the bandwidth of a traffic shaper pipe.

        Fetches the current pipe configuration, updates the bandwidth fields, then
        saves and applies the change.

        Args:
            uuid (str): Unique identifier of the target pipe.
            bandwidth (int | float): New bandwidth value.
            bandwidthtype (str): Bandwidth unit — one of ``bit``, ``Kbit``, ``Mbit``, ``Gbit``.
                Defaults to ``Mbit``.

        Returns:
            bool: True when the update and reconfigure complete successfully; otherwise, False.
        """
        pipe = await self.get_shaper_pipe(uuid)
        if not pipe:
            _LOGGER.debug("[set_pipe_bandwidth] uuid %s not found or empty", uuid)
            return False
        pipe["bandwidth"] = str(bandwidth)
        pipe["bandwidthtype"] = bandwidthtype
        response = await self._safe_dict_post(
            f"/api/trafficshaper/settings/set_pipe/{uuid}",
            payload={"pipe": pipe},
        )
        _LOGGER.debug(
            "[set_pipe_bandwidth] uuid: %s, bandwidth: %s %s, response: %s",
            uuid,
            bandwidth,
            bandwidthtype,
            response,
        )
        if response.get("result") == "failed":
            return False
        return await self._apply_shaper()

    async def toggle_shaper_pipe(self, uuid: str, toggle_on_off: str | None = None) -> bool:
        """Toggle a traffic shaper pipe on or off.

        Args:
            uuid (str): Unique identifier of the target pipe.
            toggle_on_off (str | None, optional): Target enabled state for the selected item.

        Returns:
            bool: True when the toggle operation completes successfully; otherwise, False.
        """
        url = f"/api/trafficshaper/settings/toggle_pipe/{uuid}"
        if toggle_on_off == "on":
            url = f"{url}/1"
        elif toggle_on_off == "off":
            url = f"{url}/0"
        response = await self._safe_dict_post(url, payload={})
        _LOGGER.debug(
            "[toggle_shaper_pipe] uuid: %s, action: %s, response: %s",
            uuid,
            toggle_on_off,
            response,
        )
        if response.get("result") == "failed":
            return False
        return await self._apply_shaper()

    async def toggle_shaper_queue(self, uuid: str, toggle_on_off: str | None = None) -> bool:
        """Toggle a traffic shaper queue on or off.

        Args:
            uuid (str): Unique identifier of the target queue.
            toggle_on_off (str | None, optional): Target enabled state for the selected item.

        Returns:
            bool: True when the toggle operation completes successfully; otherwise, False.
        """
        url = f"/api/trafficshaper/settings/toggle_queue/{uuid}"
        if toggle_on_off == "on":
            url = f"{url}/1"
        elif toggle_on_off == "off":
            url = f"{url}/0"
        response = await self._safe_dict_post(url, payload={})
        _LOGGER.debug(
            "[toggle_shaper_queue] uuid: %s, action: %s, response: %s",
            uuid,
            toggle_on_off,
            response,
        )
        if response.get("result") == "failed":
            return False
        return await self._apply_shaper()

    async def toggle_shaper_rule(self, uuid: str, toggle_on_off: str | None = None) -> bool:
        """Toggle a traffic shaper rule on or off.

        Args:
            uuid (str): Unique identifier of the target rule.
            toggle_on_off (str | None, optional): Target enabled state for the selected item.

        Returns:
            bool: True when the toggle operation completes successfully; otherwise, False.
        """
        url = f"/api/trafficshaper/settings/toggle_rule/{uuid}"
        if toggle_on_off == "on":
            url = f"{url}/1"
        elif toggle_on_off == "off":
            url = f"{url}/0"
        response = await self._safe_dict_post(url, payload={})
        _LOGGER.debug(
            "[toggle_shaper_rule] uuid: %s, action: %s, response: %s",
            uuid,
            toggle_on_off,
            response,
        )
        if response.get("result") == "failed":
            return False
        return await self._apply_shaper()

    async def _apply_shaper(self) -> bool:
        """Apply pending traffic shaper configuration changes.

        Returns:
            bool: True when the reconfigure operation completes successfully; otherwise, False.
        """
        apply_resp = await self._safe_dict_post("/api/trafficshaper/service/reconfigure")
        if apply_resp.get("status", "").strip() != "ok":
            return False
        return True
