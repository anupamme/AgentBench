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
	for {
		select {
		case job, ok := <-w.jobs:
			if !ok {
				return
			}
			_ = job
			time.Sleep(time.Millisecond)
		case <-w.done:
			return
		}
	}
}

// Submit sends a job to the worker.
func (w *Worker) Submit(job string) {
	w.jobs <- job
}

// Stop signals the worker to stop.
func (w *Worker) Stop() {
	close(w.done)
}
