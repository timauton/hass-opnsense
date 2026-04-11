"""OPNsense number entities (e.g. traffic shaper pipe bandwidth)."""

from collections.abc import Mapping, MutableMapping
import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_SYNC_TRAFFIC_SHAPER,
    COORDINATOR,
    DEFAULT_SYNC_OPTION_VALUE,
)
from .coordinator import OPNsenseDataUpdateCoordinator
from .entity import OPNsenseEntity

_LOGGER: logging.Logger = logging.getLogger(__name__)

_BANDWIDTHTYPE_UNITS: dict[str, str] = {
    "bit": "bit/s",
    "Kbit": "Kbit/s",
    "Mbit": "Mbit/s",
    "Gbit": "Gbit/s",
}


async def _compile_shaper_pipe_bandwidth_numbers(
    config_entry: ConfigEntry,
    coordinator: OPNsenseDataUpdateCoordinator,
    state: MutableMapping[str, Any],
) -> list:
    """Compile bandwidth number entities for all traffic shaper pipes.

    Args:
        config_entry: The Home Assistant config entry.
        coordinator: The data update coordinator.
        state: The current state data from OPNsense.

    Returns:
        list: A list of OPNsenseShaperPipeBandwidth entities.
    """
    if not isinstance(state, MutableMapping):
        return []
    shaper = state.get("traffic_shaper", {})
    if not isinstance(shaper, MutableMapping):
        return []
    entities: list = []
    for uuid, pipe in shaper.get("pipes", {}).items():
        if not isinstance(pipe, MutableMapping):
            continue
        description = pipe.get("description", uuid)
        bandwidthtype = pipe.get("bandwidthMetric", pipe.get("bandwidthtype", "Mbit"))
        unit = _BANDWIDTHTYPE_UNITS.get(bandwidthtype, f"{bandwidthtype}/s")
        entities.append(
            OPNsenseShaperPipeBandwidth(
                config_entry=config_entry,
                coordinator=coordinator,
                entity_description=NumberEntityDescription(
                    key=f"trafficshaper.pipe.{uuid}.bandwidth",
                    name=f"Shaper Pipe {description} Bandwidth",
                    icon="mdi:speedometer",
                    native_unit_of_measurement=unit,
                    entity_registry_enabled_default=True,
                ),
            )
        )
    _LOGGER.debug("[compile_shaper_pipe_bandwidth_numbers] entities: %s", len(entities))
    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up OPNsense number entities.

    Args:
        hass: The Home Assistant instance.
        config_entry: The config entry for this integration.
        async_add_entities: Callback to add entities to Home Assistant.
    """
    coordinator: OPNsenseDataUpdateCoordinator = getattr(config_entry.runtime_data, COORDINATOR)
    state: dict[str, Any] = coordinator.data
    if not isinstance(state, MutableMapping):
        _LOGGER.error("Missing state data in number async_setup_entry")
        return
    config: Mapping[str, Any] = config_entry.data

    entities: list = []

    if config.get(CONF_SYNC_TRAFFIC_SHAPER, DEFAULT_SYNC_OPTION_VALUE):
        entities.extend(
            await _compile_shaper_pipe_bandwidth_numbers(config_entry, coordinator, state)
        )

    _LOGGER.debug("[number async_setup_entry] entities: %s", len(entities))
    async_add_entities(entities)


class OPNsenseShaperPipeBandwidth(OPNsenseEntity, NumberEntity):
    """Number entity for controlling a traffic shaper pipe's bandwidth."""

    def __init__(
        self,
        config_entry: ConfigEntry,
        coordinator: OPNsenseDataUpdateCoordinator,
        entity_description: NumberEntityDescription,
    ) -> None:
        """Initialise the bandwidth number entity.

        Args:
            config_entry: The Home Assistant config entry.
            coordinator: The data update coordinator.
            entity_description: The entity description. Key: ``trafficshaper.pipe.<uuid>.bandwidth``.
        """
        name_suffix: str | None = (
            entity_description.name if isinstance(entity_description.name, str) else None
        )
        unique_id_suffix: str | None = (
            entity_description.key if isinstance(entity_description.key, str) else None
        )
        super().__init__(
            config_entry,
            coordinator,
            unique_id_suffix=unique_id_suffix,
            name_suffix=name_suffix,
        )
        self.entity_description = entity_description
        parts = entity_description.key.split(".")
        self._uuid: str = parts[2]
        self._attr_mode = NumberMode.BOX
        self._attr_native_min_value: float = 0
        self._attr_native_max_value: float = 100_000
        self._attr_native_step: float = 1
        self._attr_native_value: float | None = None

    def _opnsense_get_pipe(self) -> MutableMapping[str, Any] | None:
        """Return pipe data from coordinator state."""
        state: dict[str, Any] = self.coordinator.data
        if not isinstance(state, MutableMapping):
            return None
        return state.get("traffic_shaper", {}).get("pipes", {}).get(self._uuid)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Refresh entity state from coordinator data."""
        pipe = self._opnsense_get_pipe()
        if not isinstance(pipe, MutableMapping):
            self._available = False
            self.async_write_ha_state()
            return
        try:
            self._attr_native_value = float(pipe.get("bandwidth", 0))
        except (TypeError, ValueError):
            self._available = False
            self.async_write_ha_state()
            return
        self._available = True
        self._attr_extra_state_attributes = {
            "uuid": self._uuid,
            "bandwidthtype": pipe.get("bandwidthtype", ""),
            "description": pipe.get("description", ""),
        }
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Set a new bandwidth value on the pipe.

        Args:
            value: New bandwidth in the entity's native unit.
        """
        if not self._client:
            return
        pipe = self._opnsense_get_pipe()
        bandwidthtype = pipe.get("bandwidthMetric", pipe.get("bandwidthtype", "Mbit")) if isinstance(pipe, MutableMapping) else "Mbit"
        result = await self._client.set_pipe_bandwidth(self._uuid, value, bandwidthtype)
        if result:
            _LOGGER.info("Set bandwidth of pipe %s to %s %s", self._uuid, value, bandwidthtype)
            self._attr_native_value = value
            self.async_write_ha_state()
        else:
            _LOGGER.error("Failed to set bandwidth of pipe %s", self._uuid)
