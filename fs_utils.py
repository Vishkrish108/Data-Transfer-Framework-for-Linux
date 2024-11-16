import os


class FS:

    def __init__(self, username):
        if not os.path.exists("./server_storage"):
            os.makedirs("./server_storage")
        self.root_path = os.path.join("./server_storage", username)
        if not os.path.exists(self.root_path):
            os.makedirs(self.root_path)
        self.current_path = self.root_path

    def mkdir(self, directory_path):
        try:
            os.makedirs(os.path.join(self.current_path, directory_path))
            return "Directory created successfully"
        except OSError as error:
            return str(error)

    def rmdir(self, directory_path):
        try:
            os.rmdir(os.path.join(self.current_path, directory_path))
            return "Directory deleted successfully"
        except OSError as error:
            return str(error)

    def rm(self, file_path):
        try:
            os.remove(os.path.join(self.current_path, file_path))
            return "File deleted successfully"
        except OSError as error:
            return str(error)

    def cat(self, file_path):
        try:
            with open(os.path.join(self.current_path, file_path), "rb") as file:
                return file.read(1024)
        except OSError as error:
            return str(error)

    def ls(self, directory_path="./"):
        try:
            files = os.listdir(os.path.join(self.current_path, directory_path))
            return "\t".join(files)
        except OSError as error:
            return str(error)

    def cd(self, directory_path):
        try:
            new_path = os.path.normpath(os.path.join(self.current_path, directory_path))
            if not os.path.abspath(new_path).startswith(os.path.abspath(self.root_path)):
                return "Access denied"
            self.current_path = new_path
            return "Directory changed successfully"
        except OSError as error:
            return str(error)

    def get(self, file_path):
        try:
            with open(os.path.join(self.current_path, file_path), "rb") as file:
                return file.read()
        except OSError as error:
            return str(error)