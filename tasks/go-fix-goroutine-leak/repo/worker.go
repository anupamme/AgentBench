package main

import "time"

// Worker processes jobs from a channel.
type Worker struct {
	jobs chan string
	done chan struct{}
}

// NewWorker creates and starts a new Worker.
func NewWorker() *Worker {
	w := &Worker{
		jobs: make(chan string, 10),
		done: make(chan struct{}),
	}
	go w.run()
	return w
}

func (w *Worker) run() {
	for job := range w.jobs {
		_ = job // simulate work
		time.Sleep(time.Millisecond)
	}
}

// Submit sends a job to the worker.
func (w *Worker) Submit(job string) {
	w.jobs <- job
}

// Stop signals the worker to stop (currently broken — goroutine leaks).
func (w *Worker) Stop() {
	close(w.done)
}
