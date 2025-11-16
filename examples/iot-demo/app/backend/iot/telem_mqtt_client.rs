use rumqttc::{MqttOptions, Client};

pub fn telem_mqtt_client() -> Client {
    let options = MqttOptions::new("telem", "localhost", 1883);
    // ⛳ AI_FILL[iot_mqtt_client] --context=iot:telem
    Client::new(options, 10)
}
