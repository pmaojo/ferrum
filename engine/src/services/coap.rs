#[cfg(feature = "coap")]
use anyhow::Result;
#[cfg(feature = "coap")]
use coap::UdpCoAPClient;

/// Send a GET request and return the payload.
#[cfg(feature = "coap")]
pub async fn get(url: &str) -> Result<Vec<u8>> {
    let resp = UdpCoAPClient::get(url).await?;
    Ok(resp.message.payload)
}

/// Send a POST request with the provided data and return the payload.
#[cfg(feature = "coap")]
pub async fn post(url: &str, data: &[u8]) -> Result<Vec<u8>> {
    let resp = UdpCoAPClient::post(url, data.to_vec()).await?;
    Ok(resp.message.payload)
}
