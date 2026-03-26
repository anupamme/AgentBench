package main

import (
	"errors"
	"fmt"
)

var ErrNotFound = errors.New("not found")

type User struct {
	ID   int
	Name string
}

var db = map[int]User{
	1: {ID: 1, Name: "Alice"},
}

// FindUser looks up a user by ID.
func FindUser(id int) (User, error) {
	u, ok := db[id]
	if !ok {
		// Bug: uses %v instead of %w, so errors.Is cannot unwrap this error
		return User{}, fmt.Errorf("user %d: %v", id, ErrNotFound)
	}
	return u, nil
}
