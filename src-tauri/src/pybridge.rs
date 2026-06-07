use std::process::Stdio;
use tokio::process::{Child, Command};
use tokio::time::{sleep, Duration};
use serde_json::Value;

pub struct PyBridge {
    child: Child,
    port: u16,
    client: reqwest::Client,
}

impl PyBridge {
    pub async fn start() -> Result<Self, Box<dyn std::error::Error>> {
        let port = portpicker::pick_unused_port().expect("No free ports available");

        let child = Command::new("python")
            .arg("-m")
            .arg("backend.app")
            .env("CINEFORGE_PORT", port.to_string())
            .env("CINEFORGE_DATA_DIR", dirs::data_dir()
                .map(|p| p.join("com.lumenhelix.cineforge").to_string_lossy().to_string())
                .unwrap_or_else(|| ".cineforge".to_string()))
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .kill_on_drop(true)
            .spawn()?;

        let client = reqwest::Client::new();

        // Wait for backend to come up (max 30s)
        for _ in 0..60 {
            sleep(Duration::from_millis(500)).await;
            if let Ok(resp) = client
                .get(format!("http://127.0.0.1:{}/health", port))
                .timeout(Duration::from_secs(2))
                .send()
                .await
            {
                if resp.status().is_success() {
                    log::info!("Python backend ready on port {}", port);
                    return Ok(PyBridge { child, port, client });
                }
            }
        }

        Err("Python backend failed to start within 30 seconds".into())
    }

    pub fn port(&self) -> u16 {
        self.port
    }

    pub async fn healthcheck(&self) -> Result<Value, reqwest::Error> {
        self.client
            .get(format!("http://127.0.0.1:{}/health", self.port))
            .send()
            .await?
            .json::<Value>()
            .await
    }

    pub async fn restart(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        let _ = self.child.kill().await;
        let new = Self::start().await?;
        self.child = new.child;
        self.port = new.port;
        self.client = new.client;
        Ok(())
    }
}

impl Drop for PyBridge {
    fn drop(&mut self) {
        let _ = self.child.start_kill();
    }
}
