package main

// Contact holds contact information for a user.
type Contact struct {
	Email string
	Phone string
}

// User represents an application user.
type User struct {
	ID      int
	Name    string
	Contact *Contact
}

// GetEmail returns the user's email address.
func GetEmail(u *User) string {
	return u.Contact.Email
}

// GetName returns the user's display name.
func GetName(u *User) string {
	if u == nil {
		return ""
	}
	return u.Name
}
