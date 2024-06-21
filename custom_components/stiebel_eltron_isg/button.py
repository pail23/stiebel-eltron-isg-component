"""Button platform for stiebel_eltron_isg."""

import logging

from collections.abc import Callable, Coroutine
from dataclasses import dataclass


from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, RESET_HEATPUMP
from .entity import StiebelEltronISGEntity
from .coordinator import StiebelEltronModbusDataCoordinator

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .data import StiebelEltronISGIntegrationConfigEntry


_LOGGER = logging.getLogger(__name__)


@dataclass
class StiebelEltronISGButtonDescriptionMixin:
    """Mixin to describe aStiebel Eltron ISG button."""

    press_action: Callable[[StiebelEltronModbusDataCoordinator], Coroutine]


@dataclass
class StiebelEltronISGButtonDescription(
    ButtonEntityDescription, StiebelEltronISGButtonDescriptionMixin
):
    """Stiebel Eltron ISG button description."""


BUTTONS = [
    StiebelEltronISGButtonDescription(
        key=RESET_HEATPUMP,
        name="Reset Heatpump",
        entity_category=EntityCategory.DIAGNOSTIC,
        press_action=lambda coordinator: coordinator.async_reset_heatpump(),
    )
]


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: StiebelEltronISGIntegrationConfigEntry,
    async_add_devices: AddEntitiesCallback,
):
    """Set up the select platform."""
    coordinator = entry.runtime_data.coordinator

    if coordinator.is_wpm:
        async_add_devices(
            StiebelEltronISGButtonEntity(coordinator, entry, description)
            for description in BUTTONS
        )


class StiebelEltronISGButtonEntity(StiebelEltronISGEntity, ButtonEntity):
    """stiebel_eltron_isg button class."""

    def __init__(self, coordinator, config_entry, description):
        """Initialize the button."""
        self.entity_description = description
        super().__init__(coordinator, config_entry)

    @property
    def unique_id(self) -> str | None:
        """Return the unique id of the button entity."""
        return f"{DOMAIN}_{self.coordinator.name}_{self.entity_description.key}"

    async def async_press(self) -> None:
        """Trigger the button action."""
        await self.entity_description.press_action(self.coordinator)
