from configparser import ConfigParser

def load(filename="config/env.ini", section="virus-total"):
    parser = ConfigParser()
    parser.read(filename)
    vt_api_creds = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            vt_api_creds[param[0]] = param[1]
    else:
        raise Exception(f"Section {section} has not been found in {filename} file.")
    return vt_api_creds
