use ferrum_service::helpers::auth::authorize;

#[test]
fn authorize_checks_roles() {
    assert!(authorize(&["admin", "user"], "admin"));
    assert!(!authorize(&["user"], "admin"));
}
