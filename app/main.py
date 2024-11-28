import subprocess
from views import entrypoint, core
from controllers.utils import inform, throw_action

if __name__ == "__main__":
    if throw_action("Do you agree on launching ScrutinPunchor ?"):
        try:
            result = subprocess.run(["python", "models/database.py"], capture_output=True, text=True, shell=True, check=True)

            entrypoint.show()
        except Exception as e:
            inform(e)