from configparser import ConfigParser

def load(filename="config/env.ini", section="ftp-uploads"):
    parser = ConfigParser()
    parser.read(filename)
    ftp_server = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            ftp_server[param[0]] = param[1]
    else:
        raise Exception(f"Section {section} has not been found in {filename} file.")
    return ftp_server