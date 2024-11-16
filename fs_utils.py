import os


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
                return "Access denied"
            os.makedirs(os.path.normpath(os.path.join(self.current_path, directory_path)))
            return "Directory created successfully"
        except OSError as error:
            return str(error)

    def rmdir(self, directory_path):
        try:
            if not self.is_valid_path(directory_path):
                return "Access denied"
            os.rmdir(os.path.normpath(os.path.join(self.current_path, directory_path)))
            return "Directory deleted successfully"
        except OSError as error:
            return str(error)

    def rm(self, file_path):
        try:
            if not self.is_valid_path(file_path):
                return "Access denied"
            os.remove(os.path.normpath(os.path.join(self.current_path, file_path)))
            return "File deleted successfully"
        except OSError as error:
            return str(error)

    def cat(self, file_path):
        try:
            if not self.is_valid_path(file_path):
                return "Access denied"
            with open(os.path.normpath(os.path.join(self.current_path, file_path)), "rb") as file:
                return file.read(1024).decode("utf-8")
        except OSError as error:
            return str(error)
        except UnicodeDecodeError as error:
            return str(error)

    def ls(self, directory_path="./"):
        try:
            if not self.is_valid_path(directory_path):
                return "Access denied"
            files = os.listdir(os.path.normpath(os.path.join(self.current_path, directory_path)))
            return "\t".join(files)
        except OSError as error:
            return str(error)

    def cd(self, directory_path):
        try:
            if not self.is_valid_path(directory_path):
                return "Access denied"
            self.current_path = os.path.normpath(os.path.join(self.current_path, directory_path))
            return "Directory changed successfully"
        except OSError as error:
            return str(error)

    def get(self, file_path):
        try:
            if not self.is_valid_path(file_path):
                return "Access denied"
            with open(os.path.normpath(os.path.join(self.current_path, file_path)), "rb") as file:
                return file.read()
        except OSError as error:
            return str(error)