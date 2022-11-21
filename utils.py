import ntpath


def file_name(file_path):
    head, tail = ntpath.split(file_path)
    return tail or ntpath.basename(head)
