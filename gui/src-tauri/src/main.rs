// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::Command;
use tauri::Manager;

/// Starts the LooP kernel as a subprocess.
///
/// This command is invoked from the React frontend. It attempts to execute
/// `python3 -m loop serve` to launch the kernel in API mode.
///
/// # Returns
///
/// A `String` indicating success ("Kernel Process Spawned") or an error message.
#[tauri::command]
fn start_kernel() -> String {
    // Attempt to spawn the python kernel
    // We assume 'python3' is in path and the current directory is correctly set or we resolve it.
    // Since this runs from the GUI binary, we need to locate the repo root or assume installation.
    // For this prototype, we'll try to execute `python3 -m loop serve` assuming we are in repo root
    // or set PYTHONPATH.

    // In a real app, we might want to bundle the python interpreter or use a fixed path.
    match Command::new("python3")
        .arg("-m")
        .arg("loop")
        .arg("serve")
        .spawn() {
            Ok(_) => "Kernel Process Spawned (API Mode)".to_string(),
            Err(e) => format!("Failed to spawn kernel: {}", e),
        }
}

/// Main entry point for the Tauri backend.
///
/// Initializes the Tauri application, registers the `start_kernel` command,
/// and runs the application loop.
fn main() {
  tauri::Builder::default()
    .invoke_handler(tauri::generate_handler![start_kernel])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
