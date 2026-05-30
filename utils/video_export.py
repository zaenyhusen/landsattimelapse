import numpy as np
import cv2
import requests
from PIL import Image
from io import BytesIO

def image_to_numpy(ee_image, aoi, vis_params):
    url = ee_image.getThumbURL({
        'region': aoi,
        'dimensions': 512,
        'format': 'png',
        'min': vis_params['min'],
        'max': vis_params['max'],
    })
    response = requests.get(url)
    img = Image.open(BytesIO(response.content)).convert('RGB')
    return np.array(img)

def frames_to_mp4(frames, output_path, fps=3):
    h, w, _ = frames[0].shape
    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*'avc1'),
        fps, (w, h)
    )
    for frame in frames:
        writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    writer.release()