import os.path
from PIL import Image
import yaml


def load_yaml(fname: str, defautl_fname: str, default=None) -> dict:
    try:
        with open(fname, 'rt') as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError as error:
        if defautl_fname is not None:
            return load_yaml(defautl_fname, default)
        if default is not None:
            return default
        else:
            raise error


def save_yaml(fname: str, mapping: dict):
    with open(fname, 'wt') as file:
        for key, value in mapping.items():
            yaml.safe_dump({key: value}, file )


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


bad_chars = set('\\/:*?»<>|')
def valid_fname(fname):
    bad_chars.isdisjoint(fname)


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
