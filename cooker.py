#!/usr/bin/env python3

"""The `cooker`. Launches OpenShift/Kubernetes Jobs and monitors their
life-cycle, recording those that launched successfully and those that
failed.
"""

import os
import time

from runner.runner import RunnerState, RunnerStateTuple
from runner.kubernetes_runner import KubernetesRunner

# Pull configuration from the environment.
NUM_JOBS = os.environ.get('COOKER_NUM_JOBS', '10')

# Number of runners...
_NUM_RUNNERS_TO_FINISH = 0
# Number of runners running..
_NUM_RUNNERS_RUNNING = 0
_NUM_FAILED = 0
_MAX_CONCURRENT = 0


def callback(state, context):
    """The Runner state callback method.

    :param state: The runner state
    :param context: The numeric ID applied to the runner
    """
    # pylint: disable=global-statement
    global _NUM_RUNNERS_TO_FINISH
    global _NUM_RUNNERS_RUNNING
    global _MAX_CONCURRENT
    global _NUM_FAILED

    assert isinstance(state, RunnerStateTuple)
    assert isinstance(context, object)

    # Set the `complete` flag if the Runner has ended...
    if state.state == RunnerState.END:
        _NUM_RUNNERS_TO_FINISH -= 1
        # Some runners may not get to a running state
        # Because we're handling callbacks for every Job
        if _NUM_RUNNERS_RUNNING > 0:
            _NUM_RUNNERS_RUNNING -= 1
    elif state.state == RunnerState.RUNNING:
        _NUM_RUNNERS_RUNNING += 1
    elif state.state == RunnerState.FAILED:
        _NUM_FAILED += 1

    if _NUM_RUNNERS_RUNNING > _MAX_CONCURRENT:
        _MAX_CONCURRENT = _NUM_RUNNERS_RUNNING

    if _NUM_RUNNERS_RUNNING > 0 or _NUM_RUNNERS_TO_FINISH == 0:
        print('Running=%s Failed=%s ToFinish=%s (context=%s)' %
              (_NUM_RUNNERS_RUNNING, _NUM_FAILED, _NUM_RUNNERS_TO_FINISH,
               context))


def main():
    """Cooker entry point.
    """
    # pylint: disable=global-statement
    global _NUM_RUNNERS_TO_FINISH

    print('Starting...')

    # Start Runners...
    _NUM_RUNNERS_TO_FINISH = int(NUM_JOBS)
    for runner_number in range(1, _NUM_RUNNERS_TO_FINISH + 1):

        print('Creating KubernetesRunner (%s)...' % runner_number)
        runner = KubernetesRunner(callback, runner_number)
        runner.begin()

    print('Waiting for runners to complete...')
    while _NUM_RUNNERS_TO_FINISH:
        time.sleep(4)

    print('MaxConcurrent=%s' % _MAX_CONCURRENT)
    print('Complete!')

    # If running from within Kubernetes (OpenSHift) - just park ourselves here.
    # It stops the replication controller starting us up again!
    if os.environ.get('KUBERNETES_SERVICE_HOST'):
        print("That's all Folks!")
        while True:
            time.sleep(4.0)


# -----------------------------------------------------------------------------
# Support execution as well as import
# -----------------------------------------------------------------------------
if __name__ == '__main__':

    main()
