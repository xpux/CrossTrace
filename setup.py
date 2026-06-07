import os
import json


FILES = {
    "feedback.json": {},
    "famous.json": [],
    "history.json": [],
    "target.txt": "",
    "aliases.txt": "# Add known aliases here\n# Format: name1 = name2 = name3\n",
}

FOLDERS = [
    "data/users/me",
    "data/known",
    "output"
]


def main():
    print("\n  CrossTrace setup\n")

    for folder in FOLDERS:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"  created {folder}/")
        else:
            print(f"  exists  {folder}/")

    for filename, default in FILES.items():
        if not os.path.exists(filename):
            with open(filename, "w", encoding="utf-8") as f:
                if isinstance(default, (dict, list)):
                    json.dump(default, f)
                else:
                    f.write(default)
            print(f"  created {filename}")
        else:
            print(f"  exists  {filename}")

    print("\n  setup complete. drop your exported lists into data/users/me/ and run python crosstrace.py\n")


if __name__ == "__main__":
    main()