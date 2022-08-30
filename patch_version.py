import re
import sys

def patch_installer(tag):
    """Patches the installer with the correct connector version and specklepy version"""
    iss_file = "speckle-sharp-ci-tools/arcgis.iss"

    #py_tag = get_specklepy_version()
    with open(iss_file, "r") as file:
        lines = file.readlines()
        lines.insert(12, f'#define AppVersion "{tag.split("-")[0]}"\n')
        lines.insert(13, f'#define AppInfoVersion "{tag}"\n')

        with open(iss_file, "w") as file:
            file.writelines(lines)
            print(f"Patched installer with connector v{tag} and specklepy ")


def main():
    if len(sys.argv) < 2:
        return

    tag = sys.argv[1]
    if not re.match(r"([0-9]+)\.([0-9]+)\.([0-9]+)", tag):
        raise ValueError(f"Invalid tag provided: {tag}")

    print(f"Patching version: {tag}")
    #patch_connector(tag.split("-")[0]) if I need to edit a connector file
    patch_installer(tag)


if __name__ == "__main__":
    main()