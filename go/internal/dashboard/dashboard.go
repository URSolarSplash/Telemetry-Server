// Package dashboard ports server/dashboard.py: a static file server (the
// working directory, like Python's SimpleHTTPRequestHandler) with CORS
// enabled, used to serve the web dashboard.
package dashboard

import (
	"context"
	"fmt"
	"net/http"

	"telemetryserver/internal/config"
)

// Manager runs the dashboard HTTP server in the background.
type Manager struct {
	server *http.Server
}

// NewManager starts serving the given root directory on config.DashboardHTTPPort.
func NewManager(rootDir string) *Manager {
	fmt.Println("[Dashboard] initializing dashboard HTTP server...")
	files := http.FileServer(http.Dir(rootDir))
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		files.ServeHTTP(w, r)
	})
	m := &Manager{
		server: &http.Server{
			Addr:    fmt.Sprintf(":%d", config.DashboardHTTPPort),
			Handler: handler,
		},
	}
	go func() {
		if err := m.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			fmt.Println("[Dashboard] server error:", err)
		}
	}()
	return m
}

// Shutdown stops the dashboard server.
func (m *Manager) Shutdown() {
	m.server.Shutdown(context.Background())
}
