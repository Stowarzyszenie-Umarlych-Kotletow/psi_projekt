from threading import Lock
import os, yaml
from xml.dom import NotFoundErr
import hashlib
import fcntl

from .file_metadata import FileMetadata


class Singleton(type):

    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class LoadingRepositoryError(Exception):
    pass


class HashingError(Exception):
    pass


class RepositoryModificationError(Exception):
    pass


class Repository(metaclass=Singleton):

    _files: dict
    _path: str

    def __init__(self, config={}):
        self._path = config["path"]
        mode = 0o700
        if not os.path.isdir(self._path):
            try:
                os.mkdir(self._path, mode)
            except Exception as e:
                print(e)

    def load(self):
        self._files = dict()
        files = [
            f
            for f in os.listdir(self._path)
            if os.path.isfile(os.path.join(self._path, f))
            and f.split(".")[-1] == "yaml"
        ]
        for file in files:
            with open(self._path + file, "r+") as f:
                parsed_yaml = yaml.load(f, Loader=yaml.FullLoader)
                data = parsed_yaml["metadata"]

                if not os.path.isfile(data["path"]):
                    raise LoadingRepositoryError("Is not a file")
                if self.__calculate_hash(data["path"]) != data["hash"]:
                    data = self.__update_metadata(data)
                    parsed_yaml["metadata"] = data
                    f.seek(0)
                    yaml.dump(parsed_yaml, f)

                self._files[data["name"]] = FileMetadata(data)
                # self.__lock_file(data["path"])

    def add_file(self, path: str):
        if not os.path.isfile(path):
            raise RepositoryModificationError("Is not a file")
        filename = os.path.basename(path)
        if filename in self._files.keys():
            raise RepositoryModificationError("This file is already in the repository")
        data = self.__update_metadata(dict(name=filename, path=path, status="READY"))
        self._files[filename] = FileMetadata(data)
        self.__persist_filedata(data)

    def remove_file(self, filename: str):
        if filename not in self._files.keys():
            raise RepositoryModificationError("No such file in repository")
        if self._files[filename].status == "UPLOADING":
            raise RepositoryModificationError("File currently being uploaded")
        del self._files[filename]
        yaml_path = self._path + filename + ".yaml"
        if not os.path.exists(yaml_path):
            raise RepositoryModificationError("Cannot find yaml file")
        os.remove(yaml_path)

    def get_files(self):
        return self._files

    def find(self, filename: str) -> FileMetadata:
        if filename not in self._files.keys():
            raise NotFoundErr
        return self._files[filename]

    def change_state(self, filename: str, new_status: str = None) -> None:
        if filename not in self._files.keys():
            raise NotFoundErr
        file_data: FileMetadata = self._files[filename]
        if new_status:
            file_data.status = new_status
        self._files[filename] = FileMetadata(
            self.__update_metadata(file_data.as_dict())
        )
        self.__persist_filedata(self._files[filename].as_dict())

    # def __lock_file(self, path: str):
    #     print(path)
    #     f = open(path, "w")
    #     fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def __persist_filedata(self, data: dict) -> None:
        path = self._path + data["name"] + ".yaml"
        with open(path, "w") as f:
            yaml_data = dict()
            yaml_data["metadata"] = data
            yaml.dump(yaml_data, f)

    def __update_metadata(self, data: dict) -> dict:
        new_hash = self.__calculate_hash(data["path"])
        new_size = os.path.getsize(data["path"])
        data["hash"] = new_hash
        data["size"] = new_size
        return data

    def __calculate_hash(self, path: str) -> str:
        sha256_hash = hashlib.sha256()
        if not os.path.isfile(path):
            raise HashingError("Is not a file")
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
