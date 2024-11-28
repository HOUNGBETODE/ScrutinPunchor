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
    crypted_data = Fernet(CRYPTO_PARAMS["symk"].encode()).encrypt(json.dumps(data).encode()).decode()
    tokenized_data = jwt.encode(
        {"body": crypted_data, "pseudo_queue": pseudo_queue}, 
        CRYPTO_PARAMS["jwtk"], 
        algorithm='HS256'
    ).encode().hex()
    tokenized_data_length = len(tokenized_data)
    random_seed = random.choice(list(range(tokenized_data_length)))
    tokenized_data_shuffled = tokenized_data[random_seed:] + tokenized_data[:random_seed]
    return f"{int(tokenized_data_shuffled, 16)}.{random_seed}"

def export_to_buffer(file_path):
    with open(file_path, 'rb') as file:
        buffer = io.StringIO(file.read())
    return buffer.getvalue()

def send_mail(receiver_mail, message_subject, message_type, message_body):
    gmail = Email.load()
    multipart = MIMEMultipart()
    multipart['Subject'] = message_subject
    multipart['From'] = gmail['user']
    multipart['To'] = receiver_mail
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
    server = smtplib.SMTP_SSL('smtp.gmail.com')
    server.login(gmail['user'], gmail['password'])
    server.sendmail(gmail['user'], receiver_mail, multipart.as_string())
    server.quit()


from config import Email, SLACK
from xhtml2pdf import pisa
from getpass import getpass
from notifypy import Notify
from termcolor import colored
from sqlalchemy.orm import sessionmaker
from concurrent.futures import ThreadPoolExecutor
import pyautogui, re, requests, time
from models.database import Code, File, Log, LogTorch, User, engine

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
    RESET = "\033[0m"
    for x in range(delay, -1, -1):
        seconds = x % 60
        minutes = int(x / 60) % 60
        hours = int(x / 3600)
        print(f"\rYou need to wait for {RED}{hours:02}h:{minutes:02}min:{seconds:02}s{RESET} before going on...", end=" ")
        time.sleep(1)
    print()

def setPact(**kwargs):
    try:
        create(LogTorch, **kwargs)
    except:
        pass

def from_SP(**kwargs):
    with sessionmaker(bind=engine)() as session:
        if session.query(LogTorch).filter_by(**kwargs).first() :
            return True
    return False

def out_SP(**kwargs):
    with sessionmaker(bind=engine)() as session:
        # instance = session.query(Log).filter_by(**kwargs).order_by(Log.id.desc()).first()
        instance = session.query(LogTorch).filter_by(**kwargs).first()
        if instance :
            session.delete(instance)
            session.commit()

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

def logFileSystemEvent(**kwargs):
    if kwargs.get("user_id", None):
        log = create(Log, **kwargs)
        return log

def create(model, **kwargs):
    with sessionmaker(bind=engine)() as session:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance.id

def convert_html_to_pdf(html_string, pdf_path):
    with open(pdf_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_string, dest=pdf_file)
    return not pisa_status.err

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