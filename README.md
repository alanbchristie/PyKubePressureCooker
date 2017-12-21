# PyKubePressureCooker
An experimental Python 3 module used to stress-test an OpenShift v3.6
[Kubernetes]-based container runtime environment. This module can be used
to launch a large number of concurrent [Jobs] based on a test image.

You will need:

-   A unix OS (sorry)
-   Python 3
-   An OpenShift cluster (i.e. [minishift]).
    Tested with minishift v1.10.0 and OpenShift 3.6.0 and
    OpenShift 3.7.0 using the command:
    
    `minishift start --cpus 4 --memory 8GB --disk-size 40GB
        --openshift-version 3.6.0 --vm-driver virtualbox`

## Application configuration
The application, which uses the [PyDataLister] container image,
can be configured with a number of environment variables,
(with default values being used if not specified):

-   `COOKER_BUSY_PERIOD`
    The period of time to burn the CPU, in seconds. The CPU stressing
    takes place after the defined pre-busy period (`0.0`)
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
You can run the application from within a container in OpenShift using the
template in this project's `openshift` directory, which uses the application
image on Docker hub (`alanbchristie/pykubepressurecooker`).

The application then spawns multiple jobs from within the OpenShift
environment.

You can define the behaviour of the spawned `PyDataLister` jobs using the
parameters exposed in the template.

To run the app within OpenShift (this example uses minishift) you need
To give cluster-admin to the default service account, this is because you
need to allow the application container to create Pods.

To do this run the following command as the `system:admin` user
in the `pressure-pot` project...

    $ eval $(minishift oc-env)
    $ oc login -u admin
      ...
    $ oc new-project pressure-pot
    $ oc login -u system:admin
    $ oc adm policy add-cluster-role-to-user cluster-admin -z default

Then, you can launch the container application with the following:

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
December 2017_
