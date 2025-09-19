from fastapi import FastAPI, UploadFile, File
import cv2
import numpy as np
app = FastAPI()


@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    contents = await file.read()

    np_array = np.frombuffer(contents, np.uint8)

    image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)

    return {
        "filename": file.filename,
        "shape": image.shape if image is not None else None
    }