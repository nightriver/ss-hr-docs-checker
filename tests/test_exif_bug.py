import io
import random
from PIL import Image
from image_tools import compress_image

def test_exif_size_guard_bug_with_noise():
    # Create 100x40 image with random noise
    img = Image.new("RGB", (100, 40))
    pixels = img.load()
    random.seed(42)
    for x in range(100):
        for y in range(40):
            pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            
    buf = io.BytesIO()
    exif = img.getexif()
    exif[0x0112] = 6 # Orientation 6 (Rotate 90 CW -> should be 40x100)
    # Save with low quality so original file is small
    img.save(buf, format="JPEG", quality=30, exif=exif)
    small_noisy_jpeg = buf.getvalue()
    
    orig_len = len(small_noisy_jpeg)
    print(f"Original noisy JPEG size: {orig_len} bytes, dims: (100, 40), EXIF orientation: 6")

    # Run compress_image
    out_bytes, ext = compress_image(small_noisy_jpeg, "photo.jpg", target_bytes=2097152)
    res_img = Image.open(io.BytesIO(out_bytes))
    print(f"Output JPEG size: {len(out_bytes)} bytes, dims: {res_img.size}, ext: '{ext}'")

    if res_img.size == (100, 40):
        print("-> CRITICAL BUG CONFIRMED: Size Increase Guard returned original un-transposed JPEG! Image orientation remains incorrect (100, 40)!")
    elif res_img.size == (40, 100):
        print("-> Transposed to (40, 100) successfully.")

if __name__ == "__main__":
    test_exif_size_guard_bug_with_noise()
