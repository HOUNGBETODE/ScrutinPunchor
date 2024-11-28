# ScrutinPunchor
This is about an HIDS acting as a malicious file detector and a folder monitorer

## How to use the tool ?

Before doing anything, you need to configure :
- a custom `env.ini` file for app folder
- a custom `.env` file for worker folder

### For GUI environment
- go to `app` folder
- create a python environment using `python3 -m venv env`
- activate that virtual environment
- install prerequisites by running `pip -r intall requiremnts.txt`
- after that, run `python3 main.py` and follow the steps

### For CLI environment
rabbitmq - django backend (producer) - slack - tool on userside (consumer)
#### First thing to do
- go to `app` folder
- create a python environment using `python3 -m venv env`
- activate that virtual environment
- install prerequisites by running `pip -r intall requiremnts.txt`
- after that, run `python3 main.py` and follow the steps
- create a user account and got `id` and `pseudo` in mind
- then follow steps

#### Second thing to do in case you wanna exploit GUARDIAN 
- open another terminal
- go to `app` folder
- run `python3 consumer.py` to start the worker

#### Third thing to do
- go to `worker` folder
- run `python3 manage.py runserver 0.0.0.0:8000` to launch the service
