import hashlib
import os
import requests


def get_md5(filepath):
    md5_hash = hashlib.md5()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)
    return md5_hash.hexdigest()


def download_model(savePath):
    modelUrl = "https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3/resolve/main/model.onnx"

    print("Downloading model...")
    response = requests.get(modelUrl, stream=True)
    if response.status_code == 200:
        with open(savePath, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print("Download complete.")
    else:
        print(f"Failed to download model. Status code: {response.status_code}")


# Check if the file exists and if the MD5 doesn't match
def check_and_download():
    expectedMd5 = "fa418dfbdbc495062a5df911cf5aa6b8"

    os.makedirs("tagsModel", exist_ok=True)
    savePath = os.path.join("tagsModel", "model.onnx")

    if os.path.exists(savePath):
        if expectedMd5 != get_md5(savePath):
            download_model(savePath)
    else:
        download_model(savePath)


if __name__ == "__main__":
    check_and_download()
