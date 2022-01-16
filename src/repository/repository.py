from threading import Lock
import os, yaml
import hashlib
import fcntl
import tempfile

from enum import Enum

from file_transfer.exceptions import MessageError, FileDuplicateException
from .file_metadata import FileMetadata, FileStatus


class Singleton(type):

    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class LoadingRepositoryError(MessageError):
    pass


class HashingError(MessageError):
    pass


class RepositoryModificationError(MessageError):
    pass


class NotFoundError(MessageError):
    pass


class Repository:

    _files: dict
    _path: str
    _lock: Lock

    def __init__(self, config=None):
        if not config:
            self._path = os.path.join(tempfile.gettempdir(), "files")
        else:
            self._path = config["path"]
        mode = 0o700
        self._lock = Lock()
        if not os.path.isdir(self._path):
            try:
                os.mkdir(self._path, mode)
            except Exception as e:
                print(e)

    def load(self):
        with self._lock:
            self._files = dict()
            files = [
                f
                for f in os.listdir(self._path)
                if os.path.isfile(os.path.join(self._path, f))
                and os.path.splitext(f)[-1] == ".yaml"
            ]
            for file in files:
                metadata = None
                meta_path = os.path.join(self._path, file)
                with open(meta_path, "r+") as f:
                    loaded = yaml.load(f, Loader=yaml.FullLoader)
                    loaded["status"] = loaded["status"].upper()
                    metadata = FileMetadata(loaded)

                if not os.path.isfile(metadata.path):
                    os.remove(meta_path)
                    # TODO: think this through
                    continue


                metadata = self.__update_metadata(metadata)
                self.__persist_filedata(metadata)

                self._files[metadata.name] = metadata

    def add_file(self, path: str) -> FileMetadata:
        with self._lock:
            if not os.path.isfile(path):
                raise RepositoryModificationError("Is not a file")

            filename = os.path.basename(path)
            if filename in self._files.keys():
                raise RepositoryModificationError(
                    "This file is already in the repository"
                )

            filesize = os.path.getsize(path)

            data = self.__update_metadata(
                FileMetadata(
                    dict(
                        size=filesize,
                        name=filename,
                        path=path,
                        status=FileStatus.READY
                    )
                )
            )
            data.digest = data.current_digest
            data.size = data.current_size
            self._files[filename] = data
            self.__persist_filedata(data)
            return data

    def remove_file(self, filename: str):
        with self._lock:
            if filename not in self._files.keys():
                raise RepositoryModificationError("No such file in repository")
            #if self._files[filename].status == FileStatus.SHARING:
            #    raise RepositoryModificationError("File currently being uploaded")
            del self._files[filename]
            yaml_path = self._path + filename + ".yaml"
            if not os.path.exists(yaml_path):
                raise RepositoryModificationError("Cannot find yaml file")
            os.remove(yaml_path)

    def get_files(self):
        return self._files

    def find(self, filename: str) -> FileMetadata:
        if filename not in self._files.keys():
            raise NotFoundError("File not found")
        return self._files[filename]

    def change_state(self, filename: str, new_status: str = None) -> None:
        with self._lock:
            if filename not in self._files.keys():
                raise NotFoundError("Cannot change state: File not found")
            file_data: FileMetadata = self._files[filename]
            if new_status:
                file_data.status = FileStatus[new_status]
            self._files[filename] = file_data
            self.__persist_filedata(self._files[filename])
    
    def update_stat(self, filename: str) -> FileMetadata:
        meta = self.find(filename)
        return self.__update_metadata(meta)

    def init_meta(self, name, digest, size):
        # TODO: make file downloads separate
        if name in self._files:
            raise FileDuplicateException("File already exists")
        meta = FileMetadata(dict(name=name, digest=digest, size=size, path=os.path.join(self._path, name), status=FileStatus.DOWNLOADING))
        with self._lock:
            self.__update_metadata(meta)
            self.__persist_filedata(meta)
            self._files[name] = meta
        return meta

    def __persist_filedata(self, data: FileMetadata) -> None:
        path = os.path.join(self._path, data.name + ".yaml")
        with open(path, "w") as f:
            yaml.dump(data.as_dict(), f)

    def __update_metadata(self, data: FileMetadata) -> FileMetadata:
        try:
            new_size = os.path.getsize(data.path)
            new_hash = self.__calculate_hash(data.path)
        except:
            new_size = 0
            new_hash = None
        data.current_digest = new_hash
        data.current_size = new_size
        if not data.size:
            data.size = data.current_size
        return data

    def __calculate_hash(self, path: str) -> str:
        sha256_hash = hashlib.sha256()
        if not os.path.isfile(path):
            raise HashingError("Is not a file")
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
