from enum import Enum


class Lang(Enum):
    LANG_KO = 'ko-KR'
    LANG_EN = 'en-US'
    LANG_CN = 'zh-CN'
    LANG_JP = 'ja-JP'
    LANG_VN = 'vi-VN'


class Vendor(Enum):
    AWS = 'aw'
    ClovaNest = 'cn'
