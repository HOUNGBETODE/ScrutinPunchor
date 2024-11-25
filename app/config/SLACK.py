from configparser import ConfigParser

def load(filename="config/env.ini", section="slack-params"):
    parser = ConfigParser()
    parser.read(filename)
    slack = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            slack[param[0]] = param[1]
    else:
        raise Exception(f"Section {section} has not been found in {filename} file.")
    return slack
