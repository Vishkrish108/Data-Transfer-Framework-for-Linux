import os
from colors import FG_RED, FG_GREEN, FG_BG_CLEAR

class FS:

    def __init__(self, username):
        if not os.path.exists("./server_storage"):
            os.makedirs("./server_storage")
        self.root_path = os.path.join("./server_storage", username)
        if not os.path.exists(self.root_path):
            os.makedirs(self.root_path)
        self.current_path = self.root_path

    def is_valid_path(self, path):
        path = os.path.normpath(os.path.join(self.current_path, path))
        if os.path.abspath(path).startswith(os.path.abspath(self.root_path)):
            return True
        else:
            return False

    def mkdir(self, directory_path):
        try:
            if not self.is_valid_path(directory_path):
                return f"{FG_RED}Access denied{FG_BG_CLEAR}\n"
            os.makedirs(os.path.normpath(os.path.join(self.current_path, directory_path)))
            return f"{FG_GREEN}Directory created successfully{FG_BG_CLEAR}\n"
        except OSError as error:
            return f"{FG_RED}{str(error)}{FG_BG_CLEAR}\n"

    def rmdir(self, directory_path):
        try:
            if not self.is_valid_path(directory_path):
                return f"{FG_RED}Access denied{FG_BG_CLEAR}\n"
            os.rmdir(os.path.normpath(os.path.join(self.current_path, directory_path)))
            return f"{FG_GREEN}Directory deleted successfully{FG_BG_CLEAR}\n"
        except OSError as error:
            return f"{FG_RED}{str(error)}{FG_BG_CLEAR}\n"

    def rm(self, file_path):
        try:
            if not self.is_valid_path(file_path):
                return f"{FG_RED}Access denied{FG_BG_CLEAR}\n"
            os.remove(os.path.normpath(os.path.join(self.current_path, file_path)))
            return f"{FG_GREEN}File deleted successfully{FG_BG_CLEAR}\n"
        except OSError as error:
            return f"{FG_RED}{str(error)}{FG_BG_CLEAR}\n"

    def cat(self, file_path):
        try:
            if not self.is_valid_path(file_path):
                return f"{FG_RED}Access denied{FG_BG_CLEAR}\n"
            with open(os.path.normpath(os.path.join(self.current_path, file_path)), "rb") as file:
                return file.read(1024).decode("utf-8") + "\n"
        except OSError as error:
            return f"{FG_RED}{str(error)}{FG_BG_CLEAR}\n"
        except UnicodeDecodeError as error:
            return f"{FG_RED}{str(error)}{FG_BG_CLEAR}\n"

    def ls(self, directory_path="./"):
        try:
            if not self.is_valid_path(directory_path):
                return f"{FG_RED}Access denied{FG_BG_CLEAR}\n"
            files = os.listdir(os.path.normpath(os.path.join(self.current_path, directory_path)))
            return "\t".join(files) + "\n"
        except OSError as error:
            return f"{FG_RED}{str(error)}{FG_BG_CLEAR}\n"

    def cd(self, directory_path):
        try:
            if not self.is_valid_path(directory_path):
                return f"{FG_RED}Access denied{FG_BG_CLEAR}\n"
            if not os.path.exists(os.path.normpath(os.path.join(self.current_path, directory_path))):
                return f"{FG_RED}Directory does not exist{FG_BG_CLEAR}\n"
            self.current_path = os.path.normpath(os.path.join(self.current_path, directory_path))
            return f"{FG_GREEN}Directory changed successfully{FG_BG_CLEAR}\n"
        except OSError as error:
            return f"{FG_RED}{str(error)}{FG_BG_CLEAR}\n"

    def get(self, file_path):
        try:
            if not self.is_valid_path(file_path):
                return f"{FG_RED}Access denied{FG_BG_CLEAR}\n"
            with open(os.path.normpath(os.path.join(self.current_path, file_path)), "rb") as file:
                return file.read()
        except OSError as error:
            return f"{FG_RED}{str(error)}{FG_BG_CLEAR}\n"