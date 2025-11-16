use anyhow::Result;
use serde::{Deserialize, Serialize};

pub struct ApiClient {
    base_url: String,
    client: reqwest::blocking::Client,
}

impl ApiClient {
    pub fn new(base_url: String) -> Self {
        Self {
            base_url,
            client: reqwest::blocking::Client::new(),
        }
    }

    pub fn get<T: for<'de> Deserialize<'de>>(&self, path: &str) -> Result<T> {
        let url = format!("{}{}", self.base_url, path);
        let response = self.client.get(&url).send()?;
        let data = response.json()?;
        Ok(data)
    }

    pub fn post<T: Serialize, R: for<'de> Deserialize<'de>>(
        &self,
        path: &str,
        body: &T,
    ) -> Result<R> {
        let url = format!("{}{}", self.base_url, path);
        let response = self.client.post(&url).json(body).send()?;
        let data = response.json()?;
        Ok(data)
    }
    
    pub fn put<T: Serialize, R: for<'de> Deserialize<'de>>(
        &self,
        path: &str,
        body: &T,
    ) -> Result<R> {
        let url = format!("{}{}", self.base_url, path);
        let response = self.client.put(&url).json(body).send()?;
        let data = response.json()?;
        Ok(data)
    }
    
    pub fn delete(&self, path: &str) -> Result<()> {
        let url = format!("{}{}", self.base_url, path);
        self.client.delete(&url).send()?;
        Ok(())
    }
}
