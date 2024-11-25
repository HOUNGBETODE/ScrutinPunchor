import ftplib, os
from config import FTP
from models.database import LogEvent
from controllers.utils import inform, setPact


def ftp_put(path, user_id = None):
    if user_id:
        # print(f"{path = }")
        dirname = basename = None
        if os.path.isdir(path):
            dirname = os.path.dirname(path)
        else:
            dirname = os.path.dirname(path).replace("\\", "/")
            basename = os.path.basename(path).replace("\\", "/")
        ftp_server = FTP.load()
        try:
            # Establish FTPS connection
            with ftplib.FTP_TLS(
                ftp_server["host"],
                ftp_server["username"],
                ftp_server["password"]
            ) as session:
                # Enable data encryption
                session.prot_p()
                # Create subdirectories
                path_splitted = (str(user_id) + "/" + dirname).split("/")
                # print(f"{path_splitted = }")
                for path_part in path_splitted:
                    # print(f"{path_part  =}")
                    try:
                        session.cwd(path_part)
                    except ftplib.all_errors:
                        try:
                            session.mkd(path_part)
                            session.cwd(path_part)
                        except ftplib.all_errors as e:
                            print(str(e))
                            raise Exception("Cannot create directory chain %s" % path)
                # Upload file
                if basename:
                    with open(path, "rb") as file:
                        session.storbinary(f"STOR {basename}", file)
                inform(f"File uploaded successfully to {user_id}/{path}")
                return True
        except Exception as e:
            inform(f"Error uploading file: {e}")


def ftp_get(path, user_id = None):
    if user_id:
        filename = path.replace(os.path.sep, "/")
        path = str(user_id) + "/" + filename
        ftp_server = FTP.load()
        try:
            # Establish FTPS connection
            with ftplib.FTP_TLS(
                ftp_server["host"],
                ftp_server["username"],
                ftp_server["password"]
            ) as session:
                # Enable data encryption
                session.prot_p()
                # Create subfolders in case they do not exist
                current_path = ""
                for folder_name in filename.split("/")[:-1]:
                    current_path += f"{folder_name}/"
                    if not os.path.exists(current_path):
                        setPact(
                            event = LogEvent.CREATED, 
                            file_type = "folder", 
                            source = current_path,
                            user_id = user_id, 
                            from_sp = True
                        )
                        os.mkdir(current_path)
                # Download file
                setPact(
                    event = LogEvent.CREATED, 
                    file_type = "file", 
                    source = filename,
                    user_id = user_id, 
                    from_sp = True
                )
                setPact(
                    event = LogEvent.MODIFIED, 
                    file_type = "file", 
                    source = filename,
                    user_id = user_id, 
                    from_sp = True
                )
                print(filename)
                # print(open(filename, "rb").readline())
                # print(path)
                # print(filename)
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
            # Establish FTPS connection
            with ftplib.FTP_TLS(
                ftp_server["host"],
                ftp_server["username"],
                ftp_server["password"]
            ) as session:
                # Enable data encryption
                session.prot_p()
                # Cope with file deletion
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


# ftp_put(r"C:\Users\HP\Downloads\les-10-commandements-de-Dieu.pdf", user_id=2)
# ftp_put(r"C:\Users\HP\sharing.py", user_id=2)
# ftp_delete(r"C:\Users\HP\sharing.py", user_id=2)
# ftp_get(r"C:\Users\HP\Downloads\les-10-commandements-de-Dieu.pdf", user_id=2)

