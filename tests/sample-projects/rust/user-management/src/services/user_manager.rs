use std::collections::HashMap;
use uuid::Uuid;
use crate::models::{User, UserRole, UserStatus};
use crate::utils::errors::UserError;
use crate::utils::validators::{validate_email, validate_username};

pub struct UserManager {
    users: HashMap<Uuid, User>,
    username_index: HashMap<String, Uuid>,
    email_index: HashMap<String, Uuid>,
}

impl UserManager {
    pub fn new() -> Self {
        Self {
            users: HashMap::new(),
            username_index: HashMap::new(),
            email_index: HashMap::new(),
        }
    }

    pub fn create_user(&mut self, username: String, email: String, 
                      first_name: String, last_name: String) -> Result<User, UserError> {
        validate_username(&username)?;
        validate_email(&email)?;

        if self.username_index.contains_key(&username) {
            return Err(UserError::DuplicateUser(format!("Username '{}' already exists", username)));
        }

        if self.email_index.contains_key(&email) {
            return Err(UserError::DuplicateUser(format!("Email '{}' already exists", email)));
        }

        let mut user = User::new(username, email, first_name, last_name);
        user.activate();

        let user_id = user.id;
        let username_clone = user.username.clone();
        let email_clone = user.email.clone();

        self.users.insert(user_id, user.clone());
        self.username_index.insert(username_clone, user_id);
        self.email_index.insert(email_clone, user_id);

        Ok(user)
    }

    pub fn get_user_by_id(&self, user_id: Uuid) -> Result<User, UserError> {
        self.users.get(&user_id)
            .cloned()
            .ok_or_else(|| UserError::UserNotFound(format!("User ID '{}' not found", user_id)))
    }

    pub fn get_user_by_username(&self, username: &str) -> Result<User, UserError> {
        let user_id = self.username_index.get(username)
            .ok_or_else(|| UserError::UserNotFound(format!("Username '{}' not found", username)))?;
        self.get_user_by_id(*user_id)
    }

    pub fn get_user_by_email(&self, email: &str) -> Result<User, UserError> {
        let user_id = self.email_index.get(email)
            .ok_or_else(|| UserError::UserNotFound(format!("Email '{}' not found", email)))?;
        self.get_user_by_id(*user_id)
    }

    pub fn update_user(&mut self, user_id: Uuid, first_name: Option<String>, 
                       last_name: Option<String>) -> Result<User, UserError> {
        let mut user = self.get_user_by_id(user_id)?;
        
        if let Some(fname) = first_name {
            user.first_name = fname;
        }
        
        if let Some(lname) = last_name {
            user.last_name = lname;
        }
        
        user.updated_at = chrono::Utc::now();
        
        self.users.insert(user_id, user.clone());
        Ok(user)
    }

    pub fn delete_user(&mut self, user_id: Uuid) -> Result<(), UserError> {
        let user = self.get_user_by_id(user_id)?;
        
        self.users.remove(&user_id);
        self.username_index.remove(&user.username);
        self.email_index.remove(&user.email);
        
        Ok(())
    }

    pub fn list_users(&self) -> Vec<User> {
        self.users.values().cloned().collect()
    }

    pub fn set_user_role(&mut self, user_id: Uuid, role: UserRole) -> Result<User, UserError> {
        let mut user = self.get_user_by_id(user_id)?;
        user.set_role(role);
        self.users.insert(user_id, user.clone());
        Ok(user)
    }

    pub fn activate_user(&mut self, user_id: Uuid) -> Result<User, UserError> {
        let mut user = self.get_user_by_id(user_id)?;
        user.activate();
        self.users.insert(user_id, user.clone());
        Ok(user)
    }

    pub fn deactivate_user(&mut self, user_id: Uuid) -> Result<User, UserError> {
        let mut user = self.get_user_by_id(user_id)?;
        user.deactivate();
        self.users.insert(user_id, user.clone());
        Ok(user)
    }

    pub fn get_active_users(&self) -> Vec<User> {
        self.users.values()
            .filter(|user| user.status == UserStatus::Active)
            .cloned()
            .collect()
    }

    pub fn get_users_by_role(&self, role: UserRole) -> Vec<User> {
        self.users.values()
            .filter(|user| user.role == role)
            .cloned()
            .collect()
    }
}