package main

import "errors"

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
		return User{}, ErrNotFound
	}
	return u, nil
}
