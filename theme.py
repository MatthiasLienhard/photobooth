import os
class ThemeException(Exception):
    """Custom exception class to handle Theme class errors"""

class Theme:
    def __init__(self, name="default", stem="themes/"):
        self.name=name
        self.stem=stem

    def get_file_name(self, what="mainpage"):
        specific=self.stem + self.name + '/' + what + ".png"
        default=self.stem + 'default/' + what + ".png"
        if os.path.isfile(specific):
            return specific
        elif os.path.isfile(default):
            return default
        else:
            raise ThemeException(what +" theme not found, neither for " +self.name+" nor default")



