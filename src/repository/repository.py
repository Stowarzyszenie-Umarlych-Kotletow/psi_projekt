from threading import Lock
import os, yaml
import hashlib
import logging
from pathlib import Path

from common.config import MAX_FILENAME_LENGTH, YAML_EXTENSION, METADATA_FOLDER_NAME
from common.exceptions import (
    LogicError,
    FileDuplicateException,
    FileNameTooLongException,
)
from common.models import FileMetadata, FileStatus


class LoadingRepositoryError(LogicError):
    pass


class HashingError(LogicError):
    pass


class RepositoryModificationError(LogicError):
    pass


class NotFoundError(LogicError):
    pass


class Repository:

    _files: dict
    _path: str
    _meta_path: str
    _lock: Lock

    def __init__(self, config=None):
        self.logger = logging.getLogger("Repository")
        if not config:
            self._path = os.path.join(Path.home(), "Downloads", "simplep2p")
        else:
            self._path = config["path"]
            self.logger.info("Custom path set: %s", config["path"])
        self._lock = Lock()
        self.__check_and_create()

    def load(self):
        with self._lock:
            self._files = dict()
            files = [
                f
                for f in os.listdir(self._meta_path)
                if os.path.isfile(os.path.join(self._meta_path, f))
                and os.path.splitext(f)[-1] == YAML_EXTENSION
            ]
            for file in files:
                metadata = None
                meta_path = os.path.join(self._meta_path, file)
                with open(meta_path, "r+") as f:
                    loaded = yaml.load(f, Loader=yaml.FullLoader)
                    loaded["status"] = loaded["status"].upper()
                    metadata = FileMetadata(loaded)

                if not os.path.isfile(metadata.path):
                    self.logger.warn(
                        "Could not find file %s while loading repository. Removing metadata.",
                        metadata.path,
                    )
                    os.remove(meta_path)
                    continue

                metadata = self.__update_metadata(metadata)
                
                if metadata.status == FileStatus.READY and not metadata.is_valid:
                    # the file is no longer valid
                    self.logger.warn("File %s is no longer valid.", metadata.name)
                    metadata.status = FileStatus.INVALID
                
                self.__persist_filedata(metadata)

                self._files[metadata.name] = metadata
            self.logger.info("Repository loaded successfully.")

    def add_file(self, path: str) -> FileMetadata:
        with self._lock:
            if not os.path.isfile(path):
                raise RepositoryModificationError("Is not a file")

            filename = os.path.basename(path)
            if len(filename) > MAX_FILENAME_LENGTH:
                raise FileNameTooLongException(
                    f"File name exceeds {MAX_FILENAME_LENGTH} characters"
                )
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
                        status=FileStatus.READY,
                    )
                )
            )
            data.digest = data.current_digest
            self._files[filename] = data
            self.__persist_filedata(data)
            return data

    def remove_file(self, filename: str):
        with self._lock:
            if filename not in self._files.keys():
                raise RepositoryModificationError("No such file in repository")
            del self._files[filename]
            yaml_path = os.path.join(self._meta_path, filename + YAML_EXTENSION)
            if os.path.exists(yaml_path):
                os.remove(yaml_path)
                self.logger.info("File: %s removed successfully", filename)
            else:
                self.logger.warn(
                    "File %s could not be removed. It does not exist", filename
                )

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
        if name in self._files:
            raise FileDuplicateException("File already exists")
        meta = FileMetadata(
            dict(
                name=name,
                digest=digest,
                size=size,
                path=os.path.join(self._path, name),
                status=FileStatus.DOWNLOADING,
            )
        )
        with self._lock:
            self.__update_metadata(meta)
            self.__persist_filedata(meta)
            self._files[name] = meta
        return meta

    def __check_and_create(self, mode=0o777) -> None:
        if not os.path.isdir(self._path):
            try:
                os.makedirs(self._path, mode, exist_ok=True)
            except Exception as e:
                self.logger.error(
                    "Could not create application folder in %s", self._path
                )
                raise RepositoryModificationError("Could not create folder")
        if not os.path.isdir(self._meta_path):
            try:
                os.mkdir(os.path.join(self._path, METADATA_FOLDER_NAME))
            except Exception as e:
                self.logger.error(
                    "Could not create application metadata folder in %s",
                    self._meta_path,
                )
                raise RepositoryModificationError("Could not create metadata folder")

    def __persist_filedata(self, data: FileMetadata) -> None:
        filename: str = data.name + YAML_EXTENSION
        path = os.path.join(self._meta_path, filename)
        with open(path, "w") as f:
            yaml.dump(data.as_dict(), f)
        self.logger.debug("Metadata %s persisted successfully", data.name)

    def __update_metadata(self, data: FileMetadata) -> FileMetadata:
        try:
            new_size = os.path.getsize(data.path)
            new_hash = self.__calculate_hash(data.path)
        except OSError as e:
            self.logger.debug("Could not find file %s", data.path, exc_info=e)
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

    @property
    def _meta_path(self):
        return os.path.join(self._path, METADATA_FOLDER_NAME)
