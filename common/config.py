# sites.yml helper
import csv
import yaml
import pathlib


def csv_to_yaml(
    csv_path: str = "discovery/apple_interdiscount.csv",
    out_path: str = "config/sites.yml",
):
    """
    Read the CSV of SKUs and output a YAML mapping for the scheduler.
    Format:
      interdiscount:
        <code>:
          url: <url>
          selector: <selector>
          ean: <ean>
    """
    site: dict = {}
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            site[row["code"]] = {
                "url": row["url"],
                "selector": row["selector"],
                "ean": row["ean"],
            }

    out_data = {"interdiscount": site}
    pathlib.Path(out_path).write_text(
        yaml.safe_dump(out_data, allow_unicode=True), encoding="utf-8"
    )


if __name__ == "__main__":
    csv_to_yaml()