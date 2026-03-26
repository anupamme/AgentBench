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

/// Find a user by ID, panicking if not found.
pub fn find_user(id: u32) -> User {
    let (name, found_id) = USERS.iter().find(|(_, uid)| *uid == id).unwrap();
    User { id: found_id.clone(), name: name.to_string() }
}
