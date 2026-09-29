import argparse
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
IMAGES_DIR = ROOT / "images"
DOCS_DIR = ROOT / "data" / "docs 2025"
CATALOG_PATH = DATA_DIR / "catalog_data.csv"
IMAGE_MAP_PATH = DATA_DIR / "image_serial_map.json"
SOURCE_LIST = DOCS_DIR / "List 2025.docx"
SOURCE_PHOTOS = DOCS_DIR / "GSC - SK Catlog Photo.docx"
UNASSIGNED_DIR = DOCS_DIR / "source images without serial"


def digest(content):
    return hashlib.sha256(content).hexdigest()


def normalized(value):
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def compact_ranges(values, minimum_width=1):
    numbers = sorted(set(int(value) for value in values))
    ranges = []
    for number in numbers:
        if ranges and number == ranges[-1][1] + 1:
            ranges[-1][1] = number
        else:
            ranges.append([number, number])
    compact = ",".join(
        f"{start:0{minimum_width}d}"
        if start == end
        else f"{start:0{minimum_width}d}-{end:0{minimum_width}d}"
        for start, end in ranges
    )
    if len(compact) > 40:
        return f"{numbers[0]:0{minimum_width}d}-{numbers[-1]:0{minimum_width}d}_span"
    return compact


def photo_serials(label, products):
    text = normalized(label)
    if "pvcsealerautomaticmachineparts" in text:
        return [
            row for row in products
            if row["category"] == "PVC Sealer Automatic Machine & Parts"
        ]
    if "pvcpipe" in text:
        return [row for row in products if row["sr_number"] == "72"]
    if "pvccordblack" in text:
        return [row for row in products if row["sr_number"] == "71"]
    if "tinnedcopperfusewire" in text:
        return [row for row in products if row["sr_number"] == "280"]
    if "fan canopy" in label.casefold():
        return [row for row in products if 334 <= int(row["sr_number"]) <= 337]
    if "capacitor" in text:
        return [row for row in products if 298 <= int(row["sr_number"]) <= 333]
    if "cotton tapelotus" in text:
        return [row for row in products if 420 <= int(row["sr_number"]) <= 422]
    if "superfinecottontape" in text:
        return [row for row in products if 423 <= int(row["sr_number"]) <= 425]
    if "webbingcottontape" in text:
        return [row for row in products if row["sr_number"] == "426"]
    if "plumbertape" in text:
        return [row for row in products if row["sr_number"] == "379"]
    if "pvcheatsealing" in text:
        return [row for row in products if row["sr_number"] == "380"]
    if "pvcadhesive" in text or "steelgrip" in text:
        return [row for row in products if 381 <= int(row["sr_number"]) <= 385]
    if "fibreglassunvarnishedtape" in text:
        return [row for row in products if 386 <= int(row["sr_number"]) <= 395]
    if "rubbersubmersibletape" in text:
        return [row for row in products if 396 <= int(row["sr_number"]) <= 400]
    if "fiberglassvarnishedcable" in text or "fibreglassvarnishedcable" in text:
        return [row for row in products if row["sr_number"] in {"247", "259"}]
    if "coolingfan" in text:
        return [row for row in products if "cooling fan" in row["item_name"].casefold()]
    if "coolerfangrill" in text:
        return [row for row in products if "cooler fan grill" in row["item_name"].casefold()]

    matches = [
        row for row in products
        if normalized(label) in normalized(row["item_name"])
        or normalized(row["item_name"]) in normalized(label)
    ]
    return matches


def load_products():
    with CATALOG_PATH.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def load_price_list_images():
    extractor_path = ROOT / "tools" / "extract" / "extract_smart_v2.py"
    spec = importlib.util.spec_from_file_location("catalog_image_extractor", extractor_path)
    extractor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(extractor)
    by_hash = defaultdict(set)
    temporary_dir = tempfile.TemporaryDirectory(prefix="catalog-source-media-")
    try:
        parser = extractor.TableParser(SOURCE_LIST)
        parser.images_dir = Path(temporary_dir.name)
        with contextlib.redirect_stdout(io.StringIO()):
            parser.process()
        for item in parser.items:
            if not item["image_ref"].startswith("sr_"):
                continue
            for path in Path(temporary_dir.name).glob(item["image_ref"] + ".*"):
                by_hash[digest(path.read_bytes())].add(item["sr_number"])
    finally:
        temporary_dir.cleanup()
    return by_hash


def load_photo_document_images():
    document = Document(SOURCE_PHOTOS)
    images = {}
    for row_number, row in enumerate(document.tables[0].rows):
        for cell_number, cell in enumerate(row.cells):
            label = " ".join(cell.text.split())
            for blip in cell._element.xpath(".//a:blip"):
                relationship = blip.get(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
                )
                if not relationship:
                    continue
                part = document.part.related_parts[relationship]
                content = part.blob
                image_hash = digest(content)
                record = images.setdefault(image_hash, {
                    "content": content,
                    "extension": part.content_type.rsplit("/", 1)[-1],
                    "label": label,
                    "source_row": row_number,
                    "source_cell": cell_number,
                })
                if not record["label"] and label:
                    record["label"] = label
    return images


def image_mapping(rows, method, source_document, source_label=""):
    serials = sorted({str(row["sr_number"]) for row in rows}, key=lambda value: tuple(int(part) for part in str(value).split(".")))
    if not serials:
        raise ValueError(f"Image has no mapped product serials: {source_label!r}")
    return serials


def image_identity_prefix(rows):
    serials = sorted({int(row["sr_number"]) for row in rows})
    groups = sorted({int(row["group_number"]) for row in rows})
    if len(serials) == 1:
        row = rows[0]
        return (
            f"sr_{serials[0]:04d}_group_{int(row['group_number']):04d}_"
            f"item_{int(row['item_number']):04d}"
        )
    serial_text = compact_ranges(serials, minimum_width=4)
    if len(groups) == 1:
        item_text = compact_ranges(
            {int(row["item_number"]) for row in rows},
            minimum_width=4,
        )
        return f"group_{groups[0]:04d}_items_{item_text}_sr_{serial_text}"
    return f"groups_{compact_ranges(groups, minimum_width=4)}_sr_{serial_text}"


def image_name(rows, source_label, source_row, source_cell, image_hash):
    prefix = image_identity_prefix(rows)
    source_slug = re.sub(r"[^a-z0-9]+", "_", source_label.casefold()).strip("_")[:32]
    source_location = (
        "source_asset"
        if source_row < 0
        else f"source_photo_r{source_row + 1}c{source_cell + 1}"
    )
    return (
        f"{prefix}_{source_location}_"
        f"{image_hash[:8]}_{source_slug}"
    ).rstrip("_")


def main():
    parser = argparse.ArgumentParser(
        description="Map extracted source photos to stable serials and group/item IDs."
    )
    parser.add_argument("--apply", action="store_true", help="Rename/extract images and update the image map.")
    args = parser.parse_args()

    products = load_products()
    by_serial = {row["sr_number"]: row for row in products}
    image_map = json.loads(IMAGE_MAP_PATH.read_text(encoding="utf-8"))
    for key, mapping in image_map.items():
        image_map[key] = sorted(set(mapping), key=lambda value: tuple(int(part) for part in str(value).split(".")))
    price_hashes = load_price_list_images()
    photo_images = load_photo_document_images()
    current_images = [path for path in IMAGES_DIR.iterdir() if path.is_file()]
    current_hashes = defaultdict(list)
    for path in current_images:
        current_hashes[digest(path.read_bytes())].append(path)

    operations = []
    original_image_map = dict(image_map)
    renamed_mapped = {}
    orphan_count = 0
    for path in current_images:
        if path.stem in original_image_map:
            mapping = original_image_map[path.stem]
            mapped_rows = [by_serial[str(serial)] for serial in mapping if str(serial) in by_serial]
            expected_prefix = image_identity_prefix(mapped_rows)
            if not path.stem.startswith(expected_prefix + "_"):
                suffix_match = re.search(r"_sr_[\d,-]+_(.+)$", path.stem)
                if not suffix_match:
                    raise ValueError(
                        f"Cannot preserve the descriptive suffix for mapped image {path.name!r}."
                    )
                target_stem = f"{expected_prefix}_{suffix_match.group(1)}"
                target = path.with_name(target_stem + path.suffix.lower())
                if target.exists():
                    raise FileExistsError(f"Image rename would overwrite {target.name}.")
                operations.append((path, target))
                renamed_mapped[path.stem] = target_stem
            continue
        image_hash = digest(path.read_bytes())
        serials = price_hashes.get(image_hash)
        source_document = "List 2025.docx"
        label = ""
        method = "exact embedded image content match"
        if not serials and image_hash in photo_images:
            photo = photo_images[image_hash]
            label = photo["label"]
            matched_products = photo_serials(label, products)
            serials = {row["sr_number"] for row in matched_products}
            source_document = "GSC - SK Catlog Photo.docx"
            method = "source photo category label mapped to catalog rows"
        if not serials:
            if path.stem.startswith("item_") and not path.stem[5:].isdigit():
                continue
            raise ValueError(f"Cannot assign an sr_number to unreferenced image {path.name!r}.")
        rows = [by_serial[serial] for serial in sorted(serials, key=int)]
        target_stem = image_name(rows, path.stem or label, -1, -1, image_hash)
        target = path.with_name(target_stem + path.suffix.lower())
        if target != path:
            if target.exists():
                raise FileExistsError(f"Image mapping would overwrite {target.name}.")
            operations.append((path, target))
        image_map[target_stem] = image_mapping(rows, method, source_document, path.stem or label)
        orphan_count += 1

    for old_stem, new_stem in renamed_mapped.items():
        image_map[new_stem] = original_image_map[old_stem]
        image_map.pop(old_stem, None)

    extracted_count = 0
    for image_hash, photo in photo_images.items():
        if image_hash in current_hashes:
            continue
        rows = photo_serials(photo["label"], products)
        if not rows:
            raise ValueError(
                f"Source-photo row {photo['source_row'] + 1}, cell "
                f"{photo['source_cell'] + 1} has no serial mapping: {photo['label']!r}"
            )
        target_stem = image_name(
            rows, photo["label"], photo["source_row"], photo["source_cell"], image_hash
        )
        extension = photo["extension"].lower()
        if extension == "jpeg":
            extension = "jpg"
        target = IMAGES_DIR / f"{target_stem}.{extension}"
        if target.exists():
            raise FileExistsError(f"Source-photo extraction would overwrite {target.name}.")
        operations.append((None, target, photo["content"]))
        image_map[target_stem] = image_mapping(
            rows,
            "category caption in source photo document",
            "GSC - SK Catlog Photo.docx",
            photo["label"],
        )
        extracted_count += 1

    unassigned = [
        path for path in current_images
        if path.stem.startswith("item_") and not path.stem[5:].isdigit()
    ]
    print(
        f"Catalog-linked image refs: {len({row['image_ref'] for row in products if row['image_ref']})}; "
        f"mapped image names to improve: {len(renamed_mapped)}; "
        f"source images to tag: {orphan_count}; "
        f"category photos to extract: {extracted_count}; "
        f"source images with no serial: {len(unassigned)}"
    )
    if unassigned:
        print("Unassigned source assets will be retained outside the published images directory:")
        for path in unassigned:
            print(f"  {path.name}")
    if not args.apply:
        print("Dry run only. Re-run with --apply to update image assets and mapping.")
        return

    completed = []
    try:
        for operation in operations:
            source, target = operation[:2]
            if source is None:
                target.write_bytes(operation[2])
            else:
                source.rename(target)
            completed.append(operation)

        UNASSIGNED_DIR.mkdir(exist_ok=True)
        for path in unassigned:
            target = UNASSIGNED_DIR / f"unmapped_no_serial_{path.name[5:]}"
            if target.exists():
                raise FileExistsError(f"Unassigned source asset already exists: {target.name}.")
            path.rename(target)
            completed.append((path, target))

        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=IMAGE_MAP_PATH.parent,
                prefix=f".{IMAGE_MAP_PATH.stem}-",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(image_map, temporary_file, indent=2, ensure_ascii=False)
                temporary_file.write("\n")
            os.replace(temporary_path, IMAGE_MAP_PATH)
            temporary_path = None
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()
    except Exception:
        for operation in reversed(completed):
            source, target = operation[:2]
            if source is None:
                if target.exists():
                    target.unlink()
            elif target.exists() and not source.exists():
                target.rename(source)
        raise

    print(
        f"Mapped {len(image_map)} image names; retained {len(unassigned)} "
        f"source-only images outside the published image directory; renamed {len(renamed_mapped)} mapped assets."
    )


if __name__ == "__main__":
    main()
