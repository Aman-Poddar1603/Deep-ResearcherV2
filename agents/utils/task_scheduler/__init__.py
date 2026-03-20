"""
## Description

Initializes the task scheduler module. Exposes a pre-configured, global
`Scheduler` instance to be used across the application for background task
management and worker queueing.

## Parameters

- None (Module level initialization)

## Returns

`None`

## Raises

- None

## Side Effects

- Instantiates a global `Scheduler` object with 4 default workers.
- Sets up the underlying `TaskQueue` ready for global application usage.

## Debug Notes

- Import this `scheduler` instance directly to enqueue tasks from anywhere in the backend.
- Ensure `scheduler.start()` is explicitly called during the application startup phase.

## Customization

- Modify the `workers=4` argument here to scale the default concurrent background task capacity globally.
"""

from utils.task_scheduler.scheduler import Scheduler

scheduler: Scheduler = Scheduler(workers=4)
