use regex::Regex;
use crate::utils::errors::UserError;

pub fn validate_email(email: &str) -> Result<(), UserError> {
    let email_regex = Regex::new(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        .map_err(|_| UserError::ValidationError("Invalid email regex".to_string()))?;
    
    if !email_regex.is_match(email) {
        return Err(UserError::ValidationError("Invalid email format".to_string()));
    }
    
    Ok(())
}

pub fn validate_username(username: &str) -> Result<(), UserError> {
    if username.len() < 3 {
        return Err(UserError::ValidationError("Username must be at least 3 characters".to_string()));
    }
    
    if username.len() > 50 {
        return Err(UserError::ValidationError("Username must be less than 50 characters".to_string()));
    }
    
    let username_regex = Regex::new(r"^[a-zA-Z0-9_]+$")
        .map_err(|_| UserError::ValidationError("Invalid username regex".to_string()))?;
    
    if !username_regex.is_match(username) {
        return Err(UserError::ValidationError("Username can only contain letters, numbers, and underscores".to_string()));
    }
    
    Ok(())
}

pub fn sanitize_string(input: &str) -> String {
    input.trim().to_string()
}