// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::Command;
use tauri::Manager;

#[tauri::command]
fn start_kernel() -> String {
    // Attempt to spawn the python kernel
    // We assume 'python3' is in path and the current directory is correctly set or we resolve it.
    // Since this runs from the GUI binary, we need to locate the repo root or assume installation.
    // For this prototype, we'll try to execute `python3 -m fyodoros` assuming we are in repo root
    // or set PYTHONPATH.

    // In a real app, we might want to bundle the python interpreter or use a fixed path.
    match Command::new("python3")
        .arg("-m")
        .arg("fyodoros")
        .spawn() {
            Ok(_) => "Kernel Process Spawned".to_string(),
            Err(e) => format!("Failed to spawn kernel: {}", e),
        }
}

fn main() {
  tauri::Builder::default()
    .invoke_handler(tauri::generate_handler![start_kernel])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
