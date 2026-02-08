"""Bangumi API enum definitions."""
from enum import Enum, IntEnum


class SubjectType(IntEnum):
    """
    条目类型
    1 = book, 2 = anime, 3 = music, 4 = game, 6 = real
    """

    BOOK = 1
    ANIME = 2
    MUSIC = 3
    GAME = 4
    REAL = 6


class EpType(IntEnum):
    """
    章节类型
    0 = 本篇, 1 = 特别篇, 2 = OP, 3 = ED, 4 = 预告/宣传/广告, 5 = MAD, 6 = 其他
    """

    MAIN_STORY = 0
    SP = 1
    OP = 2
    ED = 3
    PV = 4
    MAD = 5
    OTHER = 6


class CharacterType(IntEnum):
    """
    type of a character
    1 = 角色, 2 = 机体, 3 = 舰船, 4 = 组织...
    """

    CHARACTER = 1
    MECHANIC = 2
    SHIP = 3
    ORGANIZATION = 4


class PersonType(IntEnum):
    """
    type of a person or company
    1 = 个人, 2 = 公司, 3 = 组合
    """

    INDIVIDUAL = 1
    CORPORATION = 2
    ASSOCIATION = 3


class PersonCareer(str, Enum):
    """
    Career of a person
    'producer', 'mangaka', 'artist', 'seiyu', 'writer', 'illustrator', 'actor'
    """

    PRODUCER = "producer"
    MANGAKA = "mangaka"
    ARTIST = "artist"
    SEIYU = "seiyu"
    WRITER = "writer"
    ILLUSTRATOR = "illustrator"
    ACTOR = "actor"


class BloodType(IntEnum):
    """
    Blood type of a person.
    1=A, 2=B, 3=AB, 4=O
    """

    A = 1
    B = 2
    AB = 3
    O = 4


class CollectionType(IntEnum):
    """
    Collection status type.
    1=Wish, 2=Collect, 3=Doing, 4=On Hold, 5=Dropped
    """

    WISH = 1
    COLLECT = 2
    DOING = 3
    ON_HOLD = 4
    DROPPED = 5


class EpisodeCollectionType(IntEnum):
    """
    Episode collection status type.
    1=Wish (想看), 2=Done (看过), 3=Dropped (抛弃)
    """

    WISH = 1
    DONE = 2
    DROPPED = 3
