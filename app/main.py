import subprocess
from views import entrypoint, core
from controllers.utils import inform, throw_action

if __name__ == "__main__":
    # if throw_action("Do you agree on launching ScrutinPunchor ?"):
        try:
            # init database
            result = subprocess.run(["python", "models/database.py"], capture_output=True, text=True, shell=True, check=True)

            # load the app
            # entrypoint.show()
            core.show(1, "user", "moberenge@gmail.com")
        except Exception as e:
            inform(e)














# core.show(1, "ami", "moberenge@gmail.com")

# from controllers.utils import get_or_create, from_SP, setPact
# from models.database import Log, LogEvent

# print(from_SP(
#     event = LogEvent.MODIFIED, 
#     file_type = "file", 
#     source = "G:/folder1/eat", 
#     user_id = 1,
# ))

# setPact(
#     event = LogEvent.MODIFIED, 
#     file_type = "file", 
#     source = "G:/folder1/eat", 
#     user_id = 1,
#     from_sp = True
# )

# print(get_or_create(
#     Log, 
#     event = LogEvent.MODIFIED, 
#     file_type = "file", 
#     source = "G:/folder1/eat", 
#     user_id = 1
# ))
