package main

import (
	"net/http"

	"go-multi-add-http-middleware/middleware"
)

func NewServer() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	return middleware.RequestID(mux)
}

func main() {
	http.ListenAndServe(":8080", NewServer())
}
