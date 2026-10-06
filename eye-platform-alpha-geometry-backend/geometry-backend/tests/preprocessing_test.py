import os
import resource
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw

from app.image_preprocessing import prepare_reconstruction_image


os.environ["EYE_LOCAL_SEGMENTATION"] = "0"

with TemporaryDirectory() as temporary:
    root = Path(temporary)
    source = root / "iphone-12mp.jpg"
    image = Image.new("RGB", (4032, 3024), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((900, 450, 3100, 2700), fill=(30, 90, 160))
    exif = Image.Exif()
    exif[274] = 6
    image.save(source, format="JPEG", quality=88, exif=exif)
    image.close()

    prepared, report = prepare_reconstruction_image(source, root, "STANDARD", "preprocess-test")
    with Image.open(prepared) as output:
        assert output.format == "JPEG"
        assert output.mode == "RGB"
        assert output.width <= 1280 and output.height <= 1280
        assert output.height > output.width
    assert report.source_dimensions == (4032, 3024)
    assert report.output_dimensions == (960, 1280)
    assert report.foreground_segmenter == "bypassed_resource_safe"
    assert report.object_crop_applied is False
    peak_rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    assert peak_rss_mib < 512, f"preprocessing peak RSS was {peak_rss_mib:.1f} MiB"
    assert prepared.stat().st_size < 2 * 1024 * 1024
    print({"preprocessing": "PASS", "input_dimensions": report.source_dimensions, "output_dimensions": report.output_dimensions, "segmenter": report.foreground_segmenter, "peak_rss_mib": round(peak_rss_mib, 1)})
    prepared.unlink(missing_ok=True)