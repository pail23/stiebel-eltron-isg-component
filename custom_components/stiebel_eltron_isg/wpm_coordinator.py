"""Data Coordinator for the WPM Stiebel Eltron heat pumps.

For more details about this integration, please refer to
https://github.com/pail23/stiebel_eltron_isg
"""

import logging

from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

from custom_components.stiebel_eltron_isg.coordinator import (
    StiebelEltronModbusDataCoordinator,
    get_isg_scaled_value,
)

from .const import (
    ACTIVE_ERROR,
    ACTUAL_HUMIDITY,
    ACTUAL_HUMIDITY_HK1,
    ACTUAL_HUMIDITY_HK2,
    ACTUAL_HUMIDITY_HK3,
    ACTUAL_ROOM_TEMPERATURE_HK1,
    ACTUAL_ROOM_TEMPERATURE_HK2,
    ACTUAL_ROOM_TEMPERATURE_HK3,
    ACTUAL_TEMPERATURE,
    ACTUAL_TEMPERATURE_BUFFER,
    ACTUAL_TEMPERATURE_COOLING_FANCOIL,
    ACTUAL_TEMPERATURE_COOLING_SURFACE,
    ACTUAL_TEMPERATURE_FEK,
    ACTUAL_TEMPERATURE_HK1,
    ACTUAL_TEMPERATURE_HK2,
    ACTUAL_TEMPERATURE_HK3,
    ACTUAL_TEMPERATURE_WATER,
    AREA_COOLING_TARGET_FLOW_TEMPERATURE,
    AREA_COOLING_TARGET_ROOM_TEMPERATURE,
    BUFFER_1_CHARGING_PUMP,
    BUFFER_2_CHARGING_PUMP,
    BUFFER_3_CHARGING_PUMP,
    BUFFER_4_CHARGING_PUMP,
    BUFFER_5_CHARGING_PUMP,
    BUFFER_6_CHARGING_PUMP,
    CIRCULATION_PUMP,
    COMFORT_TEMPERATURE_TARGET_HK1,
    COMFORT_TEMPERATURE_TARGET_HK2,
    COMFORT_TEMPERATURE_TARGET_HK3,
    COMFORT_WATER_TEMPERATURE_TARGET,
    COMPRESSOR_ON,
    CONSUMED_HEATING,
    CONSUMED_HEATING_TODAY,
    CONSUMED_HEATING_TOTAL,
    CONSUMED_WATER_HEATING,
    CONSUMED_WATER_HEATING_TODAY,
    CONSUMED_WATER_HEATING_TOTAL,
    COOLING_MODE,
    DEWPOINT_TEMPERATURE,
    DEWPOINT_TEMPERATURE_HK1,
    DEWPOINT_TEMPERATURE_HK2,
    DEWPOINT_TEMPERATURE_HK3,
    DHW_CHARGING_PUMP,
    DIFF_CONTROLLER_1_PUMP,
    DIFF_CONTROLLER_2_PUMP,
    DUALMODE_TEMPERATURE_HZG,
    DUALMODE_TEMPERATURE_WW,
    ECO_TEMPERATURE_TARGET_HK1,
    ECO_TEMPERATURE_TARGET_HK2,
    ECO_TEMPERATURE_TARGET_HK3,
    ECO_WATER_TEMPERATURE_TARGET,
    EMERGENCY_HEATING_1,
    EMERGENCY_HEATING_1_2,
    EMERGENCY_HEATING_2,
    ERROR_STATUS,
    EVAPORATOR_DEFROST,
    FAN_COOLING_TARGET_FLOW_TEMPERATURE,
    FAN_COOLING_TARGET_ROOM_TEMPERATURE,
    FLOW_TEMPERATURE,
    FLOW_TEMPERATURE_NHZ,
    FLOW_TEMPERATURE_WP1,
    FLOW_TEMPERATURE_WP2,
    HEAT_PUMP_1_ON,
    HEAT_PUMP_2_ON,
    HEAT_PUMP_3_ON,
    HEAT_PUMP_4_ON,
    HEAT_PUMP_5_ON,
    HEAT_PUMP_6_ON,
    HEAT_UP_PROGRAM,
    HEATER_PRESSURE,
    HEATING_CIRCUIT_1_PUMP,
    HEATING_CIRCUIT_2_PUMP,
    HEATING_CIRCUIT_3_PUMP,
    HEATING_CIRCUIT_4_PUMP,
    HEATING_CIRCUIT_5_PUMP,
    HEATING_CURVE_RISE_HK1,
    HEATING_CURVE_RISE_HK2,
    HEATING_CURVE_RISE_HK3,
    HIGH_PRESSURE,
    HIGH_PRESSURE_WP1,
    HIGH_PRESSURE_WP2,
    HOT_GAS_TEMPERATURE,
    HOT_GAS_TEMPERATURE_WP1,
    HOT_GAS_TEMPERATURE_WP2,
    IS_COOLING,
    IS_HEATING,
    IS_HEATING_WATER,
    IS_SUMMER_MODE,
    LOW_PRESSURE,
    LOW_PRESSURE_WP1,
    LOW_PRESSURE_WP2,
    MIXER_CLOSE_HTG_CIRCUIT_2,
    MIXER_CLOSE_HTG_CIRCUIT_3,
    MIXER_CLOSE_HTG_CIRCUIT_4,
    MIXER_CLOSE_HTG_CIRCUIT_5,
    MIXER_OPEN_HTG_CIRCUIT_2,
    MIXER_OPEN_HTG_CIRCUIT_3,
    MIXER_OPEN_HTG_CIRCUIT_4,
    MIXER_OPEN_HTG_CIRCUIT_5,
    NHZ_STAGES_RUNNING,
    OPERATION_MODE,
    OUTDOOR_TEMPERATURE,
    POOL_PRIMARY_PUMP,
    POOL_SECONDARY_PUMP,
    PREVIOUS_CONSUMED_HEATING_TOTAL,
    PREVIOUS_CONSUMED_WATER_HEATING_TOTAL,
    PREVIOUS_PRODUCED_HEATING_TOTAL,
    PREVIOUS_PRODUCED_WATER_HEATING_TOTAL,
    PRODUCED_HEATING,
    PRODUCED_HEATING_TODAY,
    PRODUCED_HEATING_TOTAL,
    PRODUCED_WATER_HEATING,
    PRODUCED_WATER_HEATING_TODAY,
    PRODUCED_WATER_HEATING_TOTAL,
    PUMP_ON_HK1,
    PUMP_ON_HK2,
    RETURN_TEMPERATURE,
    RETURN_TEMPERATURE_WP1,
    RETURN_TEMPERATURE_WP2,
    SECOND_GENERATOR_DHW,
    SECOND_GENERATOR_HEATING,
    SG_READY_ACTIVE,
    SG_READY_INPUT_1,
    SG_READY_INPUT_2,
    SOURCE_PRESSURE,
    SOURCE_PUMP,
    SOURCE_TEMPERATURE,
    TARGET_ROOM_TEMPERATURE_HK1,
    TARGET_ROOM_TEMPERATURE_HK2,
    TARGET_ROOM_TEMPERATURE_HK3,
    TARGET_TEMPERATURE,
    TARGET_TEMPERATURE_BUFFER,
    TARGET_TEMPERATURE_COOLING_FANCOIL,
    TARGET_TEMPERATURE_COOLING_SURFACE,
    TARGET_TEMPERATURE_FEK,
    TARGET_TEMPERATURE_HK1,
    TARGET_TEMPERATURE_HK2,
    TARGET_TEMPERATURE_HK3,
    TARGET_TEMPERATURE_WATER,
    VOLUME_STREAM,
    VOLUME_STREAM_WP1,
    VOLUME_STREAM_WP2,
    EVU,
)

_LOGGER: logging.Logger = logging.getLogger(__package__)


class StiebelEltronModbusWPMDataCoordinator(StiebelEltronModbusDataCoordinator):
    """Communicates with WPM Controllers."""

    async def read_modbus_data(self) -> dict:
        """Read the ISG data through modbus."""
        return {
            **await self.read_modbus_energy(),
            **await self.read_modbus_system_state(),
            **await self.read_modbus_system_values(),
            **await self.read_modbus_system_paramter(),
            **await self.read_modbus_sg_ready(),
        }

    async def read_modbus_system_state(self) -> dict:  # noqa: C901
        """Read the system state values from the ISG."""
        result = {}
        inverter_data = await self.read_input_registers(slave=1, address=2500, count=47)
        if not inverter_data.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                inverter_data.registers,
                byteorder=Endian.BIG,
            )
            state = decoder.decode_16bit_uint()
            result[PUMP_ON_HK1] = (state & (1 << 0)) != 0
            result[PUMP_ON_HK2] = (state & (1 << 1)) != 0
            result[HEAT_UP_PROGRAM] = (state & (1 << 2)) != 0
            result[NHZ_STAGES_RUNNING] = (state & (1 << 3)) != 0
            result[IS_HEATING] = (state & (1 << 4)) != 0
            result[IS_HEATING_WATER] = (state & (1 << 5)) != 0
            result[COMPRESSOR_ON] = (state & (1 << 6)) != 0
            result[IS_SUMMER_MODE] = (state & (1 << 7)) != 0
            result[IS_COOLING] = (state & (1 << 8)) != 0
            result[EVAPORATOR_DEFROST] = (state & (1 << 9)) != 0
            
            # 2502
            state = decoder.decode_16bit_uint()
            result[EVU] =  (state & (1 << 0)) != 0
            
            # 2503
            decoder.skip_bytes(2)
            
            # 2504
            result[ERROR_STATUS] = decoder.decode_16bit_uint()
            decoder.skip_bytes(4)
            # 2507
            error = decoder.decode_16bit_uint()
            if error == 32768:
                result[ACTIVE_ERROR] = "no error"
            else:
                result[ACTIVE_ERROR] = f"error {error}"
            # 2508
            decoder.skip_bytes(2)
            # 2509
            heating_circuit_1_pump = decoder.decode_16bit_uint()
            if heating_circuit_1_pump != 32768:
                result[HEATING_CIRCUIT_1_PUMP] = heating_circuit_1_pump
            # 2510
            heating_circuit_2_pump = decoder.decode_16bit_uint()
            if heating_circuit_2_pump != 32768:
                result[HEATING_CIRCUIT_2_PUMP] = heating_circuit_2_pump
            # 2511
            heating_circuit_3_pump = decoder.decode_16bit_uint()
            if heating_circuit_3_pump != 32768:
                result[HEATING_CIRCUIT_3_PUMP] = heating_circuit_3_pump
            # 2512
            buffer_1_charging_pump = decoder.decode_16bit_uint()
            if buffer_1_charging_pump != 32768:
                result[BUFFER_1_CHARGING_PUMP] = buffer_1_charging_pump
            # 2513
            buffer_2_charging_pump = decoder.decode_16bit_uint()
            if buffer_2_charging_pump != 32768:
                result[BUFFER_2_CHARGING_PUMP] = buffer_2_charging_pump
            # 2514
            dhw_charging_pump = decoder.decode_16bit_uint()
            if dhw_charging_pump != 32768:
                result[DHW_CHARGING_PUMP] = dhw_charging_pump
            # 2515
            source_pump = decoder.decode_16bit_uint()
            if source_pump != 32768:
                result[SOURCE_PUMP] = source_pump
            # 2516
            decoder.skip_bytes(2)
            # 2517
            circulation_pump = decoder.decode_16bit_uint()
            if circulation_pump != 32768:
                result[CIRCULATION_PUMP] = circulation_pump
            # 2518
            second_generator_dhw = decoder.decode_16bit_uint()
            if second_generator_dhw != 32768:
                result[SECOND_GENERATOR_DHW] = second_generator_dhw
            # 2519
            second_generator_heating = decoder.decode_16bit_uint()
            if second_generator_heating != 32768:
                result[SECOND_GENERATOR_HEATING] = second_generator_heating
            # 2520
            cooling_mode = decoder.decode_16bit_uint()
            if cooling_mode != 32768:
                result[COOLING_MODE] = cooling_mode
            # 2521
            mixer_open_htc_circuit_2 = decoder.decode_16bit_uint()
            if mixer_open_htc_circuit_2 != 32768:
                result[MIXER_OPEN_HTG_CIRCUIT_2] = mixer_open_htc_circuit_2
            # 2522
            mixer_close_htc_circuit_2 = decoder.decode_16bit_uint()
            if mixer_close_htc_circuit_2 != 32768:
                result[MIXER_CLOSE_HTG_CIRCUIT_2] = mixer_close_htc_circuit_2
            # 2523
            mixer_open_htc_circuit_3 = decoder.decode_16bit_uint()
            if mixer_open_htc_circuit_3 != 32768:
                result[MIXER_OPEN_HTG_CIRCUIT_3] = mixer_open_htc_circuit_3
            # 2524
            mixer_close_htc_circuit_3 = decoder.decode_16bit_uint()
            if mixer_close_htc_circuit_3 != 32768:
                result[MIXER_CLOSE_HTG_CIRCUIT_3] = mixer_close_htc_circuit_3

            # 2525
            emergency_heating_1 = decoder.decode_16bit_uint()
            if emergency_heating_1 != 32768:
                result[EMERGENCY_HEATING_1] = emergency_heating_1
            # 2526
            emergency_heating_2 = decoder.decode_16bit_uint()
            if emergency_heating_2 != 32768:
                result[EMERGENCY_HEATING_2] = emergency_heating_2
            # 2527
            emergency_heating_1_2 = decoder.decode_16bit_uint()
            if emergency_heating_1_2 != 32768:
                result[EMERGENCY_HEATING_1_2] = emergency_heating_1_2
            # 2528
            heating_circuit_4_pump = decoder.decode_16bit_uint()
            if heating_circuit_4_pump != 32768:
                result[HEATING_CIRCUIT_4_PUMP] = heating_circuit_4_pump
            # 2529
            heating_circuit_5_pump = decoder.decode_16bit_uint()
            if heating_circuit_5_pump != 32768:
                result[HEATING_CIRCUIT_5_PUMP] = heating_circuit_5_pump
            # 2530
            buffer_3_charging_pump = decoder.decode_16bit_uint()
            if buffer_3_charging_pump != 32768:
                result[BUFFER_3_CHARGING_PUMP] = buffer_3_charging_pump
            # 2531
            buffer_4_charging_pump = decoder.decode_16bit_uint()
            if buffer_4_charging_pump != 32768:
                result[BUFFER_4_CHARGING_PUMP] = buffer_4_charging_pump
            # 2532
            buffer_5_charging_pump = decoder.decode_16bit_uint()
            if buffer_5_charging_pump != 32768:
                result[BUFFER_5_CHARGING_PUMP] = buffer_5_charging_pump
            # 2533
            buffer_6_charging_pump = decoder.decode_16bit_uint()
            if buffer_6_charging_pump != 32768:
                result[BUFFER_6_CHARGING_PUMP] = buffer_6_charging_pump
            # 2534
            diff_controller_1_pump = decoder.decode_16bit_uint()
            if diff_controller_1_pump != 32768:
                result[DIFF_CONTROLLER_1_PUMP] = diff_controller_1_pump
            # 2535
            diff_controller_2_pump = decoder.decode_16bit_uint()
            if diff_controller_2_pump != 32768:
                result[DIFF_CONTROLLER_2_PUMP] = diff_controller_2_pump
            # 2536
            pool_primary_pump = decoder.decode_16bit_uint()
            if pool_primary_pump != 32768:
                result[POOL_PRIMARY_PUMP] = pool_primary_pump
            # 2537
            pool_secondary_pump = decoder.decode_16bit_uint()
            if pool_secondary_pump != 32768:
                result[POOL_SECONDARY_PUMP] = pool_secondary_pump
            # 2538
            mixer_open_htc_circuit_4 = decoder.decode_16bit_uint()
            if mixer_open_htc_circuit_4 != 32768:
                result[MIXER_OPEN_HTG_CIRCUIT_4] = mixer_open_htc_circuit_4
            # 2539
            mixer_close_htc_circuit_4 = decoder.decode_16bit_uint()
            if mixer_close_htc_circuit_4 != 32768:
                result[MIXER_CLOSE_HTG_CIRCUIT_4] = mixer_close_htc_circuit_4
            # 2540
            mixer_open_htc_circuit_5 = decoder.decode_16bit_uint()
            if mixer_open_htc_circuit_5 != 32768:
                result[MIXER_OPEN_HTG_CIRCUIT_5] = mixer_open_htc_circuit_5
            # 2541
            mixer_close_htc_circuit_5 = decoder.decode_16bit_uint()
            if mixer_close_htc_circuit_5 != 32768:
                result[MIXER_CLOSE_HTG_CIRCUIT_5] = mixer_close_htc_circuit_5
            # 2542
            heat_pump_1_on = decoder.decode_16bit_uint()
            if heat_pump_1_on != 32768:
                result[HEAT_PUMP_1_ON] = heat_pump_1_on
            # 2543
            heat_pump_2_on = decoder.decode_16bit_uint()
            if heat_pump_2_on != 32768:
                result[HEAT_PUMP_2_ON] = heat_pump_2_on
            # 2544
            heat_pump_3_on = decoder.decode_16bit_uint()
            if heat_pump_3_on != 32768:
                result[HEAT_PUMP_3_ON] = heat_pump_3_on
            # 2545
            heat_pump_4_on = decoder.decode_16bit_uint()
            if heat_pump_4_on != 32768:
                result[HEAT_PUMP_4_ON] = heat_pump_4_on
            # 2546
            heat_pump_5_on = decoder.decode_16bit_uint()
            if heat_pump_5_on != 32768:
                result[HEAT_PUMP_5_ON] = heat_pump_5_on
            # 2547
            heat_pump_6_on = decoder.decode_16bit_uint()
            if heat_pump_6_on != 32768:
                result[HEAT_PUMP_6_ON] = heat_pump_6_on

        return result

    async def read_modbus_system_values(self) -> dict:
        """Read the system related values from the ISG."""
        result: dict = {}
        inverter_data = await self.read_input_registers(slave=1, address=500, count=112)
        if not inverter_data.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                inverter_data.registers,
                byteorder=Endian.BIG,
            )
            # 501
            result[ACTUAL_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 502
            result[TARGET_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 503
            result[ACTUAL_TEMPERATURE_FEK] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 504
            result[TARGET_TEMPERATURE_FEK] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 505
            result[ACTUAL_HUMIDITY] = get_isg_scaled_value(decoder.decode_16bit_int())
            # 506
            result[DEWPOINT_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 507
            result[OUTDOOR_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 508
            result[ACTUAL_TEMPERATURE_HK1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 509
            # hk1_target = get_isg_scaled_value(decoder.decode_16bit_int())
            decoder.skip_bytes(2)
            # 510
            result[TARGET_TEMPERATURE_HK1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 511
            result[ACTUAL_TEMPERATURE_HK2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 512
            result[TARGET_TEMPERATURE_HK2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 513
            result[FLOW_TEMPERATURE] = get_isg_scaled_value(decoder.decode_16bit_int())
            # 514
            result[FLOW_TEMPERATURE_NHZ] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 515
            decoder.skip_bytes(2)
            # 516
            result[RETURN_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 517
            decoder.skip_bytes(2)
            # 518
            result[ACTUAL_TEMPERATURE_BUFFER] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 519
            result[TARGET_TEMPERATURE_BUFFER] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 520
            result[HEATER_PRESSURE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
                100,
            )
            # 521
            result[VOLUME_STREAM] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
                100,
            )
            # 522 domestic hot water
            result[ACTUAL_TEMPERATURE_WATER] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 523 domestic hot water
            result[TARGET_TEMPERATURE_WATER] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 524 Cooling Fancoil
            result[ACTUAL_TEMPERATURE_COOLING_FANCOIL] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 525 Cooling Fancoil
            result[TARGET_TEMPERATURE_COOLING_FANCOIL] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 526 Cooling Surface
            result[ACTUAL_TEMPERATURE_COOLING_SURFACE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 527 Cooling Surface
            result[TARGET_TEMPERATURE_COOLING_SURFACE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 528-535
            decoder.skip_bytes(16)
            # 536
            result[SOURCE_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 537
            decoder.skip_bytes(2)
            # 538
            result[SOURCE_PRESSURE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
                100,
            )
            # 539
            result[HOT_GAS_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 540
            result[HIGH_PRESSURE] = get_isg_scaled_value(decoder.decode_16bit_int())
            # 541
            result[LOW_PRESSURE] = get_isg_scaled_value(decoder.decode_16bit_int())
            # 542
            result[RETURN_TEMPERATURE_WP1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 543
            result[FLOW_TEMPERATURE_WP1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 544
            result[HOT_GAS_TEMPERATURE_WP1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 545
            result[LOW_PRESSURE_WP1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
                100,
            )
            # 546
            decoder.skip_bytes(2)
            # 547
            result[HIGH_PRESSURE_WP1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
                100,
            )
            # 548
            result[VOLUME_STREAM_WP1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
                10,
            )
            # 549
            result[RETURN_TEMPERATURE_WP2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 550
            result[FLOW_TEMPERATURE_WP2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 551
            result[HOT_GAS_TEMPERATURE_WP2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 552
            result[LOW_PRESSURE_WP2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
                100,
            )
            # 553
            decoder.skip_bytes(2)
            # 554
            result[HIGH_PRESSURE_WP2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
                100,
            )
            # 555
            result[VOLUME_STREAM_WP2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
                10,
            )
            # 546-583
            decoder.skip_bytes(56)
            # 584
            result[ACTUAL_ROOM_TEMPERATURE_HK1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 585
            result[TARGET_ROOM_TEMPERATURE_HK1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 586
            result[ACTUAL_HUMIDITY_HK1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 587
            result[DEWPOINT_TEMPERATURE_HK1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 588
            result[ACTUAL_ROOM_TEMPERATURE_HK2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 589
            result[TARGET_ROOM_TEMPERATURE_HK2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 590
            result[ACTUAL_HUMIDITY_HK2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 591
            result[DEWPOINT_TEMPERATURE_HK2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 592
            result[ACTUAL_ROOM_TEMPERATURE_HK3] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 593
            result[TARGET_ROOM_TEMPERATURE_HK3] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 594
            result[ACTUAL_HUMIDITY_HK3] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 595
            result[DEWPOINT_TEMPERATURE_HK3] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 596-599 TEMPERATURE_HK4
            # 600-603 TEMPERATURE_HK5
            # 604-608 COOLING CIRCUIT TEMPERATURE_HK1 to HK5
            decoder.skip_bytes(28)
            # 610
            result[ACTUAL_TEMPERATURE_HK3] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 611
            result[TARGET_TEMPERATURE_HK3] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            result["system_values"] = list(inverter_data.registers)
        return result

    async def read_modbus_system_paramter(self) -> dict:
        """Read the system paramters from the ISG."""
        result = {}
        inverter_data = await self.read_holding_registers(
            slave=1,
            address=1500,
            count=54,
        )
        if not inverter_data.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                inverter_data.registers,
                byteorder=Endian.BIG,
            )
            # 1501
            result[OPERATION_MODE] = decoder.decode_16bit_uint()
            # 1502
            result[COMFORT_TEMPERATURE_TARGET_HK1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 1503
            result[ECO_TEMPERATURE_TARGET_HK1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 1504
            result[HEATING_CURVE_RISE_HK1] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
                100,
            )
            # 1505
            result[COMFORT_TEMPERATURE_TARGET_HK2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 1506
            result[ECO_TEMPERATURE_TARGET_HK2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 1507
            result[HEATING_CURVE_RISE_HK2] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
                100,
            )
            # 1508
            decoder.skip_bytes(2)
            # 1509
            result[DUALMODE_TEMPERATURE_HZG] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
                10,
            )
            # 1510
            result[COMFORT_WATER_TEMPERATURE_TARGET] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 1511
            result[ECO_WATER_TEMPERATURE_TARGET] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 1512
            decoder.skip_bytes(2)
            # 1513
            result[DUALMODE_TEMPERATURE_WW] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
                10,
            )
            # 1514
            result[AREA_COOLING_TARGET_FLOW_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 1515
            decoder.skip_bytes(2)
            # 1516
            result[AREA_COOLING_TARGET_ROOM_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 1517
            result[FAN_COOLING_TARGET_FLOW_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 1518
            decoder.skip_bytes(2)
            # 1519
            result[FAN_COOLING_TARGET_ROOM_TEMPERATURE] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            decoder.skip_bytes(62)
            # 1550
            result[COMFORT_TEMPERATURE_TARGET_HK3] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 1551
            result[ECO_TEMPERATURE_TARGET_HK3] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
            )
            # 1552
            result[HEATING_CURVE_RISE_HK3] = get_isg_scaled_value(
                decoder.decode_16bit_int(),
                100,
            )
            result["system_paramaters"] = list(inverter_data.registers)
        return result

    async def read_modbus_energy(self) -> dict:
        """Read the energy consumption related values from the ISG."""
        result = {}
        inverter_data = await self.read_input_registers(
            slave=1,
            address=3500,
            count=22,
        )  # count=180
        _LOGGER.debug(f"Energy Data: {inverter_data.registers}")
        if not inverter_data.isError():
            decoder = BinaryPayloadDecoder.fromRegisters(
                inverter_data.registers,
                byteorder=Endian.BIG,
            )
            produced_heating_today = decoder.decode_16bit_uint()
            produced_heating_total_low = decoder.decode_16bit_uint()
            produced_heating_total_high = decoder.decode_16bit_uint()
            produced_heating_total = (
                produced_heating_total_high * 1000 + produced_heating_total_low
            )

            produced_water_today = decoder.decode_16bit_uint()
            produced_water_total_low = decoder.decode_16bit_uint()
            produced_water_total_high = decoder.decode_16bit_uint()
            produced_water_total = (
                produced_water_total_high * 1000 + produced_water_total_low
            )

            decoder.skip_bytes(8)  # Skip NHZ

            consumed_heating_today = decoder.decode_16bit_uint()
            consumed_heating_total_low = decoder.decode_16bit_uint()
            consumed_heating_total_high = decoder.decode_16bit_uint()
            consumed_heating_total = (
                consumed_heating_total_high * 1000 + consumed_heating_total_low
            )

            consumed_water_today = decoder.decode_16bit_uint()
            consumed_water_total_low = decoder.decode_16bit_uint()
            consumed_water_total_high = decoder.decode_16bit_uint()
            consumed_water_total = (
                consumed_water_total_high * 1000 + consumed_water_total_low
            )

            result[PRODUCED_HEATING_TODAY] = produced_heating_today
            result[PRODUCED_HEATING_TOTAL] = produced_heating_total
            # The following line should check if produced_heating_total before produced_heating_today resets to zero. This would cause a spike in the signal. The spike is removed by the following lines.
            if PREVIOUS_PRODUCED_HEATING_TOTAL in result:
                if (
                    produced_heating_total
                    == self.data.get(PREVIOUS_PRODUCED_HEATING_TOTAL)
                    or produced_heating_today < 2
                ):
                    result[PRODUCED_HEATING] = self.assign_if_increased(
                        produced_heating_total + produced_heating_today,
                        PRODUCED_HEATING,
                    )
            else:
                result[PREVIOUS_PRODUCED_HEATING_TOTAL] = produced_heating_total
                result[PRODUCED_HEATING] = (
                    produced_heating_total + produced_heating_today
                )

            result[PRODUCED_WATER_HEATING_TODAY] = produced_water_today
            result[PRODUCED_WATER_HEATING_TOTAL] = produced_water_total
            # The following line should check if produced_water_total before produced_water_today resets to zero. This would cause a spike in the signal. The spike is removed by the following lines.
            if PREVIOUS_PRODUCED_WATER_HEATING_TOTAL in result:
                if (
                    produced_water_total
                    == self.data.get(PREVIOUS_PRODUCED_WATER_HEATING_TOTAL)
                    or produced_water_today < 2
                ):
                    result[PRODUCED_WATER_HEATING] = self.assign_if_increased(
                        produced_water_total + produced_water_today,
                        PRODUCED_WATER_HEATING,
                    )
            else:
                result[PREVIOUS_PRODUCED_WATER_HEATING_TOTAL] = produced_water_total
                result[PRODUCED_WATER_HEATING] = (
                    produced_water_total + produced_water_today
                )

            result[CONSUMED_HEATING_TODAY] = consumed_heating_today
            result[CONSUMED_HEATING_TOTAL] = consumed_heating_total
            # The following line should check if consumed_heating_total before consumed_heating_today resets to zero. This would cause a spike in the signal. The spike is removed by the following lines.
            if PREVIOUS_CONSUMED_HEATING_TOTAL in result:
                if (
                    consumed_heating_total
                    == self.data.get(PREVIOUS_CONSUMED_HEATING_TOTAL)
                    or consumed_heating_today < 2
                ):
                    result[CONSUMED_HEATING] = self.assign_if_increased(
                        consumed_heating_total + consumed_heating_today,
                        CONSUMED_HEATING,
                    )
            else:
                result[PREVIOUS_CONSUMED_HEATING_TOTAL] = consumed_heating_total
                result[CONSUMED_HEATING] = (
                    consumed_heating_total + consumed_heating_today
                )

            result[CONSUMED_WATER_HEATING_TODAY] = consumed_water_today
            result[CONSUMED_WATER_HEATING_TOTAL] = consumed_water_total
            # The following line should check if consumed_water_total before consumed_water_today resets to zero. This would cause a spike in the signal. The spike is removed by the following lines.
            if PREVIOUS_CONSUMED_WATER_HEATING_TOTAL in result:
                if (
                    consumed_water_total
                    == self.data.get(PREVIOUS_CONSUMED_WATER_HEATING_TOTAL)
                    or consumed_water_today < 2
                ):
                    result[CONSUMED_WATER_HEATING] = self.assign_if_increased(
                        consumed_water_total + consumed_water_today,
                        CONSUMED_WATER_HEATING,
                    )
            else:
                result[PREVIOUS_CONSUMED_WATER_HEATING_TOTAL] = consumed_water_total
                result[CONSUMED_WATER_HEATING] = (
                    consumed_water_total + consumed_water_today
                )

            # decoder.skip_bytes(280)
            # result[CURRENT_POWER_CONSUMPTION] = decoder.decode_16bit_uint()
            # _LOGGER.debug(f"current power consumption {result[CURRENT_POWER_CONSUMPTION]}")
        return result

    async def set_data(self, key, value) -> None:
        """Write the data to the modbus."""
        _LOGGER.debug(f"set modbus register for {key} to {value}")
        if key == SG_READY_ACTIVE:
            await self.write_register(address=4000, value=value, slave=1)
        elif key == SG_READY_INPUT_1:
            await self.write_register(address=4001, value=value, slave=1)
        elif key == SG_READY_INPUT_2:
            await self.write_register(address=4002, value=value, slave=1)
        elif key == OPERATION_MODE:
            await self.write_register(address=1500, value=value, slave=1)
        elif key == COMFORT_TEMPERATURE_TARGET_HK1:
            await self.write_register(address=1501, value=int(value * 10), slave=1)
        elif key == ECO_TEMPERATURE_TARGET_HK1:
            await self.write_register(address=1502, value=int(value * 10), slave=1)
        elif key == HEATING_CURVE_RISE_HK1:
            await self.write_register(address=1503, value=int(value * 100), slave=1)
        elif key == COMFORT_TEMPERATURE_TARGET_HK2:
            await self.write_register(address=1504, value=int(value * 10), slave=1)
        elif key == ECO_TEMPERATURE_TARGET_HK2:
            await self.write_register(address=1505, value=int(value * 10), slave=1)
        elif key == HEATING_CURVE_RISE_HK2:
            await self.write_register(address=1506, value=int(value * 100), slave=1)
        elif key == COMFORT_TEMPERATURE_TARGET_HK3:
            await self.write_register(address=1550, value=int(value * 10), slave=1)
        elif key == ECO_TEMPERATURE_TARGET_HK3:
            await self.write_register(address=1551, value=int(value * 10), slave=1)
        elif key == HEATING_CURVE_RISE_HK3:
            await self.write_register(address=1552, value=int(value * 100), slave=1)
        elif key == DUALMODE_TEMPERATURE_HZG:
            await self.write_register(address=1508, value=int(value * 10), slave=1)
        elif key == COMFORT_WATER_TEMPERATURE_TARGET:
            await self.write_register(address=1509, value=int(value * 10), slave=1)
        elif key == ECO_WATER_TEMPERATURE_TARGET:
            await self.write_register(address=1510, value=int(value * 10), slave=1)
        elif key == DUALMODE_TEMPERATURE_WW:
            await self.write_register(address=1512, value=int(value * 10), slave=1)
        elif key == AREA_COOLING_TARGET_FLOW_TEMPERATURE:
            await self.write_register(address=1513, value=int(value * 10), slave=1)
        elif key == AREA_COOLING_TARGET_ROOM_TEMPERATURE:
            await self.write_register(address=1515, value=int(value * 10), slave=1)
        elif key == FAN_COOLING_TARGET_FLOW_TEMPERATURE:
            await self.write_register(address=1516, value=int(value * 10), slave=1)
        elif key == FAN_COOLING_TARGET_ROOM_TEMPERATURE:
            await self.write_register(address=1518, value=int(value * 10), slave=1)
        elif key == CIRCULATION_PUMP:
            await self.write_register(address=47012, value=value, slave=1)
        else:
            return
        self.data[key] = value

    async def async_reset_heatpump(self) -> None:
        """Reset the heat pump."""
        _LOGGER.debug("Reset the heat pump")
        await self.write_register(address=1519, value=3, slave=1)
