import argparse
import csv
import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "data" / "catalog_data.csv"
IMAGES_DIR = ROOT / "images"
SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
IMAGE_MAP_PATH = ROOT / "data" / "image_serial_map.json"


def number_ranges(values, minimum_width=1):
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


def safe_slug(value):
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return slug[:56].rstrip("_") or "catalog_image"


def image_description(image_ref):
    description = image_ref
    prefixes = (
        r"^(?:group_\d{4}_items_[\d,-]+(?:_span)?|groups_[\d,-]+)_sr_[\d,_-]+(?:_span)?_",
        r"^(?:groups?_[\d,-]+_)?sr_[\d,_-]+(?:_to_[\d,_-]+)?_",
        r"^group_sr_[\d,_-]+(?:_to_[\d,_-]+)?_",
    )
    while True:
        previous = description
        for prefix in prefixes:
            description = re.sub(prefix, "", description, count=1)
        if description == previous:
            return safe_slug(description)


def load_rows():
    with CATALOG_PATH.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    if "sr_number" not in fields and "sr_no" not in fields:
        raise ValueError("Catalog CSV must contain sr_number (or legacy sr_no).")
    if "sr_number" in fields and "sr_no" in fields:
        raise ValueError("Catalog CSV cannot contain both sr_number and sr_no.")
    return fields, rows


def assign_hierarchy(rows):
    has_group = all(row.get("group_number") for row in rows)
    has_item = all(row.get("item_number") for row in rows)
    if has_group != has_item:
        raise ValueError("group_number and item_number must both be present or both be absent.")

    if has_group:
        identifiers = set()
        for row in rows:
            group = row["group_number"].strip()
            item = row["item_number"].strip()
            if not group.isdigit() or int(group) < 1 or not item.isdigit() or int(item) < 1:
                raise ValueError(
                    f"Invalid hierarchical identifier for sr_number {row.get('sr_number')!r}."
                )
            identifier = (group, item)
            if identifier in identifiers:
                raise ValueError(f"Duplicate group_number.item_number: {group}.{item}")
            identifiers.add(identifier)
            row["sr_number"] = (row.get("sr_number") or row.get("sr_no") or "").strip()
            row.pop("sr_no", None)
        return

    previous_category = None
    current_group = 0
    next_item_by_group = defaultdict(int)
    seen_serials = set()
    for row in sorted(rows, key=lambda item: int(item.get("sr_number") or item.get("sr_no") or 0)):
        serial_text = (row.get("sr_number") or row.get("sr_no") or "").strip()
        if not serial_text.isdigit() or int(serial_text) < 1:
            raise ValueError(f"Invalid positive sr_number: {serial_text!r}")
        if serial_text in seen_serials:
            raise ValueError(f"Duplicate sr_number: {serial_text}")
        seen_serials.add(serial_text)

        category = row.get("category", "").strip()
        if not category:
            raise ValueError(f"Catalog item {serial_text} has no category.")
        if category != previous_category:
            current_group += 1
            previous_category = category
        next_item_by_group[current_group] += 1
        row["sr_number"] = serial_text
        row["group_number"] = str(current_group)
        row["item_number"] = str(next_item_by_group[current_group])
        row.pop("sr_no", None)


def plan_image_renames(rows):
    products_by_ref = defaultdict(list)
    for row in rows:
        if row.get("image_ref"):
            products_by_ref[row["image_ref"]].append(row)

    renames = []
    image_map = {}
    for old_ref, products in products_by_ref.items():
        serials = sorted({int(row["sr_number"]) for row in products})
        hierarchy = sorted(
            {
                f"{int(row['group_number'])}.{int(row['item_number'])}"
                for row in products
            },
            key=lambda value: tuple(int(part) for part in value.split(".")),
        )
        groups = sorted({int(row["group_number"]) for row in products})
        if len(products) == 1:
            item = products[0]
            new_ref = (
                f"sr_{int(item['sr_number']):04d}_"
                f"group_{int(item['group_number']):04d}_"
                f"item_{int(item['item_number']):04d}_"
                f"{safe_slug(item['item_name'])}"
            )
        else:
            serial_label = number_ranges(serials, minimum_width=4)
            if len(groups) == 1:
                item_numbers = {int(row["item_number"]) for row in products}
                item_label = number_ranges(item_numbers, minimum_width=4)
                identity = f"group_{groups[0]:04d}_items_{item_label}"
            else:
                group_label = number_ranges(groups, minimum_width=4)
                identity = f"groups_{group_label}"
            new_ref = f"{identity}_sr_{serial_label}_{image_description(old_ref)}"

        image_paths = [
            path for path in IMAGES_DIR.glob(f"{old_ref}.*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGES
        ]
        if not image_paths:
            raise FileNotFoundError(f"No supported image file for image_ref {old_ref!r}.")
        for image_path in image_paths:
            target = image_path.with_name(new_ref + image_path.suffix.lower())
            if target != image_path:
                if target.exists():
                    raise FileExistsError(f"Image rename would overwrite {target.name}.")
                renames.append((image_path, target))
        for row in products:
            row["image_ref"] = new_ref
        image_map[new_ref] = {
            "sr_numbers": serials,
            "group_items": hierarchy,
            "source_image_ref": old_ref,
        }

    return renames, image_map


def main():
    parser = argparse.ArgumentParser(
        description="Add stable hierarchical identifiers and serial-tag catalog images."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Rename image assets and update the canonical catalog CSV.",
    )
    args = parser.parse_args()

    fields, rows = load_rows()
    original_image_refs = {row["image_ref"] for row in rows if row.get("image_ref")}
    assign_hierarchy(rows)
    renames, image_map = plan_image_renames(rows)
    if IMAGE_MAP_PATH.exists():
        existing_image_map = json.loads(IMAGE_MAP_PATH.read_text(encoding="utf-8"))
        current_image_refs = {row["image_ref"] for row in rows if row.get("image_ref")}
        for old_ref in original_image_refs - current_image_refs:
            existing_image_map.pop(old_ref, None)
        for image_ref, mapping in image_map.items():
            existing = existing_image_map.get(image_ref)
            if existing:
                if (
                    set(existing.get("sr_numbers", [])) != set(mapping["sr_numbers"])
                    or set(existing.get("group_items", [])) != set(mapping["group_items"])
                ):
                    raise ValueError(f"Existing serial map disagrees for image_ref {image_ref!r}.")
                existing.update(mapping)
            else:
                existing_image_map[image_ref] = mapping
        image_map = existing_image_map
    output_fields = ["sr_number", "group_number", "item_number"] + [
        field for field in fields if field not in {"sr_number", "sr_no", "group_number", "item_number"}
    ]

    print(
        f"Products: {len(rows)}; image files to rename: {len(renames)}; "
        f"unique image references: {len({row['image_ref'] for row in rows if row['image_ref']})}"
    )
    print(
        "Identifiers use sr_number as the stable unique key and "
        "group_number.item_number as the category-run label."
    )
    if not args.apply:
        print("Dry run only. Re-run with --apply to write the CSV and rename images.")
        return

    temporary_path = None
    temporary_map_path = None
    completed_renames = []
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            dir=CATALOG_PATH.parent,
            prefix=f".{CATALOG_PATH.stem}-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            writer = csv.DictWriter(temporary_file, fieldnames=output_fields)
            writer.writeheader()
            writer.writerows(sorted(rows, key=lambda item: int(item["sr_number"])))
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=IMAGE_MAP_PATH.parent,
            prefix=f".{IMAGE_MAP_PATH.stem}-",
            suffix=".tmp",
            delete=False,
        ) as temporary_map:
            temporary_map_path = Path(temporary_map.name)
            json.dump(image_map, temporary_map, indent=2, ensure_ascii=False)
            temporary_map.write("\n")

        for source, target in renames:
            source.rename(target)
            completed_renames.append((source, target))
        os.replace(temporary_path, CATALOG_PATH)
        temporary_path = None
        os.replace(temporary_map_path, IMAGE_MAP_PATH)
        temporary_map_path = None
    except Exception:
        for source, target in reversed(completed_renames):
            if target.exists() and not source.exists():
                target.rename(source)
        raise
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
        if temporary_map_path and temporary_map_path.exists():
            temporary_map_path.unlink()

    print("Catalog serials, hierarchy fields, and referenced image names were updated.")


if __name__ == "__main__":
    main()
