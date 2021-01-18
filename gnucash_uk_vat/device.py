
def get_device():
    try:
        import dmidecode
        d = dmidecode.DMIDecode()
        manuf = d.manufacturer()
        model = d.model()
        serial = d.serial_number()
        return {
            "manufacturer": manuf,
            "model": model,
            "serial": serial,
        }
    except:
        return None

