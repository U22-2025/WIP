class Format:
    """
    This class is used to define the format of the packets.
    """
    def __init__(self):
        self.version = None
        self.packet_ID = None
        self.type = None
        self.weather_flag = None
        self.temperature_flag = None
        self.pops_flag = None
        self.alert_flag = None
        self.disaster_flag = None
        self.ex_flag = None
        self.day = None
        self.reserved = None
        self.timestamp = None
        self.area_code = None
        self.checksum = None

    def extract_bits(self, bitstr: int, start: int, length: int) -> int:
        mask = (1 << length) - 1
        return (bitstr >> start) & mask

    def extract_rest_bits(self, bitstr: int, start: int) -> int:
        return bitstr >> start

    def common_bit_fetch(self, bitstr: int):
        self.version = self.extract_bits(bitstr, 0, 4)
        self.packet_ID = self.extract_bits(bitstr, 4, 12)
        self.type = self.extract_bits(bitstr, 16, 3)
        self.weather_flag = self.extract_bits(bitstr, 19, 1)
        self.temperature_flag = self.extract_bits(bitstr, 20, 1)
        self.pops_flag = self.extract_bits(bitstr, 21, 1)
        self.alert_flag = self.extract_bits(bitstr, 22, 1)
        self.disaster_flag = self.extract_bits(bitstr, 23, 1)
        self.ex_flag = self.extract_bits(bitstr, 24, 1)
        self.day = self.extract_bits(bitstr, 25, 3)
        self.reserved = self.extract_bits(bitstr, 28, 4)
        self.timestamp = self.extract_bits(bitstr, 32, 64)
        self.area_code = self.extract_bits(bitstr, 96, 20)
        self.checksum = self.extract_bits(bitstr, 116, 12)


class Request(Format):
    def __init__(self):
        super().__init__()

    def bits_fetch(self, bitstr: int):
        self.common_bit_fetch(bitstr)
        # timestamp などは既に common_bit_fetch で設定済みなので再設定不要です


class Response(Format):
    def __init__(self):
        super().__init__()
        self.weather_code = None
        self.temperature = None
        self.pops = None
        self.ex_field = None

    def bits_fetch(self, bitstr: int):
        self.common_bit_fetch(bitstr)
        self.weather_code = self.extract_bits(bitstr, 16, 16)
        self.temperature = self.extract_bits(bitstr, 32, 8)
        self.pops = self.extract_bits(bitstr, 40, 8)
        self.ex_field = self.extract_rest_bits(bitstr, 48)


class ResolverRequest(Format):
    def __init__(self):
        super().__init__()
        self.longitude = None
        self.latitude = None

    def bits_fetch(self, bitstr: int):
        self.common_bit_fetch(bitstr)
        self.longitude = self.extract_bits(bitstr, 16, 64)
        self.latitude = self.extract_bits(bitstr, 80, 64)


class ResolverResponse(Format):
    def __init__(self):
        super().__init__()
        self.longitude = None
        self.latitude = None
        self.ex_field = None

    def bits_fetch(self, bitstr: int):
        self.common_bit_fetch(bitstr)
        self.longitude = self.extract_bits(bitstr, 16, 64)
        self.latitude = self.extract_bits(bitstr, 80, 64)
        self.ex_field = self.extract_rest_bits(bitstr, 144)