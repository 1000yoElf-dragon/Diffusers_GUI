import os
from PIL import Image

from utils import QueueMap


class FileCache(QueueMap):
    def __init__(self, max_size: int = 20, cache_saved: bool = False):
        super(FileCache, self).__init__(max_size)
        self.cache_saved = cache_saved

    def load(self, filename: str):
        filename = os.path.abspath(filename).lower()
        stats = os.stat(filename)
        if filename in self and self[filename][1] == stats:
            self.to_back(filename)
            return self[filename][0]
        else:
            content = self.load_from_disk(filename)
            self.push(filename, (content, stats))
        return content

    def save(self, filename: str, content, cache_saved: bool = None):
        filename = os.path.abspath(filename).lower()
        self.save_to_disk(filename, content)
        if cache_saved or cache_saved is None and self.cache_saved:
            self.push(filename, (content, os.stat(filename)))

    def load_from_disk(self, filename: str):
        raise NotImplementedError("Virtual metod overload required")

    def save_to_disk(self, filename: str, content):
        raise NotImplementedError("Virtual metod overload required")


class TextFileCahe(FileCache):
    def load_from_disk(self, filename: str):
        with open(filename, 'rt') as file:
            content = file.read()
        return content

    def save_to_disk(self, filename: str, content):
        with open(filename, 'wt') as file:
            file.write(content)


class ImageFileCahe(FileCache):
    def load_from_disk(self, filename: str):
        return Image.open(filename)

    def save_to_disk(self, filename: str, content):
        content.save(filename)


text_files = TextFileCahe(100)
image_files = ImageFileCahe(20)
