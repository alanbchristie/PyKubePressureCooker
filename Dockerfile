# Use an official Python runtime as a parent image
FROM python:3.6.4-slim

# Force the binary layer of the stdout and stderr streams to be unbuffered
ENV PYTHONUNBUFFERED 1

# Base directory for the application
# Also used for user directory
ENV APP_ROOT /home/cooker

# Containers should NOT run as root
# (as good practice)
RUN useradd -c 'Container user' -m -d ${APP_ROOT} -s /bin/bash cooker
WORKDIR ${APP_ROOT}

# Copy the current directory contents into the container at APP_ROOT
COPY cooker.py ${APP_ROOT}
COPY runner ${APP_ROOT}/runner/
COPY requirements.txt ${APP_ROOT}
RUN chown -R cooker.cooker ${APP_ROOT}

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

USER cooker
ENV HOME ${APP_ROOT}

# Run app.py when the container launches.
# Need a full path for OpenShift environment.
CMD ["python", "/home/cooker/cooker.py"]
