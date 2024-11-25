from configparser import ConfigParser

def load(filename="config/env.ini", section="gmail"):
    # parser creation
    parser = ConfigParser()
    # loading the .ini file
    parser.read(filename)
    # creating an empty email object before processing filename
    email = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            email[param[0]] = param[1]
    else:
        raise Exception(f"Section {section} has not been found in {filename} file.")
    # returning the email object
    return email
