import xml.etree.ElementTree as ET
import requests
from urllib.parse import urljoin

# Element → 辞書 に変換する関数
def etree_to_dict(elem):
    d = {elem.tag: {} if elem.attrib else None}
    children = list(elem)
    if children:
        dd = {}
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                if k in dd:
                    if not isinstance(dd[k], list):
                        dd[k] = [dd[k]]
                    dd[k].append(v)
                else:
                    dd[k] = v
        d = {elem.tag: dd}
    if elem.attrib:
        d[elem.tag].update(('@' + k, v) for k, v in elem.attrib.items())
    if elem.text and elem.text.strip():
        text = elem.text.strip()
        if children or elem.attrib:
            d[elem.tag]['#text'] = text
        else:
            d[elem.tag] = text
    return d


if __name__ == "__main__":

    # JMA XMLフィードを取得
    feed_url = "https://www.data.jma.go.jp/developer/xml/feed/regular.xml"
    response = requests.get(feed_url)
    response.raise_for_status()

    # XMLをパース
    root = ET.fromstring(response.content)

    # 辞書に変換
    result = etree_to_dict(root)

    # 出力
    import pprint
    pprint.pprint(result)
