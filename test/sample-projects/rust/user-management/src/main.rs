use tokio::net::TcpListener;
use std::collections::HashMap;
use uuid::Uuid;
use serde_json::json;

mod models;
mod services;
mod utils;

use models::{User, UserRole};
use services::UserManager;
use utils::errors::UserError;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Starting User Management Server...");

    let mut user_manager = UserManager::new();

    // Create some sample users
    let admin_user = user_manager.create_user(
        "admin".to_string(),
        "admin@example.com".to_string(),
        "System".to_string(),
        "Administrator".to_string(),
    )?;
    user_manager.set_user_role(admin_user.id, UserRole::Admin)?;

    let regular_user = user_manager.create_user(
        "john_doe".to_string(),
        "john@example.com".to_string(),
        "John".to_string(),
        "Doe".to_string(),
    )?;

    // Start TCP server
    let listener = TcpListener::bind("127.0.0.1:8080").await?;
    println!("Server listening on 127.0.0.1:8080");

    loop {
        let (mut socket, addr) = listener.accept().await?;
        let mut manager = user_manager.clone();

        tokio::spawn(async move {
            let mut buffer = [0; 1024];
            match socket.read(&mut buffer).await {
                Ok(n) => {
                    if n == 0 {
                        return;
                    }

                    let request = String::from_utf8_lossy(&buffer[..n]);
                    let response = handle_request(&request, &mut manager);
                    
                    if let Err(e) = socket.write_all(response.as_bytes()).await {
                        eprintln!("Failed to send response: {}", e);
                    }
                }
                Err(e) => {
                    eprintln!("Failed to read from socket: {}", e);
                }
            }
        });
    }
}

fn handle_request(request: &str, user_manager: &mut UserManager) -> String {
    let parts: Vec<&str> = request.trim().split_whitespace().collect();
    
    if parts.is_empty() {
        return "ERROR: Empty request".to_string();
    }

    match parts[0] {
        "CREATE" => {
            if parts.len() < 5 {
                return "ERROR: Usage: CREATE username email first_name last_name".to_string();
            }
            
            match user_manager.create_user(
                parts[1].to_string(),
                parts[2].to_string(),
                parts[3].to_string(),
                parts[4].to_string(),
            ) {
                Ok(user) => format!("OK: User created with ID: {}", user.id),
                Err(e) => format!("ERROR: {}", e),
            }
        }
        "GET" => {
            if parts.len() < 2 {
                return "ERROR: Usage: GET <username|email|id>".to_string();
            }
            
            if let Ok(uuid) = Uuid::parse_str(parts[1]) {
                match user_manager.get_user_by_id(uuid) {
                    Ok(user) => format_user_info(&user),
                    Err(e) => format!("ERROR: {}", e),
                }
            } else if parts[1].contains('@') {
                match user_manager.get_user_by_email(parts[1]) {
                    Ok(user) => format_user_info(&user),
                    Err(e) => format!("ERROR: {}", e),
                }
            } else {
                match user_manager.get_user_by_username(parts[1]) {
                    Ok(user) => format_user_info(&user),
                    Err(e) => format!("ERROR: {}", e),
                }
            }
        }
        "LIST" => {
            let users = user_manager.list_users();
            if users.is_empty() {
                return "No users found".to_string();
            }
            
            let user_list: Vec<String> = users.iter()
                .map(|u| format!("{} ({})", u.username, u.email))
                .collect();
            
            format!("Users:\n{}", user_list.join("\n"))
        }
        "DELETE" => {
            if parts.len() < 2 {
                return "ERROR: Usage: DELETE <username|email|id>".to_string();
            }
            
            let user_id = if let Ok(uuid) = Uuid::parse_str(parts[1]) {
                uuid
            } else if parts[1].contains('@') {
                match user_manager.get_user_by_email(parts[1]) {
                    Ok(user) => user.id,
                    Err(e) => return format!("ERROR: {}", e),
                }
            } else {
                match user_manager.get_user_by_username(parts[1]) {
                    Ok(user) => user.id,
                    Err(e) => return format!("ERROR: {}", e),
                }
            };
            
            match user_manager.delete_user(user_id) {
                Ok(_) => "OK: User deleted".to_string(),
                Err(e) => format!("ERROR: {}", e),
            }
        }
        "HELP" => {
            "Available commands:\n\
             CREATE username email first_name last_name - Create a new user\n\
             GET <username|email|id> - Get user information\n\
             LIST - List all users\n\
             DELETE <username|email|id> - Delete a user\n\
             HELP - Show this help message".to_string()
        }
        _ => {
            "ERROR: Unknown command. Type HELP for available commands.".to_string()
        }
    }
}

fn format_user_info(user: &User) -> String {
    format!(
        "User ID: {}\n\
         Username: {}\n\
         Email: {}\n\
         Name: {} {}\n\
         Role: {:?}\n\
         Status: {:?}\n\
         Created: {}\n\
         Updated: {}",
        user.id,
        user.username,
        user.email,
        user.first_name,
        user.last_name,
        user.role,
        user.status,
        user.created_at,
        user.updated_at
    )
}

impl Clone for UserManager {
    fn clone(&self) -> Self {
        // For simplicity, create a new manager with empty state
        // In a real application, you'd want to properly clone the state
        UserManager::new()
    }
}