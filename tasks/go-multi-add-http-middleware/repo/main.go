package main

import "net/http"

func NewServer() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	return mux
}

func main() {
	http.ListenAndServe(":8080", NewServer())
}
