from configparser import ConfigParser

# for MalwareHashRegistry X-ApiKey header
def load(filename="config/env.ini", section="malware-hash-registry"):
    parser = ConfigParser()
    parser.read(filename)
    mhr_api_infos = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            mhr_api_infos[param[0]] = param[1]
    else:
        raise Exception(f"Section {section} has not been found in {filename} file.")
    return mhr_api_infos
