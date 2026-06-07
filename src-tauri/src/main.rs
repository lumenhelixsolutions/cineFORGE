use std::sync::Arc;
use tauri::{Manager, RunEvent, WindowEvent};
use tokio::sync::Mutex;

mod pybridge;
use pybridge::PyBridge;

struct AppState {
    py: Arc<Mutex<PyBridge>>,
}

#[tauri::command]
async fn get_backend_port(state: tauri::State<'_, AppState>) -> Result<u16, String> {
    let py = state.py.lock().await;
    Ok(py.port())
}

#[tauri::command]
async fn healthcheck(state: tauri::State<'_, AppState>) -> Result<serde_json::Value, String> {
    let py = state.py.lock().await;
    py.healthcheck().await.map_err(|e| e.to_string())
}

#[tauri::command]
async fn restart_backend(state: tauri::State<'_, AppState>) -> Result<u16, String> {
    let mut py = state.py.lock().await;
    py.restart().await.map_err(|e| e.to_string())?;
    Ok(py.port())
}

fn main() {
    env_logger::init();
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_store::Builder::new().build())
        .setup(|app| {
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let bridge = PyBridge::start().await.expect("Failed to start Python backend");
                let state = AppState { py: Arc::new(Mutex::new(bridge)) };
                handle.manage(state);
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_backend_port,
            healthcheck,
            restart_backend
        ])
        .build(tauri::generate_context!())
        .expect("Error while running tauri application")
        .run(|_app_handle, event| match event {
            RunEvent::WindowEvent { event: WindowEvent::CloseRequested { .. }, .. } => {
                // Graceful shutdown handled by PyBridge Drop
            }
            _ => {}
        });
}
