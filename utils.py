import os.path
from PIL import Image
import yaml
import re
from heapq import heapify, heappop, heappushpop
from typing import Dict, Any, Union


class QueueMap:
    class Element:
        __slots__ = ['key', 'value', 'priority', 'new_priority']

        def __init__(self, key, value, priority):
            self.key = key
            self.value = value
            self.new_priority = self.priority = priority

        def __eq__(self, other):
            return self.priority == other.priority

        def __ne__(self, other):
            return self.priority != other.priority

        def __gt__(self, other):
            return self.priority > other.priority

        def __ge__(self, other):
            return self.priority >= other.priority

        def __lt__(self, other):
            return self.priority < other.priority

        def __le__(self, other):
            return self.priority <= other.priority

    __slots__ = ['heap', 'mapping', 'counter', 'max_size']
    heap: list
    mapping: Dict[Any, Element]
    counter: int
    max_size: int

    def __init__(self, max_size=None):
        super(QueueMap, self).__init__()
        self.heap = []
        self.mapping = {}
        self.counter = 0
        self.max_size = max_size

    @classmethod
    def from_dict(cls, mapping: dict, max_size=None):
        heapmap = cls(max_size)
        rest = len(mapping)
        for key, value in mapping.items():
            if max_size and rest > max_size:
                rest -= 1
                continue
            heapmap.counter += 1
            element = QueueMap.Element(key, value, heapmap.counter)
            heapmap.mapping[key] = element
            heapmap.heap.append(element)
        heapify(heapmap.heap)
        return heapmap

    def __getitem__(self, key):
        return self.mapping[key].value

    def __setitem__(self, key, value):
        self.mapping[key].value = value

    def __contains__(self, key):
        return key in self.mapping

    def __len__(self):
        return len(self.mapping)

    def clear(self) -> None:
        self.mapping.clear()
        self.heap.clear()

    def push(self, key, value):
        self.counter += 1
        if key in self.mapping:
            self.mapping[key].value = value
            self.mapping[key].new_priority = self.counter
        else:
            element = QueueMap.Element(key, value, self.counter)
            if len(self.heap) == self.max_size:
                old_element = heappushpop(self.heap, element)
                while old_element.priority != old_element.new_priority:
                    old_element.priority = old_element.new_priority
                    old_element = heappushpop(self.heap, old_element)
                del self.mapping[old_element.key]
            self.mapping[key] = element

    def to_back(self, key):
        self.counter += 1
        element = self.mapping[key]
        element.new_priority = self.counter
        return element.value

    def pop(self):
        element = heappop(self.heap)
        while element.priority != element.new_priority:
            element.priority = element.new_priority
            element = heappushpop(self.heap, element)
        del self.mapping[element.key]
        return element.key, element.value

    def exodus(self):
        while len(self.heap):
            yield self.pop()


def load_yaml(fname: str) -> dict:
    with open(fname, 'rt') as file:
        return yaml.safe_load(file) or {}


def save_yaml(fname: str, mapping: dict):
    with open(fname, 'wt') as file:
        for key, value in mapping.items():
            yaml.safe_dump({key: value}, file)


TRUE_STR = {'yes', 'y', 'true', 't', 'on'}
def check_bool_opt(config: dict, option, default: bool = None):
    if option not in config:
        if default is not None:
            config[option] = default
            return default
        else:
            return None
    if isinstance(config[option], str):
        config[option] = config[option].lower() in TRUE_STR
    else:
        config[option] = bool(config[option])
    return config[option]


def not_include(bad_chars: str = '\\/:*?»<>|'):
    bad_chars_set = set(bad_chars)
    return lambda string: bad_chars_set.isdisjoint(string)


pattern_space = re.compile(r'\s+')
pattern_space_commas = re.compile(r'(?<=[.,])[\s.,]+|\s+')
def normalize_space(s: str):
    return re.sub(pattern_space, ' ', s).strip()
def normalize_space_commas(s: str):
    return re.sub(pattern_space_commas, ' ', s).strip()


# TODO: create adequate qoute parser
def strip_quotes(s: str) -> str:
    return s.strip(' \t\r\n\'\"')


def append_non_zero(list_: list, value):
    if value:
        list_.append(value)


def repo_key(repo_name: str) -> str:
    return repo_name.lower().replace(' ', '').replace('\t', '')


def image_fit(image: Image.Image, width: int, height: int, grid: int = 0) -> Image.Image:
    w, h = image.size
    w, h = (w * height // h, height) if h * width > w * height else (width, h * width // w)
    image = image.resize((w, h))
    if grid:
        if w < grid:
            w, h = grid, h * grid // w
        if h < grid:
            w, h = w * grid // h, grid
        crop_w = min(width, w // 32 * 32)
        crop_h = min(height, h // 32 * 32)
        image = image.crop((
            (w - crop_w) // 2, (h - crop_h) // 2,
            (w - crop_w) // 2 + crop_w, (h - crop_h) // 2 + crop_h)
        )
    if 0 in image.size:
        raise ValueError("Empty image")
    return image


def get_available_filename(folder, template, mask='?'):
    if not os.path.exists(folder):
        return template.replace(mask, '0')
    begin = template.find(mask)
    end = template.rfind(mask) + 1
    prefix = template[:begin]
    suffix = template[end:]
    digits = end - begin
    index = 0
    for file in os.scandir(folder):
        name = file.name
        if name.startswith(prefix) and name.endswith(suffix):
            num = name.removeprefix(prefix).removesuffix(suffix)
            if len(num) == digits:
                try:
                    index = max(index, int(num))
                except ValueError:
                    continue
    num = str(index+1)
    zeros = digits - len(num)
    return prefix + '0' * zeros + num + suffix


def file_naming(folder, template, mask='?'):
    begin = template.find(mask)
    end = template.rfind(mask)+1
    prefix = template[:begin]
    suffix = template[end:]
    digits = end-begin
    index = 0
    for file in os.scandir(folder):
        name = file.name
        if name.startswith(prefix) and name.endswith(suffix):
            num = name.removeprefix(prefix).removesuffix(suffix)
            if len(num) == digits:
                try:
                    index = max(index, int(num))
                except ValueError:
                    continue
    num = str(index)
    zeros = digits - len(num)
    while zeros >= 0:
        fname = os.path.join(folder, prefix + '0' * zeros + num + suffix)
        if not os.path.exists(fname):
            yield fname
        index += 1
        num = str(index)
        zeros = digits - len(num)


class SubstituteImage:
    def __init__(self, image_file=None):
        if image_file is not None:
            try:
                self.image = Image.open(image_file)
                self.w, self.h = self.image.size
                return
            except (AttributeError, FileNotFoundError):
                pass
        self.image = Image.new('RGB', (512, 512), (128, 128, 128))
        self.w, self.h = 512, 512

    def subst(self, width, height):
        image = image_fit(self.image, width, height)
        w, h = image.size
        x = (w - width) // 2
        y = (h - height) // 2
        return image.crop((x, y, x + width, y + height))


def clip(x: Union[int, float], lower: Union[int, float], upper: Union[int, float]) -> Union[int, float]:
    return max(min(x, upper), lower)
