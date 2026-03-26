use rust_add_option_handling::find_user;

#[test]
fn test_find_existing_user() {
    let user = find_user(1).expect("user 1 should exist");
    assert_eq!(user.name, "Alice");
}

#[test]
fn test_find_missing_user() {
    let result = find_user(999);
    assert!(result.is_none(), "expected None for missing user");
}
