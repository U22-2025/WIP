import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../srv')))

from WIPCommonPy.utils.network import resolve_ipv4


def test_resolve_ipv4_localhost():
    assert resolve_ipv4('localhost') == '127.0.0.1'
