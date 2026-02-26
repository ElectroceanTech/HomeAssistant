"""EOT HOME API Client with AWS IoT MQTT Integration for Real-time State Updates."""
from __future__ import annotations
import socket
import json
import asyncio
from typing import Any, Optional
import aiohttp
import async_timeout
from homeassistant.core import HomeAssistant
from .auth import EOTAuthHandler
from .iotfile import AwsIotMqttClient

from .const import API_URL





class EotHomeApiClientError(Exception):
    """Exception to indicate a general API error."""


class EotHomeApiClientCommunicationError(
    EotHomeApiClientError,
):
    """Exception to indicate a communication error."""


class EotHomeApiClientAuthenticationError(
    EotHomeApiClientError,
):
    """Exception to indicate an authentication error."""


def _verify_response_or_raise(response: aiohttp.ClientResponse) -> None:
    """Verify that the response is valid."""
    if response.status in (401, 403):
        msg = "Invalid credentials"
        raise EotHomeApiClientAuthenticationError(msg)
    response.raise_for_status()

class DeviceConverter:
    """Convert between Google Assistant and Home Assistant device types."""
    
    # Map Google Assistant device types to Home Assistant domains
    GA_TO_HA_DEVICE_TYPE = {
        "action.devices.types.LIGHT": "light",
        "action.devices.types.SWITCH": "switch",
        "action.devices.types.FAN": "fan",
        "action.devices.types.CURTAIN": "cover",
        "action.devices.types.SCENE": "scene",
        "action.devices.types.SENSOR": "binary_sensor",  # Added motion sensor
    }
    
    # Map Home Assistant domains to Google Assistant device types
    HA_TO_GA_DEVICE_TYPE = {v: k for k, v in GA_TO_HA_DEVICE_TYPE.items()}
    
    @staticmethod
    def ga_to_ha_type(ga_type: str) -> str:
        """Convert Google Assistant device type to Home Assistant domain."""
        return DeviceConverter.GA_TO_HA_DEVICE_TYPE.get(ga_type, "switch")
    
    @staticmethod
    def ha_to_ga_type(ha_domain: str) -> str:
        """Convert Home Assistant domain to Google Assistant device type."""
        return DeviceConverter.HA_TO_GA_DEVICE_TYPE.get(
            ha_domain, 
            "action.devices.types.SWITCH"
        )
    
    @staticmethod
    def convert_ga_device_to_ha(ga_device: dict[str, Any]) -> dict[str, Any]:
        """Convert Google Assistant device format to Home Assistant format."""
        device_type = ga_device.get("type", "action.devices.types.SWITCH")
        traits = ga_device.get("traits", [])
        
        ha_device = {
            "id": ga_device.get("id"),
            "name": ga_device.get("name", {}).get("name", "Unknown Device"),
            "type": DeviceConverter.ga_to_ha_type(device_type),
            "room": ga_device.get("roomHint"),
            "model": ga_device.get("deviceInfo", {}).get("model"),
            "manufacturer": ga_device.get("deviceInfo", {}).get("manufacturer"),
            "sw_version": ga_device.get("deviceInfo", {}).get("swVersion"),
            "hw_version": ga_device.get("deviceInfo", {}).get("hwVersion"),
            "will_report_state": ga_device.get("willReportState", False),
        }
        
        # Convert traits to capabilities
        capabilities = []
        
        if "action.devices.traits.OnOff" in traits:
            capabilities.append("onoff")
        if "action.devices.traits.Brightness" in traits:
            capabilities.append("brightness")
        if "action.devices.traits.ColorSetting" in traits:
            capabilities.append("color")
        if "action.devices.traits.FanSpeed" in traits:
            capabilities.append("fan_speed")
        if "action.devices.traits.TemperatureSetting" in traits:
            capabilities.append("temperature")
        if "action.devices.traits.OpenClose" in traits:
            capabilities.append("position")
        if "action.devices.traits.Scene" in traits:
            capabilities.append("scene")
        if "action.devices.traits.OccupancySensing" in traits:  # Added motion sensor trait
            capabilities.append("occupancy")
            
        ha_device["capabilities"] = capabilities
        ha_device["original_type"] = device_type
        ha_device["traits"] = traits
        
        # For devices that don't report state (like scenes), set default state
        if not ha_device["will_report_state"]:
            ha_device["available"] = True
            if ha_device["type"] == "scene":
                ha_device["state"] = "off"
            else:
                ha_device["state"] = "unknown"
        
        # Motion sensors have default state
        if ha_device["type"] == "binary_sensor" and "occupancy" in capabilities:
            ha_device["state"] = "not_detected"
            ha_device["available"] = True
        
        return ha_device
    
    @staticmethod
    def convert_ga_state_to_ha(
        ga_state: dict[str, Any], 
        device_type: str
    ) -> dict[str, Any]:
        """Convert Google Assistant device state to Home Assistant state."""
        ha_state = {
            "available": ga_state.get("online", True),
        }
        
        # OnOff state
        if "on" in ga_state:
            ha_state["state"] = "on" if ga_state["on"] else "off"
        else:
            ha_state["state"] = "off"
        
        # Brightness
        if "brightness" in ga_state:
            ha_state["brightness"] = ga_state.get("brightness", 0)
        else:
            ha_state["brightness"] = 0
        
        # Color
        if "color" in ga_state:
            color = ga_state["color"]
            if "temperatureK" in color:
                ha_state["color_temp"] = color.get("temperatureK")
        
        # Fan speed
        if "currentFanSpeedSetting" in ga_state:
            ha_state["percentage"] = int(ga_state.get("currentFanSpeedSetting", "0")) * 25
        
        # Temperature
        if "thermostatTemperatureAmbient" in ga_state:
            ha_state["current_temperature"] = ga_state["thermostatTemperatureAmbient"]
        if "thermostatTemperatureSetpoint" in ga_state:
            ha_state["temperature"] = ga_state["thermostatTemperatureSetpoint"]
        if "thermostatMode" in ga_state:
            ha_state["hvac_mode"] = DeviceConverter._ga_to_ha_hvac_mode(
                ga_state["thermostatMode"]
            )
        
        # Lock state
        if "isLocked" in ga_state:
            ha_state["state"] = "locked" if ga_state["isLocked"] else "unlocked"
        
        # Cover position
        if "openPercent" in ga_state:
            ha_state["current_position"] = ga_state["openPercent"]
            ha_state["state"] = "open" if ga_state["openPercent"] > 0 else "closed"
        
        # Motion/Occupancy sensor state (Google Home)
        if "occupancy" in ga_state:
            occupancy_state = ga_state["occupancy"]
            if occupancy_state == "OCCUPIED":
                ha_state["state"] = "detected"
            elif occupancy_state == "UNOCCUPIED":
                ha_state["state"] = "not_detected"
            else:
                ha_state["state"] = "not_detected"
        
        return ha_state
    
    @staticmethod
    def _ga_to_ha_hvac_mode(ga_mode: str) -> str:
        """Convert Google Assistant HVAC mode to Home Assistant."""
        mode_map = {
            "off": "off",
            "heat": "heat",
            "cool": "cool",
            "on": "heat_cool",
            "auto": "auto",
            "fan-only": "fan_only",
            "dry": "dry",
            "eco": "eco",
        }
        return mode_map.get(ga_mode, "auto")


class EotHomeApiClient:
    """EOT HOME API Client with real-time AWS IoT MQTT sync."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        auth_handler: EOTAuthHandler,
        user_email: str,
        entry_id = "",
        enable_mqtt: bool = True,
    ) -> None:
        self._session = session
        self._auth_handler = auth_handler
        self._user_email = user_email
        self._enable_mqtt = enable_mqtt
        self._entry_id= entry_id
        self._converter = DeviceConverter()
        self._device_states_cache: dict[str, dict] = {}

        self._mqtt: Optional[AwsIotMqttClient] = None
        self._hass: Optional[HomeAssistant] = None
        self._coordinator = None
        self.relay_keys = ["r1","r2","r3","r4","r5","r6","r7","r8","rall"]
        self.curtain_keys = ["c0","c1"]
        self.dimmer_keys = ["dimmer"]
        self.fan_keys = ["fan"]
        self.motion_sensor_keys = ["motionSensor"]

    # -------------------------------------------------
    # HA lifecycle injection
    # -------------------------------------------------

    def set_hass_and_coordinator(self, hass: HomeAssistant, coordinator) -> None:
        """Inject HA runtime objects (called from async_setup_entry)."""
        self._hass = hass
        self._coordinator = coordinator

    # -------------------------------------------------
    # MQTT handling
    # -------------------------------------------------
    
    def _handle_mqtt_message(self, topic: str, payload: str) -> None:
        """
        MQTT RX callback (runs in Paho thread)
        NEVER touch HA objects directly here
        """
       

        if not self._hass or not self._coordinator:
            return

        self._hass.loop.call_soon_threadsafe(
            asyncio.create_task,
            self._async_process_mqtt_message(topic, payload),
        )
    
      
    async def _async_process_mqtt_message(self, topic: str, payload: str) -> None:
      

      try:
        msg = json.loads(payload)
        data = msg.get("body", {}).get("data", {})
      except json.JSONDecodeError:
        return

      d_id = data.get("d_id")
      if not d_id:
        return

      
      relay = next((k for k in self.relay_keys if k in data), None)
      curtain = next((k for k in self.curtain_keys if k in data), None)
      dimmer = next((k for k in self.dimmer_keys if k in data), None)
      fan = next((k for k in self.fan_keys if k in data), None)
      motionSensor = next((k for k in self.motion_sensor_keys if k in data), None)
      
      if relay: 
        switches = self._coordinator.data.setdefault("switches", {})
        for key in self.relay_keys:
          if key in data: 
             device_id = f"{self._user_email}-{d_id}-{key}"
             
             switch = switches.get(device_id, {})
             if switch:
               switch["state"] = "on" if str(data[key]) == "1" else "off"
          else:
              continue
              
      elif curtain:
        curtains = self._coordinator.data.setdefault("covers", {})
        for key in self.curtain_keys:
          if key in data: 
             device_id = f"{self._user_email}-{d_id}-{key}"
             
             curtain = curtains.get(device_id, {})
             if curtain:
               curtain["position"] = 100 if str(data[key]) == "1" else 0
               curtain["is_closed"] = False if str(data[key]) == "1" else True
          else:
              continue
              
      elif dimmer:  
        ''' LIGHT_TYPE_TO_COLOR_TEMP = {
            3: 2500,  # warmWhite
            5: 3200,  # softWhite
            2: 3800,  # white
            4: 4400,  # dayLightWhite
            1: 5000,  # naturalWhite
        } '''

        LIGHT_TYPE_TO_COLOR_TEMP = {
            2: 5000,  # white
            4: 4400,  # dayLightWhite
            1: 3800,  # naturalWhite
            5: 3200,  # sofWhite
            3: 2500,  # warmWhite
        }

        dimmers = self._coordinator.data.setdefault("lights", {})
        for key in self.dimmer_keys:
          if key in data: 
             device_id = f"{self._user_email}-{d_id}-{key}"
             bri = int(data.get("brightNess", "0"))
             per = 0 if not 0 <= bri <= 255 else round((bri / 255) * 100)
             dimmer = dimmers.get(device_id, {})
             if dimmer:
               dimmer["state"] = "on" if str(data[key]) == "1" else "off"
               dimmer["brightness"] = per
               dimmer["color_temp"] = LIGHT_TYPE_TO_COLOR_TEMP.get(int(data["lightType"]), 3800)
              
          else:
              continue 
              
      elif fan: 
        fans = self._coordinator.data.setdefault("fans", {})
        for key in self.fan_keys:
          if key in data: 
             device_id = f"{self._user_email}-{d_id}-{key}"
             percentage = int(data.get("fanspeed", "0")) * 25
             fan = fans.get(device_id, {})
             if fan:
               fan["state"] = "on" if str(data[key]) == "1" else "off"
               fan["percentage"] = percentage
          else:
              continue
              
      elif motionSensor:
        motion_sensors = self._coordinator.data.setdefault("motion_sensors", {})
        for key in self.motion_sensor_keys:
          if key in data:
             device_id = f"{self._user_email}-{d_id}-{key}"
             
             sensor = motion_sensors.get(device_id, {})
             if sensor:
               # Convert motion sensor value to detected/not_detected
               # Assuming: "1" = detected, "0" = not_detected
               sensor["state"] = "detected" if str(data[key]) == "1" else "not_detected"
          else:
              continue

      self._coordinator.async_set_updated_data(self._coordinator.data)
    def start_mqtt(self) -> None:
        """Start AWS IoT MQTT client (HA-safe, non-blocking)."""
        if not self._enable_mqtt or self._mqtt:
            return

        self._mqtt = AwsIotMqttClient(
           sub_topic=f"users/{self._user_email}/update/response",
           auth_handler=self._auth_handler,
           user_email=self._user_email,
           entry_id= self._entry_id
        )

        self._mqtt.set_message_listener(self._handle_mqtt_message)
        self._mqtt.start_background()


    def stop_mqtt(self) -> None:
        """Stop AWS IoT MQTT client."""
        if self._mqtt:
            self._mqtt.stop()
            self._mqtt = None
   
    async def async_get_data(self) -> Any:
        """Get data from the API - for testing/compatibility."""
        result = await self.async_get_devices()
        return result



    async def async_sync_devices(self) -> dict[str, Any]:
        """SYNC: Get all devices (Google Assistant SYNC intent)."""
        return await self._api_wrapper(
            method="post",
            url=API_URL,
            data={
                "requestId": "6894439706274654512",
                "inputs": [{
                    "intent": "action.devices.SYNC"
                }]
            }
        )

    async def async_query_devices(self, device_ids: list[str]) -> dict[str, Any]:
        """QUERY: Get current state of devices (Google Assistant QUERY intent)."""
        
        return await self._api_wrapper(
            method="post",
            url=API_URL,
            data={
                "requestId": "6894439706274654513",
                "inputs": [{
                    "intent": "action.devices.QUERY",
                    "payload": {
                        "devices": [{"id": device_id} for device_id in device_ids]
                    }
                }]
            }
        )

    async def _refresh_device_state_after_command(
        self, 
        device_id: str, 
        command_result: dict[str, Any]
    ) -> None:
        """Refresh device state in cache after command execution."""
        try:
            if not command_result or not isinstance(command_result, dict):
                return
            
            payload = command_result.get("payload", {})
            commands = payload.get("commands", [])
            
            for command in commands:
                if device_id in command.get("ids", []):
                    states = command.get("states", {})
                    if states:
                        # Update cache with new state
                        self._device_states_cache[device_id] = states

        except Exception as e:
            return

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Get list of devices in Home Assistant format with current states."""
        result = await self.async_sync_devices()
        
        if isinstance(result, dict):
            payload = result.get("payload", {})
            ga_devices = payload.get("devices", [])
            
            # Convert each device to HA format
            ha_devices = [
                self._converter.convert_ga_device_to_ha(device)
                for device in ga_devices
            ]
            
            # Fetch current states for all devices that report state
            if ha_devices:
                queryable_device_ids = []
                for ga_device in ga_devices:
                    if ga_device.get("willReportState", False):
                        queryable_device_ids.append(ga_device.get("id"))
                
                if queryable_device_ids:
                    try:
                        state_result = await self.async_query_devices(queryable_device_ids)
                        
                        if isinstance(state_result, dict):
                            state_payload = state_result.get("payload", {})
                            device_states = state_payload.get("devices", {})
                            
                            # Update cache with queried states
                            for device_id, ga_state in device_states.items():
                                self._device_states_cache[device_id] = ga_state
                    except Exception as e:
                        return
                
                # Attach states to devices (from cache or fresh query)
                for ha_device in ha_devices:
                    device_id = ha_device.get("id")
                    if device_id in self._device_states_cache:
                        ga_state = self._device_states_cache[device_id]
                        ha_state = self._converter.convert_ga_state_to_ha(
                            ga_state,
                            ha_device["type"]
                        )
                        ha_device.update(ha_state)

            
            return ha_devices
        
        return []

    def get_cached_device_state(self, device_id: str) -> dict[str, Any] | None:
        """Get cached device state without querying the API.
        
        Returns the last known state from cache (updated by MQTT), or None if not cached.
        """
        return self._device_states_cache.get(device_id)

    async def async_handle_brightness(
        self,
        device_id: str,
        per : int
    ) -> bool:
        """Set brightness (Home Assistant: 0-255)."""
        parts = device_id.split("-")
        userId= parts[0]
        dId = parts[1]
        subDId=parts[2]
        msg={"d_id":dId, "operationType" : "relayChangeRequest" , "opUsr" : userId}
        bri = 0 if per == 0 else round((per / 100) * 255)
        msg["brightNess"]  = str(bri) 
        return self._mqtt.publish(json.dumps(msg),f"users/{userId}/update/{dId}")
        
        return False




    async def async_set_speed(
        self,
        device_id: str,
        speed: int
    ) -> bool:
        """Set fan speed by percentage."""
        parts = device_id.split("-")
        userId= parts[0]
        dId = parts[1]
        subDId=parts[2]
        msg={"d_id":dId, "operationType" : "relayChangeRequest" , "opUsr" : userId}
       
        msg["fan"]  = str(speed)
        return self._mqtt.publish(json.dumps(msg),f"users/{userId}/update/{dId}")
        



    async def async_handle_scene(
        self,
        device_id: str
    ) -> bool:
        """Activate a scene."""
        parts = device_id.split("-")
        userId= parts[0]
        dId = parts[1]
        subDId=parts[2]
        msg={"d_id":dId, "operationType" : "sceneExecuteRequestById" , "opUsr" : userId}
        msg["scId"] = subDId
        self._mqtt.publish(json.dumps(msg),f"{userId}")
        return self._mqtt.publish(json.dumps(msg),f"users/{userId}/update/{dId}")


    
    
    async def async_handle_color_temp(
    self, device_id: str, temperature: float
) -> bool:
      """Set color temperature."""
      parts = device_id.split("-")
      userId = parts[0]
      dId = parts[1]
      subDId = parts[2]

      # Hardware light type codes mapped to Kelvin midpoints
    # 1: naturalWhite  ~5000K
    # 2: white         ~3800K
    # 3: warmWhite     ~2500K
    # 4: dayLightWhite ~4400K
    # 5: softWhite     ~3200K
    # white - 5000 ,dayLightWhite,naturalWhite,softWhite,warmWhite - 2500

      def get_light_type(temp: float) -> int:
        if temp >= 4700:       # ~5000K → white
            return 2
        elif temp >= 4100:     # ~4400K → dayLightWhite
            return 4
        elif temp >= 3500:     # ~3800K → naturalWhite
            return 1
        elif temp >= 2850:     # ~3200K → softWhite
            return 5
        else:                  # ~2500K → warmWhite
            return 3
      light_type = get_light_type(temperature)

      msg = {
        "d_id": dId,
        "operationType": "relayChangeRequest",
        "opUsr": userId,
        "lightType": str(light_type)
    }

      return self._mqtt.publish(json.dumps(msg), f"users/{userId}/update/{dId}")


    async def async_handle_curtain_position(self, device_id: str, position: int) -> bool:
        """Set curtain/cover position."""
        parts = device_id.split("-")
        userId= parts[0]
        dId = parts[1]
        subDId=parts[2]
        msg={"d_id":dId, "operationType" : "relayChangeRequest" , "opUsr" : userId}

        keyList = {
        "c0": {100: "r1", 0: "r2"},
        "c1": {100: "r3", 0: "r4"}
       }

        if subDId in ("c0", "c1"):
            newSub = keyList[subDId][position]
            msg[newSub]  = "1"
            return self._mqtt.publish(json.dumps(msg),f"users/{userId}/update/{dId}")
           
        return False



    async def async_handle_on_off(self, device_id: str, state: bool) -> bool:
       parts = device_id.split("-")
       userId= parts[0]
       dId = parts[1]
       subDId=parts[2]
       msg={"d_id":dId, "operationType" : "relayChangeRequest" , "opUsr" : userId}
       if subDId in self.relay_keys:
           msg[subDId]  = "1" if state else "0" 
           return self._mqtt.publish(json.dumps(msg),f"users/{userId}/update/{dId}")
       elif subDId  in self.fan_keys:
            msg["r6"]  = "1" if state else "0" 
            return self._mqtt.publish(json.dumps(msg),f"users/{userId}/update/{dId}")
       elif subDId in self.dimmer_keys:
               msg["rall"]  = "1" if state else "0" 
               return self._mqtt.publish(json.dumps(msg),f"users/{userId}/update/{dId}")
       return False
       

       

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Get information from the API with authentication."""
        try:
            token = await self._auth_handler.async_get_access_token()

            request_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            if headers:
                request_headers.update(headers)



            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    json=data,
                )

                response_text = await response.text()

                _verify_response_or_raise(response)

                return await response.json()

        except TimeoutError as exception:
            msg = f"Timeout error fetching information - {exception}"
            raise EotHomeApiClientCommunicationError(msg) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            msg = f"Error fetching information - {exception}"
            raise EotHomeApiClientCommunicationError(msg) from exception
        except Exception as exception:
            msg = f"Something really wrong happened! - {exception}"
            raise EotHomeApiClientError(msg) from exception
    
