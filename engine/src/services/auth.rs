/// Simple authorization helpers.

/// Returns true if the provided `required_role` exists in `user_roles`.
pub fn authorize(user_roles: &[&str], required_role: &str) -> bool {
    user_roles.iter().any(|r| *r == required_role)
}
