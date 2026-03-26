package middleware

import (
	"fmt"
	"math/rand"
	"net/http"
)

func RequestID(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		id := fmt.Sprintf("%08x", rand.Uint32())
		w.Header().Set("X-Request-ID", id)
		next.ServeHTTP(w, r)
	})
}
