"""
Custom integration to integrate stiebel_eltron_isg with Home Assistant.

For more details about this integration, please refer to
https://github.com/pail23/stiebel_eltron_isg
"""
import asyncio
from datetime import timedelta
import logging
import threading
from typing import Dict


import voluptuous as vol
from pymodbus.client import ModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    VERSION,
    PLATFORMS,
    STARTUP_MESSAGE,
    ACTUAL_TEMPERATURE,
    TARGET_TEMPERATURE,
    ACTUAL_TEMPERATURE_FEK,
    TARGET_TEMPERATURE_FEK,
    ACTUAL_HUMIDITY,
    DEWPOINT_TEMPERATURE,
    OUTDOOR_TEMPERATURE,
    ACTUAL_TEMPERATURE_HK1,
    TARGET_TEMPERATURE_HK1,
    ACTUAL_TEMPERATURE_HK2,
    TARGET_TEMPERATURE_HK2,
    ACTUAL_TEMPERATURE_BUFFER,
    TARGET_TEMPERATURE_BUFFER,
    ACTUAL_TEMPERATURE_WATER,
    TARGET_TEMPERATURE_WATER,
    HEATER_PRESSURE,
    VOLUME_STREAM,
    SOURCE_TEMPERATURE,
    PRODUCED_HEATING_TODAY,
    PRODUCED_HEATING_TOTAL,
    PRODUCED_WATER_HEATING_TODAY,
    PRODUCED_WATER_HEATING_TOTAL,
    CONSUMED_HEATING_TODAY,
    CONSUMED_HEATING_TOTAL,
    CONSUMED_WATER_HEATING_TODAY,
    CONSUMED_WATER_HEATING_TOTAL,
    CONSUMED_POWER,
    HEATPUMPT_AVERAGE_POWER,
    IS_HEATING,
    IS_HEATING_WATER,
    IS_SUMMER_MODE,
    IS_COOLING,
    SG_READY_STATE,
    SG_READY_ACTIVE,
    SG_READY_INPUT_1,
    SG_READY_INPUT_2,
    OPERATION_MODE,
)

SCAN_INTERVAL = timedelta(seconds=30)

_LOGGER: logging.Logger = logging.getLogger(__package__)


STIEBEL_ELTRON_ISG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.string,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): cv.positive_int,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({cv.slug: STIEBEL_ELTRON_ISG_SCHEMA})}, extra=vol.ALLOW_EXTRA
)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    name = entry.data.get(CONF_NAME)
    host = entry.data.get(CONF_HOST)
    port = entry.data.get(CONF_PORT)
    scan_interval = entry.data[CONF_SCAN_INTERVAL]

    coordinator = StiebelEltronModbusDataCoordinator(
        hass, name, host, port, scan_interval
    )
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


def get_isg_scaled_value(value) -> float:
    return value * 0.1 if value != -32768 else None


class StiebelEltronModbusDataCoordinator(DataUpdateCoordinator):
    """Thread safe wrapper class for pymodbus."""

    def __init__(
        self,
        hass,
        name,
        host,
        port,
        scan_interval,
    ):
        """Initialize the Modbus hub."""
        self._hass = hass
        self._host = host
        self._model = VERSION
        self._client = ModbusTcpClient(host=host, port=port)
        self._lock = threading.Lock()
        self._scan_interval = timedelta(seconds=scan_interval)
        self.platforms = []

        super().__init__(hass, _LOGGER, name=name, update_interval=self._scan_interval)

    def close(self):
        """Disconnect client."""
        with self._lock:
            self._client.close()

    def connect(self):
        """Connect client."""
        with self._lock:
            self._client.connect()

    @property
    def host(self) -> str:
        """return the host address of the Stiebel Eltron ISG"""
        return self._host

    @property
    def model(self) -> str:
        """return the host address of the Stiebel Eltron ISG"""
        return self._model

    def read_input_registers(self, slave, address, count):
        """Read input registers."""
        with self._lock:
            return self._client.read_input_registers(address, count, slave)

    def read_holding_registers(self, slave, address, count):
        """Read holding registers."""
        with self._lock:
            return self._client.read_holding_registers(address, count, slave)

    def write_register(self, address, value, slave):
        """Write holding register."""
        with self._lock:
            return self._client.write_registers(address, value, slave)

    async def _async_update_data(self) -> Dict:
        """Time to update."""
        try:
            return self.read_modbus_data()
        except Exception as exception:
            raise UpdateFailed() from exception

    def read_modbus_data(self) -> Dict:
        """Read the ISG data through modbus."""
        result = {
            **self.read_modbus_energy(),
            **self.read_modbus_system_state(),
            **self.read_modbus_system_values(),
            **self.read_modbus_system_paramter(),
            **self.read_modbus_sg_ready(),
        }
        return result

    def read_modbus_system_state(self) -> Dict:
        """Read the system state values from the ISG."""
        result = {}
        inverter_data = self.read_input_registers(slave=1, address=2500, count=1)
        if not inverter_data.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                inverter_data.registers, byteorder=Endian.Big
            )
            state = decoder.decode_16bit_uint()
            is_heating = (state & (1 << 4)) != 0
            result[IS_HEATING] = is_heating
            is_heating_water = (state & (1 << 5)) != 0
            result[IS_HEATING_WATER] = is_heating_water
            result[CONSUMED_POWER] = (
                HEATPUMPT_AVERAGE_POWER if is_heating_water or is_heating else 0.0
            )

            result[IS_SUMMER_MODE] = (state & (1 << 7)) != 0
            result[IS_COOLING] = (state & (1 << 8)) != 0

        return result

    def read_modbus_system_values(self) -> Dict:
        """Read the system related values from the ISG."""
        result = {}
        inverter_data = self.read_input_registers(slave=1, address=500, count=40)
        if not inverter_data.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                inverter_data.registers, byteorder=Endian.Big
            )
            result[ACTUAL_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
            result[TARGET_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
            result[ACTUAL_TEMPERATURE_FEK] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
            result[TARGET_TEMPERATURE_FEK] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
            result[ACTUAL_HUMIDITY] = get_isg_scaled_value(decoder.decode_16bit_int())
            result[DEWPOINT_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
            result[OUTDOOR_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
            result[ACTUAL_TEMPERATURE_HK1] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
            hk1_target = get_isg_scaled_value(decoder.decode_16bit_int())
            result[TARGET_TEMPERATURE_HK1] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
            result[ACTUAL_TEMPERATURE_HK2] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
            result[TARGET_TEMPERATURE_HK2] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
            decoder.skip_bytes(10)
            result[ACTUAL_TEMPERATURE_BUFFER] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
            result[TARGET_TEMPERATURE_BUFFER] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
            result[HEATER_PRESSURE] = (
                get_isg_scaled_value(decoder.decode_16bit_int()) / 10
            )
            result[VOLUME_STREAM] = (
                get_isg_scaled_value(decoder.decode_16bit_int()) / 10
            )
            result[ACTUAL_TEMPERATURE_WATER] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
            result[TARGET_TEMPERATURE_WATER] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
            decoder.skip_bytes(24)
            result[SOURCE_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int()
            )
        return result

    def read_modbus_system_paramter(self) -> Dict:
        """Read the system paramters from the ISG."""
        result = {}
        inverter_data = self.read_holding_registers(slave=1, address=1500, count=19)
        if not inverter_data.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                inverter_data.registers, byteorder=Endian.Big
            )
            result[OPERATION_MODE] = decoder.decode_16bit_uint()
        return result

    def read_modbus_energy(self) -> Dict:
        """Read the energy consumption related values from the ISG."""
        result = {}
        inverter_data = self.read_input_registers(slave=1, address=3500, count=22)
        if not inverter_data.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                inverter_data.registers, byteorder=Endian.Big
            )
            produced_heating_today = decoder.decode_16bit_uint()
            produced_heating_total_low = decoder.decode_16bit_uint()
            produced_heating_total_high = decoder.decode_16bit_uint()
            produced_water_today = decoder.decode_16bit_uint()
            produced_water_total_low = decoder.decode_16bit_uint()
            produced_water_total_high = decoder.decode_16bit_uint()
            decoder.skip_bytes(8)  # Skip NHZ
            consumed_heating_today = decoder.decode_16bit_uint()
            consumed_heating_total_low = decoder.decode_16bit_uint()
            consumed_heating_total_high = decoder.decode_16bit_uint()
            consumed_water_today = decoder.decode_16bit_uint()
            consumed_water_total_low = decoder.decode_16bit_uint()
            consumed_water_total_high = decoder.decode_16bit_uint()

            result[PRODUCED_HEATING_TODAY] = produced_heating_today
            result[PRODUCED_HEATING_TOTAL] = (
                produced_heating_total_high * 1000 + produced_heating_total_low
            )
            result[PRODUCED_WATER_HEATING_TODAY] = produced_water_today
            result[PRODUCED_WATER_HEATING_TOTAL] = (
                produced_water_total_high * 1000 + produced_water_total_low
            )
            result[CONSUMED_HEATING_TODAY] = consumed_heating_today
            result[CONSUMED_HEATING_TOTAL] = (
                consumed_heating_total_high * 1000 + consumed_heating_total_low
            )
            result[CONSUMED_WATER_HEATING_TODAY] = consumed_water_today
            result[CONSUMED_WATER_HEATING_TOTAL] = (
                consumed_water_total_high * 1000 + consumed_water_total_low
            )
        return result

    def read_modbus_sg_ready(self) -> Dict:
        """Read the sg ready related values from the ISG."""
        result = {}
        inverter_data = self.read_input_registers(slave=1, address=5000, count=2)
        if not inverter_data.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                inverter_data.registers, byteorder=Endian.Big
            )
            result[SG_READY_STATE] = decoder.decode_16bit_uint()
            model = decoder.decode_16bit_uint()
            if model == 390:
                self._model = "WPM 3"
            elif model == 391:
                self._model = "WPM 3i"
            elif model == 449:
                self._model = "WPMsystem"
            else:
                self._model = "other model"
        inverter_data = self.read_holding_registers(slave=1, address=4000, count=3)
        if not inverter_data.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                inverter_data.registers, byteorder=Endian.Big
            )
            result[SG_READY_ACTIVE] = decoder.decode_16bit_uint()
            result[SG_READY_INPUT_1] = decoder.decode_16bit_uint()
            result[SG_READY_INPUT_2] = decoder.decode_16bit_uint()
        return result

    def set_data(self, key, value) -> None:
        """Write the data to the modbus"""
        if key == SG_READY_ACTIVE:
            self.write_register(address=4000, value=value, slave=1)
        elif key == SG_READY_INPUT_1:
            self.write_register(address=4001, value=value, slave=1)
        elif key == SG_READY_INPUT_2:
            self.write_register(address=4002, value=value, slave=1)
        elif key == OPERATION_MODE:
            self.write_register(address=1500, value=value, slave=1)
        else:
            return
        self.data[key] = value


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
