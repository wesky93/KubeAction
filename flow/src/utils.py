from os import walk


def files_list(_path: str):
    f = []
    for (_, _, filenames) in walk(_path):
        f.extend(filenames)
        break
    return f
