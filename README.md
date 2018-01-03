# PyKubePressureCooker
An experimental Python 3 module used to stress-test an OpenShift v3.6
[Kubernetes]-based container runtime environment. This module can be used
to launch a large number of concurrent [Jobs] based on a test image.

You will need:

-   A unix OS (sorry)
-   Python 3
-   An OpenShift cluster (i.e. [minishift]).
    Tested with minishift v1.10.0, OpenShift 3.6.0 and 3.7.0 using the command:
    
    `minishift start --cpus 4 --memory 8GB --disk-size 40GB
        --openshift-version 3.6.0 --vm-driver virtualbox`

## Background
The _pressure cooker_ has been designed to launch a test image in OpenShift
for the purposes of analysing OpenShift's behaviour when presented with
the concurrent execution of a large number of container images, CPU and
memory pressures and observe the OpenShift queue process and its reaction
to a Job that exceeds its defined CPU and memory limits.

The pressure cooker application and the test image can be found on the
Docker hub as:

-   `alanbchristie/pykubepressurecooker` (the main app)
-   `alanbchristie/pydatalister` (launched as child jobs)

>   The pressure cooker (and the pods it creates) is written in Python 3.

>   The pressure cooker can also be run from source on the command-line using
    its public GitHub repository. Instructions for running from the
    command-line and from within OpenShift can be found later in this README.

Using environment variables (from the command-line) or template parameters
(for an OpenShift application) the cooker allows you to set the number
of concurrently executing child Jobs. These jobs can be configured to run for
a period of time and also be configured to:

-   Burn-up the CPU with 1 or more processing threads (which is accomplished
    by calculating large factorials) and...
-   Consume memory

A simple way to exercise OpenShift's container-based queueing,
CPU and Memory limits.

>   _Out of the box_ the cooker creates 10 individual Jobs that run
    for two minutes before they exit cleanly. The default jobs do not burn the
    CPU and do not allocate additional memory beyond that required for them
    to start and stop. Essentially, running the cooker _as is_ 10 Jobs
    should be seen to start and two minutes later they should all complete.

## Application configuration
The cooker, which uses the [PyDataLister] container image,
can be configured with a number of environment variables or template
parameters. The default values are displayed in brackets:

-   `COOKER_BUSY_PERIOD`
    The period of time to burn the CPU, in seconds. The CPU stressing
    takes place after the defined pre-busy period (`0.0`). Using this value
    you can set the child containers to run for a fixed period of time.
    If you want to do a fixed amount of work use the `COOKER_BUSY_WORK`
    parameter.
-   `COOKER_BUSY_WORK`
    The amount of work to do in burning the CPU, in unit. The CPU stressing
    takes place after the defined pre-busy period (`0`). Using this value
    you can set the child containers to do a fixed amount of work (which is a
    a factorial of 150000). If you want to do burn the CPU for a fixed amount
    of time use the `COOKER_BUSY_PERIOD` parameter.
-   `COOKER_BUSY_PROCESSES`.
    The number of separate process threads to use to stress the CPU (`0`)
-   `COOKER_CPU_LIMIT`.
    The CPU limit for the Job container (`150m`)
-   `COOKER_CPU_REQUEST`
    The CPU request for the Job container (`150m`)
-   `COOKER_MEMORY_LIMIT`
    The Memory limit for the Job container(`10Mi`)
-   `COOKER_MEMORY_REQUEST`
    The Memory request for the Job container (`10Mi`)
-   `COOKER_NUM_PODS`
    The number of pods to launch (`10`)
-   `COOKER_PRE_BUSY_SLEEP_S`
    The period of time, in seconds, after launching the Job to pause before
    looking busy or consuming memory (`120.0`)
-   `COOKER_USE_MEMORY_M`
    The approximate amount of memory (in megabytes) to consume after
    the pre-busy sleep period (`0`)

## Running (from the command-line)
You can run the _cooker_ from the command-line and it will interact with the
OpenShift/Kubernetes API using the client API.

You will need Python 3 (ideally from within a [virtualenv]) and will need
to install the requirements (dependent Python modules):

    $ pip install -r requirements.txt

If running with minishift, make sure it's running and you have created the
cooker project (`pressure-pot`) and have logged in as a suitable user using
the OpenShift console commands...

    $ eval $(minishift oc-env)
    $ oc login -u admin
      ...
    $ oc new-project pressure-pot
    
Then, run the pressure cooker using the default values...

    $ ./cooker.py
    
>   Alternatively you can copy the environment setup example file
    and change the values to suit your needs...
    
    $ cp setenv-example.sh setenv.sh
    $ source setenv.sh
    $ ./cooker.py

## Running (as a container in OpenShift)
You can run the cooker from within a container in OpenShift using the
template in this project's `openshift` directory, which uses the cooker
image on Docker hub (`alanbchristie/pykubepressurecooker`).

The cooker then spawns multiple jobs from within the OpenShift
environment.

You can define the behaviour of the spawned `PyDataLister` jobs using the
parameters exposed in the template.

To run the cooker you need to give `cluster-admin` to the `default` service
account, this is because you need to allow the cooker's container to
create Jobs.

To do this run the following commands to setup your minishift instance...

    $ eval $(minishift oc-env)
    $ oc login -u admin
      ...
    $ oc new-project pressure-pot
    $ oc login -u system:admin
    $ oc adm policy add-cluster-role-to-user cluster-admin -z default

Then, you can launch the cooker with the following:

    $ oc process -f openshift/cooker.yml | oc create -f -

And delete it with:

    $ oc delete all --selector template=pressure-cooker

---

[Kubernetes]: https://kubernetes.io
[minishift]: https://github.com/minishift/minishift
[Jobs]: https://docs.openshift.org/3.6/dev_guide/jobs.html
[PyDataLister]: https://hub.docker.com/r/alanbchristie/pydatalister/
[VirtualEnv]: https://virtualenvwrapper.readthedocs.io/en/latest/

_Alan B. Christie  
January 2018_
