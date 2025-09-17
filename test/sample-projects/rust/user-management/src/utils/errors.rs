use thiserror::Error;

#[derive(Debug, Error)]
pub enum UserError {
    #[error("User not found: {0}")]
    UserNotFound(String),
    
    #[error("Duplicate user: {0}")]
    DuplicateUser(String),
    
    #[error("Validation error: {0}")]
    ValidationError(String),
    
    #[error("Database error: {0}")]
    DatabaseError(String),
}