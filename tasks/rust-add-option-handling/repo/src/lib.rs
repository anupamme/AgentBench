#[derive(Debug, PartialEq)]
pub struct User {
    pub id: u32,
    pub name: String,
}

static USERS: &[(&str, u32)] = &[
    ("Alice", 1),
    ("Bob", 2),
    ("Carol", 3),
];

/// Find a user by ID. Returns None if not found.
pub fn find_user(id: u32) -> Option<User> {
    // Bug: unwrap() panics on missing user instead of returning None
    let (name, found_id) = USERS.iter().find(|(_, uid)| *uid == id).unwrap();
    Some(User { id: *found_id, name: name.to_string() })
}
