import exiftool


def get_metadata(image):
    with exiftool.ExifToolHelper() as et:
        metadata = et.get_metadata(image)
    return metadata


def delete_metadata(image):
    with exiftool.ExifToolHelper() as et:
        et.execute("-all=", "-overwrite_original", image)


def write_tags(image, tags):
    with exiftool.ExifToolHelper() as et:
        et.execute(f"-XMP-dc:Subject={tags}", "-overwrite_original", image)


def write_text(image, text):
    with exiftool.ExifToolHelper() as et:
        et.execute(f"-XMP-dc:Description={text}", "-overwrite_original", image)


def write_comment(image, comment):
    with exiftool.ExifToolHelper() as et:
        et.execute(f"-XMP-exif:UserComment={comment}", "-overwrite_original", image)


def read_tags(image):
    with exiftool.ExifToolHelper() as et:
        tags = et.execute("-XMP-dc:Subject", image)
    return tags.split(":")[1].strip()


def read_text(image):
    with exiftool.ExifToolHelper() as et:
        text = et.execute("-XMP-dc:Description", image)
    return text.split(":")[1].strip()


def read_comment(image):
    with exiftool.ExifToolHelper() as et:
        comment = et.execute("-XMP-exif:UserComment", image)
    return comment.split(":")[1].strip()
