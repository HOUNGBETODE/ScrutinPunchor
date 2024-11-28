from config import FTP
import filehash, ftplib, os
from models.database import LogEvent
from controllers.utils import inform, save_to_file_table, setPact


def ftp_put(path, user_id = None):
    if user_id:
        dirname = basename = None
        if os.path.isdir(path):
            dirname = os.path.dirname(path)
        else:
            dirname = os.path.dirname(path).replace("\\", "/")
            basename = os.path.basename(path).replace("\\", "/")
        ftp_server = FTP.load()
        try:
            with ftplib.FTP_TLS(
                ftp_server["host"],
                ftp_server["username"],
                ftp_server["password"]
            ) as session:
                session.prot_p()
                path_splitted = (str(user_id) + "/" + dirname).split("/")
                for path_part in path_splitted:
                    try:
                        session.cwd(path_part)
                    except ftplib.all_errors:
                        try:
                            session.mkd(path_part)
                            session.cwd(path_part)
                        except ftplib.all_errors as e:
                            print(str(e))
                            raise Exception("Cannot create directory chain %s" % path)
                if basename:
                    with open(path, "rb") as file:
                        session.storbinary(f"STOR {basename}", file)
                inform(f"File uploaded successfully to {user_id}/{path}")
                save_to_file_table(path, filehash.FileHash("sha512").hash_file(path))
                return True
        except Exception as e:
            inform(f"Error uploading file: {e}")


def ftp_get(path, user_id = None):
    if user_id:
        filename = path.replace(os.path.sep, "/")
        path = str(user_id) + "/" + filename
        ftp_server = FTP.load()
        try:
            with ftplib.FTP_TLS(
                ftp_server["host"],
                ftp_server["username"],
                ftp_server["password"]
            ) as session:
                session.prot_p()
                current_path = ""
                for folder_name in filename.split("/")[:-1]:
                    current_path += f"{folder_name}/"
                    if not os.path.exists(current_path):
                        setPact(
                            event = LogEvent.CREATED, 
                            file_type = "folder", 
                            source = current_path,
                            user_id = user_id
                        )
                        os.mkdir(current_path)
                setPact(
                    event = LogEvent.CREATED, 
                    file_type = "file", 
                    source = filename,
                    user_id = user_id
                )
                setPact(
                    event = LogEvent.MODIFIED, 
                    file_type = "file", 
                    source = filename,
                    user_id = user_id
                )
                with open(filename, "wb") as file:
                    session.retrbinary(f"RETR {path}", file.write)
                inform(f"File downloaded successfully from {path}")
                return True
        except Exception as e:
            inform(f"Error downloading file: {e}")


def ftp_delete(path, user_id = None):
    if user_id:
        dirname = os.path.dirname(path)
        basename = os.path.basename(path)
        path_splitted = (str(user_id) + os.path.sep + dirname).split(os.path.sep)
        path = "/".join(path_splitted)
        ftp_server = FTP.load()
        try:
            with ftplib.FTP_TLS(
                ftp_server["host"],
                ftp_server["username"],
                ftp_server["password"]
            ) as session:
                session.prot_p()
                session.cwd(path)
                files = session.nlst()
                if basename in files:
                    session.delete(basename)
                    if len(files) == 1:
                        for folder in path_splitted[::-1]:
                            session.cwd("..")
                            session.rmd(folder)
                            if session.nlst():
                                break
                    inform(f"File deleted successfully from {path}/{basename}")
                    return True
                else:
                    raise Exception(path + "/" + basename)
        except Exception as e:
            inform(f"Error deleting file: {e}")