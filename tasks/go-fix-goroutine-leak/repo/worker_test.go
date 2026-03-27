package main

import (
	"runtime"
	"testing"
	"time"
)

func TestWorkerProcessesJobs(t *testing.T) {
	w := NewWorker()
	w.Submit("job1")
	w.Submit("job2")
	w.Stop()
}

func TestWorkerNoLeak(t *testing.T) {
	before := runtime.NumGoroutine()
	w := NewWorker()
	w.Submit("a")
	w.Submit("b")
	w.Stop()

	// Give goroutine time to exit
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		time.Sleep(10 * time.Millisecond)
		if runtime.NumGoroutine() <= before {
			return
		}
	}
	after := runtime.NumGoroutine()
	if after > before {
		t.Errorf("goroutine leak: started with %d, ended with %d", before, after)
	}
}
