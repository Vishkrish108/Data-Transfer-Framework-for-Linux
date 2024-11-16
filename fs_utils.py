import os


class FS:

    def __init__(self, username):
        if not os.path.exists("./server_storage"):
            os.makedirs("./server_storage")
        self.Client_Directory = os.path.join("./server_storage", username)
        if not os.path.exists(self.Client_Directory):
            os.makedirs(self.Client_Directory)

    def mkdir(self, directory_path):
        try:
            os.makedirs(os.path.join(self.Client_Directory, directory_path))
            return "Directory created successfully"
        except OSError as error:
            return str(error)

    def rmdir(self, directory_path):
        try:
            os.rmdir(os.path.join(self.Client_Directory, directory_path))
            return "Directory deleted successfully"
        except OSError as error:
            return str(error)

    def rm(self, file_path):
        try:
            os.remove(os.path.join(self.Client_Directory, file_path))
            return "File deleted successfully"
        except OSError as error:
            return str(error)

    def cat(self, file_path):
        try:
            with open(os.path.join(self.Client_Directory, file_path), "rb") as file:
                return file.read(1024)
        except OSError as error:
            return str(error)

    def ls(self, directory_path="./"):
        try:
            files = os.listdir(os.path.join(self.Client_Directory, directory_path))
            return "\t".join(files)
        except OSError as error:
            return str(error)

    def cd(self, directory_path):
        try:
            os.chdir(os.path.join(self.Client_Directory, directory_path))
            return "Directory changed successfully"
        except OSError as error:
            return str(error)

    def get(self, file_path):
        try:
            with open(os.path.join(self.Client_Directory, file_path), "rb") as file:
                return file.read()
        except OSError as error:
            return str(error)
