from config import CRYPT
from email import encoders
from email.mime.base import MIMEBase
from models.database import LogEvent
from email.mime.text import MIMEText
from cryptography.fernet import Fernet
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import base64, io, json, jwt, os, random, smtplib, sys


def obfuscate_data(data, pseudo_queue):
    CRYPTO_PARAMS = CRYPT.load()
    # print(data)
    # print(json.dumps(data))
    crypted_data = Fernet(CRYPTO_PARAMS["symk"].encode()).encrypt(json.dumps(data).encode()).decode()
    tokenized_data = jwt.encode(
        {"body": crypted_data, "pseudo_queue": pseudo_queue}, 
        CRYPTO_PARAMS["jwtk"], 
        algorithm='HS256'
    ).encode().hex()
    # print(tokenized_data)
    tokenized_data_length = len(tokenized_data)
    random_seed = random.choice(list(range(tokenized_data_length)))
    tokenized_data_shuffled = tokenized_data[random_seed:] + tokenized_data[:random_seed]
    return f"{int(tokenized_data_shuffled, 16)}.{random_seed}"

def export_to_buffer(file_path):
    with open(file_path, 'rb') as file:
        buffer = io.StringIO(file.read())
    return buffer.getvalue()
# attachment = MIMEApplication(export_to_buffer(message_body[filename]))

def send_mail(receiver_mail, message_subject, message_type, message_body):
    gmail = Email.load()
    # defining the mail headers
    multipart = MIMEMultipart()
    multipart['Subject'] = message_subject
    multipart['From'] = gmail['user']
    multipart['To'] = receiver_mail
    # attaching content inside mail's body according to message_type
    match message_type:
        case "CODE":
            template = r"notifications\template.html"
            with open(template, 'r', encoding="utf-8") as f:
                temp = f.read()
            temp = temp.replace("{{ full_name }}", 
                                message_body['name']
                            ).replace("{{ otp_code }}", 
                                message_body['code']
                        )
            multipart.attach(MIMEText(temp, 'html'))
        case "REPORT":
            for filename in message_body:
                attachment = MIMEBase("application", "octet-stream")
                with open(message_body[filename], "rb") as file:
                    attachment.set_payload(file.read())
                    encoders.encode_base64(attachment)
                    attachment.add_header('Content-Disposition', f"attachment; filename= {filename}")
                    multipart.attach(attachment)
        case "AWARENESS":
            template = r"notifications\confirm.html"
            with open(template, 'r', encoding="utf-8") as f:
                temp = f.read()
            temp = temp.replace("{{ pseudo }}", 
                                message_body['pseudo']
                            ).replace("{{ sys-event }}", 
                                message_body['event']
                            ).replace("{{ data-link }}", 
                                message_body['data']
                        )
            multipart.attach(MIMEText(temp, 'html'))
        case _:
            return None
    # connecting to the SMTP server with an email and password
    server = smtplib.SMTP_SSL('smtp.gmail.com')
    server.login(gmail['user'], gmail['password'])
    server.sendmail(gmail['user'], receiver_mail, multipart.as_string())
    # closing the connection to the SMTP server
    server.quit()


from storage import ftp
from config import Email, SLACK
from xhtml2pdf import pisa
from getpass import getpass
from notifypy import Notify
from termcolor import colored
from sqlalchemy.orm import sessionmaker
from concurrent.futures import ThreadPoolExecutor
import filehash, pyautogui, re, requests, shutil, time
from models.database import Code, File, Log, User, engine

"""
import pyfiglet
pyfiglet.figlet_format(text)
"""
def banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("""\033[93m
 ____                  _   _         ____                   _
/ ___|  ___ _ __ _   _| |_(_)_ __   |  _ \\ _   _ _ __   ___| |__   ___  _ __
\\___ \\ / __| '__| | | | __| | '_ \\  | |_) | | | | '_ \\ / __| '_ \\ / _ \\| '__|
 ___) | (__| |  | |_| | |_| | | | | |  __/| |_| | | | | (__| | | | (_) | |
|____/ \\___|_|   \\__,_|\\__|_|_| |_| |_|    \\__,_|_| |_|\\___|_| |_|\\___/|_|
\033[0m""")

def menu_at_beginning():
    print(colored("""
=> 1. Register
=> 2. Login
""", "magenta"))

def menu_for_MFA():
    print(colored("""
=> 1. Code not received ? Resend code
=> 2. Provide code to probe for your identity
""", "magenta"))

def prompt(defaultText=""):
    return input(colored(f"(hids)@sp> {defaultText}", "green"))

def inform(text):
    print(colored(f"INFO : {text}.", "red"))

def pause():
    print("\nContinue...")
    return sys.stdin.read(1)

def get_input(field_name, read_function):
    user_input = read_function(f"Your {field_name} : ")
    while True:
        if not user_input:
            inform(f"{field_name} should not be empty")
            user_input = read_function(f"Your {field_name} : ")
        else:
            break
    return user_input

def get_email():
    email = input("Your email : ")
    while True:
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
            inform("this is not a valid email")
            email = input("Your email : ")
        else:
            break
    return email

def get_email_for_register():
    Session = sessionmaker(bind=engine)
    session = Session()
    email = get_email()
    while True:
        if session.query(User).filter_by(email = email).one_or_none():
            inform("email already registered; please, try another one")
            email = get_email()
        else:
            break
    session.close()
    return email

def get_pseudo():
    pseudo = input("Your pseudo : ")
    while True:
        if not re.match(r"^[a-zA-Z0-9]{3,}$", pseudo):
            inform("pseudo should only contain letters and digits and have a minima length of 3")
            pseudo = input("Your pseudo : ")
        else:
            break
    return pseudo

def get_pseudo_for_register():
    Session = sessionmaker(bind=engine)
    session = Session()
    pseudo = get_pseudo()
    while True:
        if session.query(User).filter_by(pseudo = pseudo).one_or_none():
            inform("pseudo already taken")
            pseudo = get_pseudo()
        else:
            break
    session.close()
    return pseudo

def get_password():
    password1 = getpass("Your password : ")
    while True:
        if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{6,}$", password1):
            inform("password should contain at least an uppercase letter, a lowercase letter, a digit, a special character among [@,$,!,%,*,?,&] and have a minima length of 6")
            password1 = getpass("Your password : ")
        else:
            break
    password2 = getpass("Your password again : ")
    while True:
        if password1 != password2:
            inform("passwords do not match")
            password2 = getpass("Your password again : ")
        else:
            break
    return password1

def validate_folder(folder):
    if not os.path.exists(folder):
        inform(f"path {folder} does not exist on your system")
    elif not os.path.isdir(folder):
        inform(f"{folder} is not a valid folder path")
    return os.path.realpath(folder).replace("\\", "/")

def validate_hids_mode(mode):
    if mode in ("GUARDIAN", "WATCHER"):
        return True
    else:
        inform(f"{mode} not a valid mode : choose between GUARDIAN or WATCHER")

""" def list_all_folder_files(folder):
    # declaring a function to print out all files located inside a directory
    def display_file(tuple_arg):
        folder = tuple_arg[0].replace("\\", "/")
        for file in tuple_arg[2]:
            print(f"(hids)@sp> {folder}/{file}")
    # running the script with parallel tasks so as to speed the listing
    inform("here comes the folder's files tree")
    with ThreadPoolExecutor(os.cpu_count()) as executor:
        executor.map(display_file, os.walk(folder)) """

def notify(message, title = "SCRUTIN-PUNCHOR", audio_file = "media/sound.wav", icon_file = "media/author.png"):
    notification = Notify()
    notification.title = title
    notification.message = message
    notification.audio = audio_file
    notification.icon = icon_file
    notification.send()

def throw_action(question):
    return pyautogui.confirm(
        text = question, 
        buttons = ["Yes", "No"],
        title = "SCRUTIN-PUNCHOR"
    ) == "Yes"

def countdown_timer(delay):
    RED = "\033[31m"
    RESET = "\033[0m"  # Reset to default color
    for x in range(delay, -1, -1):
        seconds = x % 60
        minutes = int(x / 60) % 60
        hours = int(x / 3600)
        print(f"\rYou need to wait for {RED}{hours:02}h:{minutes:02}min:{seconds:02}s{RESET} before going on...", end=" ")
        time.sleep(1)
    print()

def setPact(**kwargs):
    try:
        create(Log, **kwargs) # get_or_create(Log, **kwargs)
    except:
        pass

def from_SP(**kwargs):
    with sessionmaker(bind=engine)() as session:
        instance = session.query(Log).filter_by(**kwargs).order_by(Log.id.desc()).first()
        if instance :
            return instance.from_sp
    return False

def core_info():
    print(colored("""
    Give us a(more) folder(s) to guard or watch according to the following syntax : <folder-path>#<desired-mode>.

    Nota Bene : ScrutinPunchor has two desired modes :
                -""", "cyan") + " \033[93mGUARDIAN\033[0m " + colored("""accustomed to folder bolt,
                - and""", "cyan") + " \033[93mWATCHER\033[0m " + colored("""good at vulnerability analysis.

    Some examples: """, "cyan")+colored("""
        1.) """, "cyan") + colored("""E:/harmful#GUARDIAN""", "red")+colored("""
        2.) """, "cyan") + colored("""C:/sensitive#WATCHER
    """, "red"))

# def logFileSystemEvent(event, what, source, destination, user_id):
def logFileSystemEvent(**kwargs):
    if kwargs.get("user_id", None):
        # register log here into the database
        log = create(Log, **kwargs) # get_or_create(Log, **kwargs)
        return log

def create(model, **kwargs): # def get_or_create(model, **kwargs):
    with sessionmaker(bind=engine)() as session:
        # instance = session.query(model).filter_by(**kwargs).order_by(model.id.desc()).first()
        # # Instance found, return it and indicate it wasn't created
        # if instance:
        #     return instance.id, False 
        # Instance not found, create it, return it and indicate it was created
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance.id # return instance.id, True

# print(setPact(event = "created", source = r"E:\__stage__\endProject\app\test\keyboard"))

def convert_html_to_pdf(html_string, pdf_path):
    with open(pdf_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_string, dest=pdf_file)
    return not pisa_status.err



# # # utilities for files
def save_to_file_table(filepath, filesha512hash, newname = None):
    instance = None
    with sessionmaker(bind=engine)() as session:
        instance = session.query(File).filter_by(name=filepath).first()
        if not instance:
            instance = File(name=filepath)
            session.add(instance)
        if filesha512hash:
            instance.hash = filesha512hash
        if newname:
            instance.name = newname
        session.commit()

def read_from_file_table(filepath):
    with sessionmaker(bind=engine)() as session:
        instance = session.query(File).filter_by(name=filepath, deleted=False).first()
        if instance:
            return instance.hash

def mark_as_deleted(filepath):
    with sessionmaker(bind=engine)() as session:
        instance = session.query(File).filter_by(name=filepath).first()
        if instance:
            instance.deleted = True
            session.commit()

def extract_patterns_from_file_table(pattern):
    name_hash_dict = {}
    search_term = f'{pattern}%'
    with sessionmaker(bind=engine)() as session:
        instances = session.query(File).filter(File.name.like(search_term)).filter_by(deleted=False).all()
        for instance in instances:
            name_hash_dict[instance.name] = instance.hash
    return name_hash_dict


def init_checking_G_gui(folder, user_id):
    previous_state = extract_patterns_from_file_table(folder)
    previous_state_keys = list(previous_state.keys())
    # declaring a function to print out all files located inside a directory
    def checker(tuple_arg):
        folder_path = tuple_arg[0].replace("\\", "/")
        for file in tuple_arg[2]:
            full_file_path = f"{folder_path}/{file}"
            if full_file_path in previous_state_keys:
                filesha512hash = filehash.FileHash("sha512").hash_file(full_file_path)
                if filesha512hash != previous_state[full_file_path]:
                    message = f"{full_file_path } has been modified quite a long time. Are you the one behind it ?"
                    notify(message)
                    if not throw_action(message):
                        os.remove(full_file_path)
                        ftp.ftp_get(full_file_path, user_id)
                    else:
                        save_to_file_table(full_file_path, filesha512hash)
                        ftp.ftp_put(full_file_path, user_id)
            else:
                filesha512hash = filehash.FileHash("sha512").hash_file(full_file_path)
                save_to_file_table(full_file_path, filesha512hash)
                ftp.ftp_put(full_file_path, user_id)  # Assuming ftp_put is properly defined elsewhere

    # running the script with parallel tasks so as to speed the listing
    # inform("Here comes the folder's files tree")

    with ThreadPoolExecutor(os.cpu_count()) as executor:
        # Pass only the folder path using os.walk, and handle user_id in the function itself
        executor.map(checker, os.walk(folder))


def init_checking_G_cli(folder, user_id, user_pseudo, user_email):
    previous_state = extract_patterns_from_file_table(folder)
    previous_state_keys = list(previous_state.keys())
    # declaring a function to print out all files located inside a directory
    def checker(tuple_arg):
        folder_path = tuple_arg[0].replace("\\", "/")
        for file in tuple_arg[2]:
            full_file_path = f"{folder_path}/{file}"
            if full_file_path in previous_state_keys:
                filesha512hash = filehash.FileHash("sha512").hash_file(full_file_path)
                if filesha512hash != previous_state[full_file_path]:
                    message = f"{full_file_path } has been modified quite a long time. Are you the one behind it ? Check your mail in order to react 😳."
                    send_message_to_slack(message)
                    # view consumer for actions
                    send_mail(
                        receiver_mail = user_email,
                        message_subject = "User Awareness",
                        message_type = "AWARENESS",
                        message_body = {
                            "pseudo": self.user_pseudo,
                            "event": f"File {message}",
                            "data": obfuscate_data(
                                {
                                    "scrutin-punchor-mode": "GUARDIAN at init_checking",
                                    "source": full_file_path,
                                    "filetype": "file",
                                    "user_id": user_id,
                                    "originate-timestamp": datetime.now().timestamp()
                                },
                                user_pseudo
                            )
                        }
                    )
            else:
                filesha512hash = filehash.FileHash("sha512").hash_file(full_file_path)
                save_to_file_table(full_file_path, filesha512hash)
                ftp.ftp_put(full_file_path, user_id)  # Assuming ftp_put is properly defined elsewhere

    # running the script with parallel tasks so as to speed the listing
    with ThreadPoolExecutor(os.cpu_count()) as executor:
        # Pass only the folder path using os.walk, and handle user_id in the function itself
        executor.map(checker, os.walk(folder))


from controllers.mdp import check_user_identity_on_confirm_box
def action_on_create(created_file_type, created_file_path, user_id):
    if not throw_action(f"{created_file_path} has just been created. Does such event come from you ?"):
        if check_user_identity_on_confirm_box():
            setPact(
                event = LogEvent.DELETED, 
                file_type = created_file_type, 
                source = created_file_path, 
                user_id = user_id, 
                from_sp = True
            )
            if created_file_type == "folder":
                for tuple_choices in list(os.walk(created_file_path)):
                    for file in tuple_choices[-1]:
                        to_erase = tuple_choices[0] + os.path.sep + file
                        setPact(
                            event = LogEvent.DELETED, 
                            file_type = "file", 
                            source = to_erase, 
                            user_id = user_id, 
                            from_sp = True
                        )
                        os.remove(to_erase)
                    # if tuple_choices[0] != cr
                os.rmdir(created_file_path)
            elif created_file_type == "file":
                os.remove(created_file_path)
    else:
        if check_user_identity_on_confirm_box():
            if created_file_type == "file":
                filesha512hash = filehash.FileHash("sha512").hash_file(created_file_path)
                save_to_file_table(created_file_path, filesha512hash)
            ftp.ftp_put(created_file_path, user_id)


def action_on_modify(modified_file_type, modified_file_path, user_id):
    if not throw_action(f"{modified_file_path} has just been modified. Does such event come from you ?"):
        if check_user_identity_on_confirm_box():
            setPact(
                event = LogEvent.DELETED, 
                file_type = modified_file_type, 
                source = modified_file_path, 
                user_id = user_id, 
                from_sp = True
            )
            os.remove(modified_file_path)
            ftp.ftp_get(modified_file_path, user_id)
    else:
        if check_user_identity_on_confirm_box():
            filesha512hash = filehash.FileHash("sha512").hash_file(modified_file_path)
            save_to_file_table(modified_file_path, filesha512hash)
            ftp.ftp_put(modified_file_path, user_id)


def action_on_move(moved_file_type, old_file_path, new_file_path, user_id):
    if not throw_action(f"{old_file_path} has just been moved to {new_file_path}. Does such event come from you ?"):
        if check_user_identity_on_confirm_box():
            setPact(
                event = LogEvent.MOVED, 
                file_type = moved_file_type, 
                source = new_file_path,
                destination = old_file_path, 
                user_id = user_id, 
                from_sp = True
            )
            shutil.move(new_file_path, old_file_path)
    else:
        if check_user_identity_on_confirm_box():
            if moved_file_type == "file":
                save_to_file_table(moved_file_path, None, new_file_path)
            ftp.ftp_delete(old_file_path, user_id)
            ftp.ftp_put(new_file_path, user_id)


def action_on_delete(deleted_file_type, deleted_file_path, user_id):
    if not throw_action(f"{deleted_file_path} has just been deleted. Does such event come from you ?"):
        if check_user_identity_on_confirm_box():
            setPact(
                event = LogEvent.CREATED, 
                file_type = deleted_file_type, 
                source = deleted_file_path,
                user_id = user_id, 
                from_sp = True
            )
            ftp.ftp_get(deleted_file_path, user_id)
    else:
        if check_user_identity_on_confirm_box():
            mark_as_deleted(deleted_file_path)
            ftp.ftp_delete(deleted_file_path, user_id)


# # # send messages to slack instance
def send_message_to_slack(message):
    """
    Send message to our slack channel #notifications as pylarm-sentinel user.
    """
    try:
        response = requests.post(
            SLACK.load()["webhook-url"],
            data = "{'text': '%s'}" %(message)
        )
        return (response.text == "ok")
    except:
        return False
