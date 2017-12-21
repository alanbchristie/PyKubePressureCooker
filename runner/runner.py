#!/usr/bin/env python3

"""An abstract _Runner_ module.
"""

from abc import ABCMeta, abstractmethod
from collections import namedtuple
from enum import Enum, auto, unique
import threading
import uuid

RUNNER_IMAGE = 'alanbchristie/pydatalister'
RUNNER_TAG = 'latest'


@unique
class RunnerState(Enum):
    """Runner execution states.
    """

    # The first event is always BEGIN.
    # The last and final event is always END.
    #
    # The normal event sequence, which relates to a runner
    # that's successfully created, runs, completes and is then
    # automatically deleted is represented by the following sequence:
    #
    # BEGIN - PREPARING - RUNNING - COMPLETE - END

    BEGIN = auto()          # The Runner initial state (assigned in begin())
    PREPARING = auto()      # The Runner is preparing to run
    RUNNING = auto()        # The Runner is Running
    COMPLETE = auto()       # The Runner has completed its actions (naturally)
    STOPPING = auto()       # The Runner is stopping - in response to a stop()
    STOPPED = auto()        # The runner has stopped - in response to a stop()
    FAILED = auto()         # There has been a problem
    END = auto()            # The last event, issued when the runner's gone


RunnerStateTuple = namedtuple('Runner', ['state', 'context', 'msg'])


class Runner(threading.Thread, metaclass=ABCMeta):
    """The ``Runner`` base class, from which all Runners are derived.
    """

    def __init__(self, callback, callback_context):
        """The basic Runner initialser.
        """
        threading.Thread.__init__(self)

        assert callable(callback)

        self._state_callback = callback
        self._callback_context = callback_context
        self._runner_state = None
        self._stopping = False
        self._runner_uuid = uuid.uuid4()

        # A synchronisation lock
        self.lock = threading.Lock()

        print('New Runner() {%s}' % self._runner_uuid)

    def _set_runner_state(self, runner_state, msg=None):
        """Sets the runner state and informs the user.

        :param runner_state: The new Runner state
        :type runner_state: ``RunnerState
        """
        assert isinstance(runner_state, RunnerState)
        self._runner_state = runner_state

        print('New RunnerState (%s) {%s}' % (runner_state, self._runner_uuid))

        # Inform the user of each state change.
        # The receiver must expect a `RunnerStateTuple` as the first argument
        # in the callback method.
        assert self._state_callback
        rso = RunnerStateTuple(runner_state, self._callback_context, msg)
        self._state_callback(rso, self._callback_context)

    @abstractmethod
    def begin(self):
        """Starts the Runner. The state_callback will be supplied with
        instances of the RunnerState as the runner progresses. This
        method must only be called once.

        This method must not block.

        """
        assert self._runner_state is None
        self._set_runner_state(RunnerState.BEGIN)

    def end(self):
        """Stops the Runner. This method should be called only of a Runner is
        to be prematurely stopped. Runners have a built-in lifetime and are
        normally left to complete naturally.

        If the Runner is still running this method introduces the
        ``RunnerState`` values of ``STOPPING`` and ``STOPPED``, normally not
        seen.

        This method does nothing if the Runner is already stopping or has
        completed.

        This method must not block.
        """
        print('End called... {%s}' % self._runner_uuid)

        if self._stopping:
            print('Ignoring (already in progress). {%s}' %
                  self._runner_uuid)
            return
        elif self._runner_state in [RunnerState.COMPLETE,
                                    RunnerState.END]:
            print('Ignoring (Runner already gone). {%s}' %
                  self._runner_uuid)
            return

        self._set_runner_state(RunnerState.STOPPING)
        # Just set the 'stopping' field (and change the state).
        # This should cause the main thread to exit - it's
        # the responsibility of the implementing class.
        self._stopping = True

        print('End is nigh! {%s}' % self._runner_uuid)
