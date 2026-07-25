//! Generic worker-thread abstraction for subprocess execution.
//!
//! This module provides a safe, non-blocking way to run external commands
//! from the GUI without freezing the UI. It uses structured command arguments
//! (no shell-string concatenation) and supports cancellation.

use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::{self, Receiver, Sender, TryRecvError};
use std::sync::Arc;
use std::thread::{self, JoinHandle};

// ---------------------------------------------------------------------------
// Worker messages
// ---------------------------------------------------------------------------

/// Messages sent from the worker thread to the GUI thread.
#[derive(Debug, Clone)]
pub enum WorkerMessage {
    /// A line of stdout output.
    StdoutLine(String),
    /// A line of stderr output.
    StderrLine(String),
    /// Progress update text.
    Progress(String),
    /// The process completed successfully with an exit code.
    Completed(i32),
    /// The process failed to start or was killed.
    Failed(String),
}

// ---------------------------------------------------------------------------
// Worker handle
// ---------------------------------------------------------------------------

/// Handle to a running worker thread. The GUI polls this for updates.
pub struct WorkerHandle {
    receiver: Receiver<WorkerMessage>,
    cancel_flag: Arc<AtomicBool>,
    _thread: JoinHandle<()>,
}

impl WorkerHandle {
    /// Poll for new messages without blocking.
    pub fn try_recv(&self) -> Option<WorkerMessage> {
        match self.receiver.try_recv() {
            Ok(msg) => Some(msg),
            Err(TryRecvError::Empty | TryRecvError::Disconnected) => None,
        }
    }

    /// Drain all pending messages.
    pub fn drain(&self) -> Vec<WorkerMessage> {
        let mut messages = Vec::new();
        loop {
            match self.receiver.try_recv() {
                Ok(msg) => messages.push(msg),
                Err(_) => break,
            }
        }
        messages
    }

    /// Request cancellation.
    pub fn cancel(&self) {
        self.cancel_flag.store(true, Ordering::Release);
    }

    /// Check if cancellation was requested.
    #[must_use]
    pub fn is_cancelled(&self) -> bool {
        self.cancel_flag.load(Ordering::Acquire)
    }
}

// ---------------------------------------------------------------------------
// Launching workers
// ---------------------------------------------------------------------------

/// Spawn a subprocess using structured arguments and return a handle.
///
/// # Arguments
/// * `program` — The executable path.
/// * `args` — Structured command-line arguments (not concatenated as a shell string).
/// * `cancel_flag` — Shared cancellation flag.
///
/// The worker thread reads stdout and stderr line-by-line, forwarding them
/// as `WorkerMessage` variants. When the process exits, a final `Completed`
/// or `Failed` message is sent.
pub fn spawn_subprocess(
    program: &str,
    args: &[String],
    cancel_flag: Arc<AtomicBool>,
) -> WorkerHandle {
    let (sender, receiver) = mpsc::channel();
    let program = program.to_string();
    let args: Vec<String> = args.to_vec();
    let flag = Arc::clone(&cancel_flag);

    let thread = thread::spawn(move || {
        run_subprocess(&program, &args, &sender, &flag);
    });

    WorkerHandle {
        receiver,
        cancel_flag,
        _thread: thread,
    }
}

/// Internal: run the subprocess, capturing output and checking cancellation.
fn run_subprocess(
    program: &str,
    args: &[String],
    sender: &Sender<WorkerMessage>,
    cancel_flag: &Arc<AtomicBool>,
) {
    let child_result = Command::new(program)
        .args(args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn();

    let mut child: Child = match child_result {
        Ok(c) => c,
        Err(e) => {
            let _ = sender.send(WorkerMessage::Failed(format!(
                "Failed to start '{}': {}",
                program, e
            )));
            return;
        }
    };

    let _ = sender.send(WorkerMessage::Progress("Process started...".to_string()));

    // Read stdout in a separate thread.
    let stdout_sender = sender.clone();
    let stdout = child.stdout.take();
    let stdout_thread = thread::spawn(move || {
        if let Some(pipe) = stdout {
            let reader = BufReader::new(pipe);
            for line in reader.lines().flatten() {
                if stdout_sender.send(WorkerMessage::StdoutLine(line)).is_err() {
                    break;
                }
            }
        }
    });

    // Read stderr in a separate thread.
    let stderr_sender = sender.clone();
    let stderr = child.stderr.take();
    let stderr_thread = thread::spawn(move || {
        if let Some(pipe) = stderr {
            let reader = BufReader::new(pipe);
            for line in reader.lines().flatten() {
                if stderr_sender.send(WorkerMessage::StderrLine(line)).is_err() {
                    break;
                }
            }
        }
    });

    // Wait for the process, checking cancellation.
    loop {
        if cancel_flag.load(Ordering::Acquire) {
            let _ = child.kill();
            let _ = child.wait();
            let _ = sender.send(WorkerMessage::Failed("Process cancelled by user".to_string()));
            break;
        }

        match child.try_wait() {
            Ok(Some(status)) => {
                let _ = stdout_thread.join();
                let _ = stderr_thread.join();
                let code = status.code().unwrap_or(-1);
                if status.success() {
                    let _ = sender.send(WorkerMessage::Completed(code));
                } else {
                    let _ = sender.send(WorkerMessage::Failed(format!(
                        "Process exited with code {}",
                        code
                    )));
                }
                break;
            }
            Ok(None) => {
                // Still running, sleep briefly.
                thread::sleep(std::time::Duration::from_millis(50));
            }
            Err(e) => {
                let _ = sender.send(WorkerMessage::Failed(format!(
                    "Error waiting for process: {}",
                    e
                )));
                break;
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Spawn a closure as a worker (for in-process calculations)
// ---------------------------------------------------------------------------

/// Spawn a closure on a background thread, sending progress updates.
pub fn spawn_task<F>(cancel_flag: Arc<AtomicBool>, task: F) -> WorkerHandle
where
    F: FnOnce(Sender<WorkerMessage>, Arc<AtomicBool>) + Send + 'static,
{
    let (sender, receiver) = mpsc::channel();
    let flag = Arc::clone(&cancel_flag);

    let thread = thread::spawn(move || {
        task(sender, flag);
    });

    WorkerHandle {
        receiver,
        cancel_flag,
        _thread: thread,
    }
}
