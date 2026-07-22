import io
from PIL import Image
from image_tools import compress_image

def test_when_size_guard_triggers():
    # Scenario 1: Small RGBA PNG where converting to JPEG Q95 makes file larger
    # Create a small 50x50 PNG with RGBA mode
    img = Image.new("RGBA", (50, 50), (255, 0, 0, 100))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    small_png = buf.getvalue()
    print(f"Small RGBA PNG size: {len(small_png)} bytes, mode: RGBA")

    out_bytes, ext = compress_image(small_png, "small_icon.png", target_bytes=2097152)
    res_img = Image.open(io.BytesIO(out_bytes))
    print(f"Result size: {len(out_bytes)} bytes, mode: {res_img.mode}, ext: '{ext}'")

    if res_img.mode == "RGBA":
        print("-> BUG CONFIRMED: Size Increase Guard returned original RGBA PNG bytes when JPEG encoding increased size!")
    elif res_img.mode == "RGB":
        print("-> Flattened to RGB successfully.")

    # Scenario 2: Small JPEG with EXIF orientation 6 where original size < re-encoded size
    img_exif = Image.new("RGB", (100, 50), (120, 130, 140))
    buf_exif = io.BytesIO()
    exif = img_exif.getexif()
    exif[0x0112] = 6 # Orientation 6
    img_exif.save(buf_exif, format="JPEG", quality=20, exif=exif) # highly compressed original
    small_exif_jpeg = buf_exif.getvalue()
    print(f"\nSmall JPEG with EXIF 6 size: {len(small_exif_jpeg)} bytes, dims: 100x50")

    out_exif_bytes, ext_exif = compress_image(small_exif_jpeg, "small_photo.jpg", target_bytes=2097152)
    res_exif_img = Image.open(io.BytesIO(out_exif_bytes))
    print(f"Result size: {len(out_exif_bytes)} bytes, dims: {res_exif_img.size}, ext: '{ext_exif}'")

    if res_exif_img.size == (100, 50):
        print("-> BUG CONFIRMED: Size Increase Guard returned original un-transposed JPEG! Transposition (50, 100) was lost!")
    elif res_exif_img.size == (50, 100):
        print("-> Transposed to (50, 100) successfully.")

if __name__ == "__main__":
    test_when_size_guard_triggers()
