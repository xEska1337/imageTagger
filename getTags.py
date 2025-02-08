import numpy as np
import onnxruntime as onr
import pandas as pd
from PIL import Image

LABEL_FILE_PATH = "tagsModel/selected_tags.csv"
MODEL_FILE_PATH = "tagsModel/model.onnx"
def load_labels(dataframe) -> list[str]:
    name_series = dataframe["name"]
    tag_names = name_series.tolist()

    rating_indexes = list(np.where(dataframe["category"] == 9)[0])
    general_indexes = list(np.where(dataframe["category"] == 0)[0])
    character_indexes = list(np.where(dataframe["category"] == 4)[0])
    return tag_names, rating_indexes, general_indexes, character_indexes

class Predictor:
    def __init__(self):
        self.model_target_size = None
        self.load_model(MODEL_FILE_PATH, LABEL_FILE_PATH)

    def load_model(self, model_path, csv_path):
        tags_df = pd.read_csv(csv_path)
        sep_tags = load_labels(tags_df)

        self.tag_names = sep_tags[0]
        self.rating_indexes = sep_tags[1]
        self.general_indexes = sep_tags[2]
        self.character_indexes = sep_tags[3]

        model = onr.InferenceSession(model_path)
        _, height, width, _ = model.get_inputs()[0].shape
        self.model_target_size = height

        self.model = model

    def prepare_image(self, image):
        target_size = self.model_target_size

        if image.mode != "RGBA":
            image = image.convert("RGBA")

        canvas = Image.new("RGBA", image.size, (255, 255, 255, 0))
        canvas.alpha_composite(image)

        image = canvas.convert("RGB")

        # Pad image to square
        image_shape = image.size
        max_dim = max(image_shape)
        pad_left = (max_dim - image_shape[0]) // 2
        pad_top = (max_dim - image_shape[1]) // 2

        padded_image = Image.new("RGB", (max_dim, max_dim), (255, 255, 255))
        padded_image.paste(image, (pad_left, pad_top))

        # Resize
        if max_dim != target_size:
            padded_image = padded_image.resize(
                (target_size, target_size),
                Image.BICUBIC,
            )

        # Convert to numpy array
        image_array = np.asarray(padded_image, dtype=np.float32)

        # Convert PIL-native RGB to BGR
        image_array = image_array[:, :, ::-1]

        return np.expand_dims(image_array, axis=0)

    def predict(self, image, general_thresh):
        image = self.prepare_image(image)

        input_name = self.model.get_inputs()[0].name
        label_name = self.model.get_outputs()[0].name
        preds = self.model.run([label_name], {input_name: image})[0]

        labels = list(zip(self.tag_names, preds[0].astype(float)))

        # First 4 labels are actually ratings: pick one with argmax
        ratings_names = [labels[i] for i in self.rating_indexes]
        ratings_names = dict(ratings_names)
        ratings_names = sorted(
            ratings_names.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        # Then we have general tags: pick any where prediction confidence > threshold
        general_names = [labels[i] for i in self.general_indexes]
        general_res = [x for x in general_names if x[1] > general_thresh]
        general_res = dict(general_res)

        # Character tags
        character_names = [labels[i] for i in self.character_indexes]
        character_res = [x for x in character_names if x[1] > general_thresh]
        character_res = dict(character_res)
        general_res.update(character_res)

        ratings = "rating:" + ratings_names[0][0]
        if ratings_names[0][0] == "general":
            ratings = "rating:safe"
        general_res[ratings] = ratings_names[0][1]

        general_res = sorted(
            general_res.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return dict(general_res)


# Initialize the predictor object
predictor = Predictor()

def getTag(image_path: str, score_threshold: float):
    image = Image.open(image_path)
    return predictor.predict(image, score_threshold)

