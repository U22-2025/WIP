# チェックサムの計算メソッド
def calc_checksum12(data: bytes) -> int:
    sum = 0

    # 1バイトずつ加算
    for byte in data:
        sum += byte

    # キャリーを12ビットに折り返し
    while sum >> 12:
        sum = (sum & 0xFFF) + (sum >> 12)

    # 1の補数を返す（12ビットマスク）
    checksum = (~sum) & 0xFFF
    return checksum

# チェックサムの検証メソッド
def verify_checksum12(data_with_checksum: bytes) -> bool:
    return calc_checksum12(data_with_checksum) == 0

import dns.resolver
def resolve_dns(domain:str):
    resolver = dns.resolver.Resolver()
    answers = resolver.resolve(domain, 'a')
    if not answers:
        # aレコードが取得できなかったらaaaaレコードを要求
        answers = resolver.resolve(domain, 'aaaa')
    return answers[0]
