

import ssl
import asyncio
import urllib.parse
import os
from typing import Callable, Optional
from .auth import EOTAuthHandler
INTEGRATION_DIR = os.path.dirname(__file__)
CERT_PATH = os.path.join(INTEGRATION_DIR, "AmazonRootCA1.pem")
import paho.mqtt.client as mqtt




class AwsIotMqttClient:
    """
    AWS IoT MQTT Client
    - Custom Authorizer
    - ALPN over port 443
    - Paho MQTT v1 callbacks (Home Assistant safe)
    - Loop fully managed inside the class
    """
    def __init__(
        self,
        auth_handler: EOTAuthHandler,
        sub_topic: str,
        user_email : str,
        entry_id:str

    ):

        self._user_email = user_email
        self._auth_handler= auth_handler
        self.sub_topic = sub_topic
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self._device_id = entry_id


        self.external_message_listener: Optional[
            Callable[[str, str], None]
        ] = None


    def set_message_listener(self, callback: Callable[[str, str], None]):
        self.external_message_listener = callback
        
    

    
    def start_background(self):
        """Connect and start NON-BLOCKING MQTT loop"""
        self._setup_client()

        if not self._connect():
            return

        self.client.loop_start()

    def stop(self):
        """Stop MQTT loop and disconnect"""
        if self.client:
            try:
                self.client.loop_stop()
            except Exception:
                pass
            self.client.disconnect()
            self.connected = False

    def publish(self, payload: str, topic: str) -> bool:
        if not self.connected:
            return False

        result = self.client.publish(topic, payload, qos=1)
        return result.rc == mqtt.MQTT_ERR_SUCCESS

  
    def _setup_client(self):
        if self.client:
            return
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
           access_token = loop.run_until_complete(self._auth_handler.async_get_access_token())
        finally:
            loop.close()
        client_id = f"eotHAClient_{self._user_email}_{self._device_id}"

        encoded_auth = urllib.parse.quote("MyESP32Authorizer")
        encoded_token = urllib.parse.quote(f"Bearer {access_token}")
        
        username = (
            f"{self._user_email}/{self._device_id}"
            f"?x-amz-customauthorizer-name={encoded_auth}"
            f"&token={encoded_token}"
        )

        self.client = mqtt.Client(
            client_id=client_id,
            protocol=mqtt.MQTTv311,
            transport="tcp",
        )

        self.client.username_pw_set(username=username)


        ssl_ctx = ssl.create_default_context()
        ssl_ctx.load_verify_locations(CERT_PATH)
        ssl_ctx.set_alpn_protocols(["mqtt"])

        self.client.tls_set_context(ssl_ctx)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
 

    def _connect(self) -> bool:
        try:
            self.client.connect("a2xn0k34m1px32-ats.iot.ap-south-1.amazonaws.com", 443, keepalive=60)
            return True
        except Exception as e:
            return False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            client.subscribe(self.sub_topic, qos=1)



    def _on_disconnect(self, client, userdata, rc):
        self.connected = False

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        if self.external_message_listener:
            self.external_message_listener(topic, payload)
            return

   