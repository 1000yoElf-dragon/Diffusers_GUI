import os
from PIL import Image

from typing import Optional

from utils import load_yaml, save_yaml


def _try_load_image(filename, default_size=None):
    if isinstance(default_size, int):
        default_size = (default_size, default_size)
    try:
        return Image.open(filename)
    except:
        return Image.new(mode='L', size=default_size, color=128)


ICON_PATH = os.path.abspath("Icons")
CONFIG_FILE = os.path.abspath("config.yml")
DEFAULT_CONFIG_FILE = os.path.abspath("default.yml")
ICON_SIZE = 32
ADPROMPT_MAXLEN = 2048

PLACEHOLDER_IMAGE = _try_load_image(os.path.join(ICON_PATH, "placeholder.png"), ICON_SIZE)
ICONS = dict(
    (name, _try_load_image(os.path.join(ICON_PATH, name+".png"), ICON_SIZE))
    for name in [
        "favicon",
        "folder",
        "open_file",
        "plus",
        "arrow_up",
        "arrow_down",
        "arrow_right",
        "arrow_left",
        "arrow_trash",
        'forward',
        'backward'
    ]
)


default_config = dict(
    cache_dir="cache",         # Path to HuggingFace cache directory, default 'cache'
    max_models=1,              # Maximal number of models in memory, default '1'
    use_cuda=True,             # 'true' to use GPU if available, default 'true'
    use_float16=True,          # 'true' to use 'float16' for inference, default 'true'
    adprompt_path="adprompt",  # Path to store adPrompts

    nsfw_image="Icons/nsfw.png",

    repo_history=[],
    adprompt_history=[],
    neg_adprompt_history=[],
    init_image_history=[],
    filename_prefix_history=[],
    outdir_history=[],

)
config: Optional[dict] = default_config.copy()


def load():
    global config
    try:
        config.update(load_yaml(CONFIG_FILE))
    except FileNotFoundError:
        pass


def save():
    if config:
        save_yaml(CONFIG_FILE, config)
