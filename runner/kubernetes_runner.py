#!/usr/bin/env python3

"""The Kubernetes-based Job module.

>   This module relies on the `default` service account in the cluster
    and for that account to hold the `cluster-admin` _role_.
    See `open-shift/manager.yml` for instructions.
"""

import logging
import os
import time
import urllib3

from kubernetes import client, config
import yaml

from runner.runner import Runner, RunnerState
from runner.runner import RUNNER_IMAGE, RUNNER_TAG

_LOGGER = logging.getLogger(__name__)

# Retrieve configuration from the environment, using defaults if needed.
BUSY_PERIOD = float(os.environ.get('COOKER_BUSY_PERIOD', '0.0'))
BUSY_PROCESSES = int(os.environ.get('COOKER_BUSY_PROCESSES', '0'))
CPU_LIMIT = os.environ.get('COOKER_CPU_LIMIT', '150m')
CPU_REQUEST = os.environ.get('COOKER_CPU_REQUEST', '150m')
MEMORY_LIMIT = os.environ.get('COOKER_MEMORY_LIMIT', '10Mi')
MEMORY_REQUEST = os.environ.get('COOKER_MEMORY_REQUEST', '10Mi')
PRE_BUSY_SLEEP_S = float(os.environ.get('COOKER_PRE_BUSY_SLEEP_S', '120.0'))
USE_MEMORY_M = int(os.environ.get('COOKER_USE_MEMORY_M', '0'))

_NAMESPACE = 'pressure-pot'
_POLL_PERIOD_S = 6

# Kubernetes configuration.
# Try the in-cluster configuration
# (this should work if we're inside the cluster)
# then (if unsuccessful) try the kube configuration
# (which uses .kube/config).
_CONFIGURATION = None
try:
    config.load_incluster_config()
    _CONFIGURATION = 'InCluster'
except config.config_exception.ConfigException:
    try:
        config.load_kube_config()
        _CONFIGURATION = 'Kube'
    except FileNotFoundError:
        pass

if _CONFIGURATION:
    # Create API objects
    # These will only be used if the configuration has been successful.
    _CORE_API = client.CoreV1Api()
    _BATCH_API = client.BatchV1Api()


class KubernetesRunner(Runner):
    """A Runner that instantiates an instance of the defined
    container image in a Kubernetes environment. You should create and `begin`
    one of these for each Runner. It runs as a separate thread and the
    callback function you supply will be given progress notifications.
    """

    def __init__(self, callback, callback_context):
        """Standard initialiser. Supplied with a callback function.
        The callback function should not block and should complete quickly.

        :param callback_context: An optional context, passed to the callback
        :type callback_context: ``Object``
        """
        super().__init__(callback, callback_context)

        _LOGGER.debug('Initialising (configuration=%s)', _CONFIGURATION)

        self._job_name = None
        self._pod_name = None

        self._job_created = False
        self._service_created = False

    def begin(self):
        """Starts the runner.
        """

        super().begin()

        self._job_name = 'cooker-job-%s' % self._runner_uuid

        # We're a thread - start our run() method
        self.start()

    def _create_job(self):
        """Tries to create the Job.

        :returns: True on success
        :rtype: ``bool``
        """
        image_fq_name = '%s:%s' % (RUNNER_IMAGE, RUNNER_TAG)
        _LOGGER.debug('Creating Job for image %s (%s)...',
                      image_fq_name, self._job_name)

        job_string = """
        kind: Job
        apiVersion: batch/v1
        metadata:
          name: {name}
        spec:
          template:
            metadata:
              name: {name}
            spec:
              containers:
              - name: {name}
                image: {image}
                env:
                - name: PRE_LIST_SLEEP
                  value: "0"
                - name: POST_LIST_SLEEP
                  value: "{sleep}"
                - name: POST_SLEEP_BUSY_PERIOD
                  value: "{busy}"
                - name: BUSY_PROCESSES
                  value: "{processes}"
                - name: USE_MEMORY_M
                  value: "{memory}"
              resources:
                limits:
                  cpu: {c_limit}
                  memory: {m_limit}
                requests:
                  cpu: {c_request}
                  memory: {m_request}
              imagePullPolicy: IfNotPresent
              restartPolicy: Never
              backOffLimit: 0
        """.format(name=self._job_name, image=image_fq_name,
                   sleep=PRE_BUSY_SLEEP_S, busy=BUSY_PERIOD,
                   processes=BUSY_PROCESSES, memory=USE_MEMORY_M,
                   c_limit=CPU_LIMIT, c_request=CPU_REQUEST,
                   m_limit=MEMORY_LIMIT, m_request=MEMORY_REQUEST)

        job_payload = yaml.load(job_string)

        try:
            _BATCH_API.create_namespaced_job(body=job_payload,
                                             namespace=_NAMESPACE)
            self._job_created = True
        except client.rest.ApiException as api_ex:
            _LOGGER.exception(api_ex)
        except urllib3.exceptions.MaxRetryError:
            _LOGGER.error("MaxRetryError with Job (%s)", self._job_name)
        except urllib3.exceptions.ProtocolError:
            _LOGGER.error("ProtocolError with Job (%s)", self._job_name)

        if self._job_created:
            _LOGGER.debug('Created Job (%s)', self._job_name)
        else:
            _LOGGER.error('Failed creating Job (%s)', self._job_name)

        return self._job_created

    def _kill_job(self):
        """Destroys the Job (if it exists).
        """
        if not self._job_created:
            return

        # Delete the Job
        body = client.V1DeleteOptions()
        body.grace_period_seconds = 0
        try:
            _BATCH_API.delete_namespaced_job(name=self._job_name,
                                             namespace=_NAMESPACE,
                                             body=body)
        except urllib3.exceptions.MaxRetryError as url_e:
            _LOGGER.warning('MaxRetryError deleting Job (%s) reason=%s',
                            self._job_name, url_e.reason)

        # Delete the Pod
        # (created by Kubernetes to shadow the Job)
        try:
            _CORE_API.delete_namespaced_pod(name=self._pod_name,
                                            namespace=_NAMESPACE,
                                            body=body)
        except client.rest.ApiException as api_e:
            _LOGGER.warning("Failed to delete Job's Pod (%s) ApiException=%s",
                            self._job_name, api_e)

    def _wait_for_job_running(self):
        """Wait for job running (whether successful or not).
        """
        _LOGGER.debug('Waiting for Job running (%s)...', self._job_name)

        running = False
        while not running:

            api_response = None
            try:
                api_response = _CORE_API.\
                    list_namespaced_pod(namespace=_NAMESPACE,
                                        label_selector="job-name={name}"
                                        .format(name=self._job_name))
            except client.rest.ApiException:
                _LOGGER.debug('Failed to get API response. Server busy?')
            except urllib3.exceptions.MaxRetryError:
                _LOGGER.debug("MaxRetryError. Server busy?")

            if api_response and api_response.items:
                status = api_response.items[0].status.phase
                if status in ['Running', 'Succeeded', 'Failed', 'Unknown']:
                    running = True
                    self._pod_name = api_response.items[0].metadata.name

            if not running:
                time.sleep(_POLL_PERIOD_S)

        _LOGGER.debug('Job running (%s).', self._job_name)

    def _wait_for_job_complete(self):
        """Wait for job completion (whether successful or not).

        :returns: True is completed successfully.
        """
        _LOGGER.debug('Waiting for Job complete (%s)...', self._job_name)

        complete = False
        status = None
        while not complete:

            api_response = None
            try:
                api_response = _CORE_API.\
                    list_namespaced_pod(namespace=_NAMESPACE,
                                        label_selector="job-name={name}"
                                        .format(name=self._job_name))
            except client.rest.ApiException:
                _LOGGER.debug('Failed to get API response. Server Busy?')
            except urllib3.exceptions.MaxRetryError:
                _LOGGER.debug("MaxRetryError. Server busy?")

            if api_response and api_response.items:
                status = api_response.items[0].status.phase
                if status in ['Succeeded', 'Failed', 'Unknown']:
                    complete = True

            if not complete:
                time.sleep(_POLL_PERIOD_S)

        _LOGGER.debug('Job complete (%s).', self._job_name)

        return status in ['Succeeded', 'Unknown']

    def run(self):
        """The Thread run() method.
        """
        _LOGGER.debug('Entering run()...')

        # First step ... PREPARING
        self._set_runner_state(RunnerState.PREPARING)

        if not _CONFIGURATION or not self._create_job():
            _LOGGER.error('Failed to create Job %s', self._callback_context)
            self._set_runner_state(RunnerState.FAILED)
            self._set_runner_state(RunnerState.END)
            return

        # Wait for running...
        _LOGGER.info('Job %s has been created.', self._callback_context)
        self._wait_for_job_running()
        self._set_runner_state(RunnerState.RUNNING)

        # Wait for completion...
        _LOGGER.info('Job %s is now running.', self._callback_context)
        success = self._wait_for_job_complete()

        # If stopping do not replace with COMPLETE.
        if self._stopping:
            self._set_runner_state(RunnerState.STOPPED)
        else:
            if success:
                self._set_runner_state(RunnerState.COMPLETE)
            else:
                self._set_runner_state(RunnerState.FAILED)

        # Complete or stopped.
        # Destroy the Job.
        self._kill_job()

        # Final state... End
        self._set_runner_state(RunnerState.END)

        _LOGGER.debug('Left run().')
