#[cfg(feature = "mqtt")]
use anyhow::Result;
#[cfg(feature = "mqtt")]
use rumqttc::{AsyncClient, MqttOptions, QoS};
#[cfg(feature = "mqtt")]
use tokio::task;

/// Connect to an MQTT broker and spawn the event loop.
#[cfg(feature = "mqtt")]
pub async fn connect(
    client_id: &str,
    host: &str,
    port: u16,
) -> (AsyncClient, task::JoinHandle<()>) {
    let opts = MqttOptions::new(client_id, host, port);
    let (client, mut eventloop) = AsyncClient::new(opts, 10);
    let handle = task::spawn(async move { while let Ok(_) = eventloop.poll().await {} });
    (client, handle)
}

/// Publish a message using an existing client.
#[cfg(feature = "mqtt")]
pub async fn publish(client: &AsyncClient, topic: &str, payload: &str) -> Result<()> {
    client
        .publish(topic, QoS::AtLeastOnce, false, payload)
        .await?;
    Ok(())
}
