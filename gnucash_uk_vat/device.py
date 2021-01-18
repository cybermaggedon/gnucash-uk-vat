
def get_device():
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

