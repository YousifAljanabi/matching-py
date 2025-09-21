# # normal_phone.py
# import os
# import cv2
# import numpy as np
# import base64
# from skimage.filters import threshold_sauvola
# from PIL import Image
# from fastapi import APIRouter, File, UploadFile, HTTPException
#
# from app.modules.normalize_phone.utils.normalization import normalize as iitk_normalize
# from app.modules.normalize_phone.utils.segmentation import create_segmented_and_variance_images
# from app.modules.normalize_phone.utils.orientation import calculate_angles
# from app.modules.normalize_phone.utils.frequency import ridge_freq
# from .utils.gabor_filter import gabor_filter
#
# # -------------------------
# # Utilities
# # -------------------------
# def to_gray(img: np.ndarray) -> np.ndarray:
#     if img.ndim == 3:
#         img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#     return img
#
# def pad_to_square(img: np.ndarray, size: int = 512) -> np.ndarray:
#     h, w = img.shape[:2]
#     scale = size / max(h, w)
#     new_w, new_h = int(round(w * scale)), int(round(h * scale))
#     resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
#     canvas = np.full((size, size), 255, dtype=np.uint8)
#     x0 = (size - new_w) // 2
#     y0 = (size - new_h) // 2
#     canvas[y0:y0+new_h, x0:x0+new_w] = resized
#     return canvas
#
# def remove_background(img: np.ndarray, sigma: int = 35) -> np.ndarray:
#     f = img.astype(np.float32)
#     bg = cv2.GaussianBlur(f, (0, 0), sigma)
#     diff = cv2.subtract(f, bg)
#     norm = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
#     return norm.astype(np.uint8)
#
# def enhance_contrast(img: np.ndarray, clip_limit=2.0, tile_grid_size=(4, 4)) -> np.ndarray:
#     clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
#     return clahe.apply(img)
#
# def unsharp_mask(img, ksize=(5, 5), amount=1.5):
#     blur = cv2.GaussianBlur(img, ksize, 0)
#     return cv2.addWeighted(img, 1 + amount, blur, -amount, 0)
#
# def adaptive_binarize(img):
#     win_size = 25
#     thresh = threshold_sauvola(img, window_size=win_size)
#     binary = (img > thresh).astype(np.uint8) * 255
#     return binary
#
# def deskew(img: np.ndarray) -> np.ndarray:
#     coords = np.column_stack(np.where(img > 0))
#     if coords.size == 0:
#         return img
#     angle = cv2.minAreaRect(coords)[-1]
#     if angle < -45:
#         angle = -(90 + angle)
#     else:
#         angle = -angle
#     (h, w) = img.shape[:2]
#     M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
#     return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC,
#                           borderMode=cv2.BORDER_REPLICATE)
#
# def _fingerprint_bbox(binary_img: np.ndarray) -> tuple[int, int, int, int]:
#     """Estimate bounding box of the fingerprint area on a binary/near-binary image.
#     Assumes background is mostly white. Returns (x, y, w, h).
#     Fallbacks to center box if nothing is found.
#     """
#     h, w = binary_img.shape[:2]
#     # Consider anything not white as foreground
#     mask = (binary_img < 250).astype(np.uint8) * 255
#     if mask.sum() == 0:
#         # fallback: center box
#         cw, ch = int(w * 0.6), int(h * 0.6)
#         cx, cy = w // 2, h // 2
#         return max(0, cx - cw // 2), max(0, cy - ch // 2), cw, ch
#
#     # Connect ridges and remove tiny noise
#     kernel = np.ones((5, 5), np.uint8)
#     mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
#     mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
#
#     cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#     if not cnts:
#         cw, ch = int(w * 0.6), int(h * 0.6)
#         cx, cy = w // 2, h // 2
#         return max(0, cx - cw // 2), max(0, cy - ch // 2), cw, ch
#
#     c = max(cnts, key=cv2.contourArea)
#     x, y, bw, bh = cv2.boundingRect(c)
#     return x, y, bw, bh
#
# def crop_upper_two_thirds(img: np.ndarray, ref_for_bbox: np.ndarray | None = None,
#                           zoom_factor: float = 1.15, pad: int = 8) -> np.ndarray:
#     """Crop a zoomed region centered on the fingerprint and keep only the upper 2/3.
#
#     - ref_for_bbox: image used to detect bbox (binary preferred). If None, uses img.
#     - zoom_factor > 1.0: values slightly >1 reduce the bbox (zoom in).
#     - pad: small margin around the crop.
#     """
#     src = ref_for_bbox if ref_for_bbox is not None else img
#     if src.ndim == 3:
#         src_gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
#     else:
#         src_gray = src
#
#     x, y, bw, bh = _fingerprint_bbox(src_gray)
#
#     # Zoom: shrink bbox around its center
#     cx, cy = x + bw / 2.0, y + bh / 2.0
#     zw, zh = int(round(bw / zoom_factor)), int(round(bh / zoom_factor))
#     zx, zy = int(round(cx - zw / 2.0)), int(round(cy - zh / 2.0))
#
#     # Keep only upper 2/3 of the zoomed bbox
#     upper_h = int(round(zh * (2.0 / 3.0)))
#     x1 = max(0, zx - pad)
#     y1 = max(0, zy - pad)
#     x2 = min(img.shape[1], zx + zw + pad)
#     y2 = min(img.shape[0], zy + upper_h + pad)
#
#     # Guard against invalid ranges
#     if x2 <= x1 or y2 <= y1:
#         return img.copy()
#     return img[y1:y2, x1:x2].copy()
#
# def preprocess_phone_capture(img, size=512):
#     gray = to_gray(img)
#     gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
#     return pad_to_square(gray, size)
#
# def save_with_dpi(path, arr, dpi=(500, 500)):
#     im = Image.fromarray(arr)
#     im.save(path, dpi=dpi)
#
# # -------------------------
# # Phone capture pipeline
# # -------------------------
# def phone_pipeline(img: np.ndarray, block_size: int = 16):
#     pre = preprocess_phone_capture(img)
#     nobg = remove_background(pre)
#     contrast = enhance_contrast(nobg)
#     sharpened = unsharp_mask(contrast)
#     binary = adaptive_binarize(sharpened)
#     aligned = deskew(binary)
#
#     # Crop: zoom on center and keep upper 2/3 of the fingerprint
#     aligned_upper23 = crop_upper_two_thirds(aligned, ref_for_bbox=aligned,
#                                             zoom_factor=1.15, pad=8)
#
#     normalized = iitk_normalize(aligned.copy(), 100.0, 100.0)
#     segmented, normim, mask = create_segmented_and_variance_images(normalized, block_size, 0.2)
#     angles = calculate_angles(normalized, W=block_size, smoth=False)
#     freq = ridge_freq(normim, mask, angles, block_size,
#                       kernel_size=5, minWaveLength=5, maxWaveLength=15)
#
#     gabor_img = gabor_filter(normim, angles, freq)
#     gabor_img = np.nan_to_num(gabor_img)
#     gabor_img = cv2.normalize(gabor_img, None, 0, 255,
#                               cv2.NORM_MINMAX).astype(np.uint8)
#
#     # Also provide a cropped version of the final skeleton-like output
#     skeleton_upper23 = crop_upper_two_thirds(gabor_img, ref_for_bbox=aligned,
#                                              zoom_factor=1.15, pad=8)
#
#     return {
#         "preprocessed": pre,
#         "background_removed": nobg,
#         "contrast_enhanced": contrast,
#         "sharpened": sharpened,
#         "binary": binary,
#         "aligned": aligned,
#         "aligned_upper23": aligned_upper23,
#         "skeleton": gabor_img,
#         "skeleton_upper23": skeleton_upper23,
#     }
#
# def phone_pipeline_base64(img: np.ndarray, block_size: int = 16) -> str:
#     pre = preprocess_phone_capture(img)
#     nobg = remove_background(pre)
#     contrast = enhance_contrast(nobg)
#     sharpened = unsharp_mask(contrast)
#     binary = adaptive_binarize(sharpened)
#     aligned = deskew(binary)
#
#     normalized = iitk_normalize(aligned.copy(), 100.0, 100.0)
#     segmented, normim, mask = create_segmented_and_variance_images(normalized, block_size, 0.2)
#     angles = calculate_angles(normalized, W=block_size, smoth=False)
#     freq = ridge_freq(normim, mask, angles, block_size,
#                       kernel_size=5, minWaveLength=5, maxWaveLength=15)
#
#     gabor_img = gabor_filter(normim, angles, freq)
#     gabor_img = np.nan_to_num(gabor_img)
#     gabor_img = cv2.normalize(gabor_img, None, 0, 255,
#                               cv2.NORM_MINMAX).astype(np.uint8)
#
#     # Convert to base64
#     _, buffer = cv2.imencode('.png', gabor_img)
#     img_base64 = base64.b64encode(buffer).decode('utf-8')
#
#     return img_base64
#
# # -------------------------
# # FastAPI Router
# # -------------------------
# router = APIRouter(prefix="/normalize-phone", tags=["normalize-phone"])
#
# @router.post("/enhance_phone")
# async def enhance_fingerprint(file: UploadFile = File(...)):
#     try:
#         # Read uploaded file
#         contents = await file.read()
#         nparr = np.frombuffer(contents, np.uint8)
#         img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#
#         if img is None:
#             raise HTTPException(status_code=400, detail="Invalid image file")
#
#         # Rotate image 90 degrees clockwise
#         rotated_img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
#
#         # Process image and get base64 result
#         enhanced_image_base64 = phone_pipeline_base64(rotated_img)
#
#         return {
#             "status": "success",
#             "enhanced_image": enhanced_image_base64
#         }
#
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
#
# # -------------------------
# # Augmentations
# # -------------------------
# def generate_rotations_and_flips(img: np.ndarray):
#     """Generate rotated and flipped variants."""
#     results = {}
#     for angle in [90, 180, 270]:
#         rot = cv2.rotate(img, {
#             90: cv2.ROTATE_90_CLOCKWISE,
#             180: cv2.ROTATE_180,
#             270: cv2.ROTATE_90_COUNTERCLOCKWISE
#         }[angle])
#         results[f"rot{angle}"] = rot
#         results[f"rot{angle}_flip"] = cv2.flip(rot, 1)  # horizontal flip
#     return results
#
# # -------------------------
# # CLI
# # -------------------------
# if __name__ == "__main__":
#     import argparse
#     ap = argparse.ArgumentParser()
#     ap.add_argument("--input", required=True, help="Path to fingerprint image (phone capture on paper)")
#     ap.add_argument("--outdir", default="out_phone", help="Output directory")
#     args = ap.parse_args()
#
#     os.makedirs(args.outdir, exist_ok=True)
#     img = cv2.imread(args.input, cv2.IMREAD_UNCHANGED)
#     if img is None:
#         raise FileNotFoundError(f"Could not read {args.input}")
#
#     outputs = phone_pipeline(img)
#     stem = os.path.splitext(os.path.basename(args.input))[0]
#
#     # Save main pipeline outputs
#     for key, arr in outputs.items():
#         save_with_dpi(os.path.join(args.outdir, f"{stem}_{key}.png"), arr)
#
#     # Generate rotations + flips of final skeleton
#     augments = generate_rotations_and_flips(outputs["skeleton"])
#     for key, arr in augments.items():
#         save_with_dpi(os.path.join(args.outdir, f"{stem}_{key}.png"), arr)
#
#     print(f"[OK] Saved results in {os.path.abspath(args.outdir)}")
