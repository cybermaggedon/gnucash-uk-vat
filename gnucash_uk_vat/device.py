from typing import Optional, Dict, Any

def get_device() -> Optional[Dict[str, Any]]:

    import platform
    p = platform.system()

    if p == 'Linux':
        return get_linux_device()
    elif p == 'Darwin':
        return get_darwin_device()
    elif p == 'Windows':
        return get_windows_device()
    else:
        raise RuntimeError("Can't do get_device on platform " + p)

def get_linux_device() -> Optional[Dict[str, Any]]:
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

def get_windows_device() -> Dict[str, Any]:
    import subprocess
    uuid = str(
        subprocess.check_output('wmic csproduct get uuid'), 'utf-8'
    ).split('\n')[1].strip()
    model = str(
        subprocess.check_output('wmic csproduct get name'), 'utf-8'
    ).split('\n')[1].strip()
    manuf = str(
        subprocess.check_output('wmic csproduct get vendor'), 'utf-8'
    ).split('\n')[1].strip()

    return {
        "manufacturer": manuf,
        "model": model,
        "serial": id,
    }

def get_darwin_device() -> Dict[str, Any]:
    import json
    import subprocess
    system_profile_data = subprocess.Popen(
        ['system_profiler', '-json', 'SPHardwareDataType'],
        stdout=subprocess.PIPE
    )
    if system_profile_data.stdout is not None:
        data = json.loads(system_profile_data.stdout.read())
    else:
        data = {}
    sp = data.get('SPHardwareDataType', {})[0]

    return {
        "manufacturer": "Apple",
        "model": sp.get("machine_model"),
        "serial": sp.get("serial_number"),
    }

