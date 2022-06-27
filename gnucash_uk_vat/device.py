
import platform

def get_device():

    p = platform.system()
    print("Platform is", p)

    if p == 'Linux':
        return get_linux_device()
    elif p == 'Darwin':
        return get_darwin_device()
    elif p == 'Windows':
        return get_windows_device()
    else:
        raise RuntimeError("Can't do get_device on platform " + p)

def get_linux_device():
    try:
        import dmidecode
        d = dmidecode.DMIDecode(command=["sudo",  "dmidecode"])
        manuf = d.manufacturer()
        model = d.model()
        serial = d.serial_number()
        return {
            "manufacturer": manuf,
            "model": model,
            "serial": serial,
        }
    except Exception as e:
        print(e)
        return None

def get_windows_device():
    print("NOT WORKING?!")
    raise RuntimeError("Windows not implemented")

def get_darwin_device():
    import json
    import subprocess
    system_profile_data = subprocess.Popen(
        ['system_profiler', '-json', 'SPHardwareDataType'],
        stdout=subprocess.PIPE
    )
    data = json.loads(system_profile_data.stdout.read())
    sp = data.get('SPHardwareDataType', {})[0]

    return {
        "manufacturer": "Apple",
        "model": sp.get("machine_model"),
        "serial": sp.get("serial_number"),
    }

