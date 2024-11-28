from storage import ftp
from config import CRYPT, RMQ
import filehash, json, jwt, os, pika, sys
from models.database import LogEvent
from cryptography.fernet import Fernet
from controllers.utils import (
    read_from_file_table, save_to_file_table, setPact, mark_as_deleted
)
from controllers.modes.guardian.gui import (
    action_on_create, action_on_modify, action_on_move, action_on_delete
)

def mainT(user_id, user_pseudo):
    BROKER_CREDS = RMQ.load()
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=BROKER_CREDS["host"],
            credentials=pika.PlainCredentials(
                username=BROKER_CREDS["username"], 
                password=BROKER_CREDS["password"]
            )
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue=user_pseudo)

    def callback(ch, method, properties, body):
        print(body)
        CRYPTO_KEYS = CRYPT.load()
        data = jwt.decode(body, CRYPTO_KEYS["jwtk"], algorithms=['HS256'])
        body_in_data = json.loads(
            Fernet(CRYPTO_KEYS["symk"].encode()).decrypt(data["body"].encode())
        )
        pseudo_queue_in_data = data["pseudo_queue"]
        trusted_in_data = data["trusted"]
        print(data)
        print(body_in_data)
        if body_in_data["scrutin-punchor-mode"][:8] == "GUARDIAN":
            if len(body_in_data["scrutin-punchor-mode"]) > 8:
                if trusted_in_data:
                    os.remove(full_file_path)
                    ftp.ftp_get(full_file_path, user_id)
                else:
                    save_to_file_table(full_file_path, filesha512hash)
                    ftp.ftp_put(full_file_path, user_id)
            else:
                event_name = body_in_data["event"]
                event = LogEvent.CREATED if event_name == "created" else LogEvent.MODIFIED if event_name == "modified" else LogEvent.MOVED if event_name == "moved" else LogEvent.DELETED
                source = body_in_data.get("source", "")
                destination = body_in_data.get("destination", "")
                file_type = body_in_data.get("filetype", "")
                user_id = body_in_data.get("user_id", None)
                match event_name:
                    case "created":
                        if not trusted_in_data:
                            setPact(
                                event = LogEvent.DELETED, 
                                file_type = file_type, 
                                source = source, 
                                user_id = user_id
                            )
                            if file_type == "folder":
                                for tuple_choices in list(os.walk(source)):
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
                                os.rmdir(source)
                            elif file_type == "file":
                                os.remove(source)
                        else:
                            if file_type == "file":
                                filesha512hash = filehash.FileHash("sha512").hash_file(source)
                                save_to_file_table(source, filesha512hash)
                            ftp.ftp_put(source, user_id)
                    case "modified":
                        if not trusted_in_data:
                            setPact(
                                event = LogEvent.DELETED, 
                                file_type = file_type, 
                                source = source, 
                                user_id = user_id, 
                                from_sp = True
                            )
                            os.remove(source)
                            ftp.ftp_get(source, user_id)
                        else:
                            filesha512hash = filehash.FileHash("sha512").hash_file(source)
                            save_to_file_table(source, filesha512hash)
                            ftp.ftp_put(source, user_id)
                    case "moved":
                        if not trusted_in_data:
                            setPact(
                                event = LogEvent.MOVED, 
                                file_type = file_type, 
                                source = destination,
                                destination = source, 
                                user_id = user_id, 
                                from_sp = True
                            )
                            shutil.move(destination, source)
                        else:
                            if file_type == "file":
                                save_to_file_table(source, None, destination)
                            ftp.ftp_delete(source, user_id)
                            ftp.ftp_put(destination, user_id)
                    case "deleted":
                        if not trusted_in_data:
                            setPact(
                                event = LogEvent.CREATED, 
                                file_type = file_type, 
                                source = source,
                                user_id = user_id, 
                                from_sp = True
                            )
                            ftp.ftp_get(source, user_id)
                        else:
                            mark_as_deleted(source)
                            ftp.ftp_delete(source, user_id)
        elif body_in_data["scrutin-punchor-mode"][:7] == "WATCHER":
            pass
        print(f" [x] Received {body.decode()}")

    channel.basic_consume(
        queue=user_pseudo, 
        on_message_callback=callback, 
        auto_ack=True
    )
    print(' [*] Waiting for messages. To exit press CTRL+C')
    channel.start_consuming()


def consume(user_id, user_pseudo):
    try:
        mainT(user_id, user_pseudo)
    except KeyboardInterrupt:
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)