# OpenAgri Evaluation Repository
🇪🇺 *"This service was created in the context of OpenAgri project (https://horizon-openagri.eu/). OpenAgri has received funding from the EU’s Horizon Europe research and innovation programme under Grant Agreement no. 101134083."*


A set of toolkits and to perform reproducible experiments and evaluations of the performance of the OpenAgri ecosystem of services.



## Prerequisites

Before you start, make sure Docker and Docker Compose are installed on your system.
Later versions of Docker also include now Docker Compose, but it is used as `docker compose` instead of `docker-compose`.

## Service Setup

### Setting up Configurations (.env file)
If you wish to start up this Farm Calendar service from this repository, you'll need to first copy the `.env.sample` file into a new file called `.env`, which will be the source of all configurations for this service, and its database.

In this new `.env` file you should change the configurations of the service to meet your deployment scenario. We strongly suggest changing configurations for the default usernames and passwords of the services used.

## Running
There is already a simple and ready to use `docker-compose.yml` file for your convinience. Nonetheless, you should be able to use the existing file as a base, and adapt it to your own deployment setup.

To run the service, execute the following command:
```
$ docker compose up -d
```

## Stopping/Restarting

To stop the service related containers, run:

```commandline
docker compose stop
```
And to start again the stopped containers:

```commandline
docker compose start
```

To stop and remove the containers, use:

```commandline
docker-compose down
```


# License
This project code is licensed under the Apache License Version 2.0, see the LICENSE file for more details.
Please note that each service may have different licenses, which can be found their specific source code repository.
