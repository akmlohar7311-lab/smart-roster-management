
import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

BASE_URL = "http://127.0.0.1:8002"

SHIFTS = {
    "Aman 10:00-14:00": "e341b605-7b28-4d77-b466-0dd3f281aca7",
    "Aman 14:00-18:00": "73e027cc-93ba-4a19-b167-e5082385a3c1",
    "Priya 10:00-14:00": "8b14e9bf-3daf-4672-b64e-438510cd435a",
    "Priya 14:00-18:00": "4ce451c0-b244-4bd7-96cf-a710aa3f2ced",
    "Sneha 14:00-18:00": "5af6a875-ed13-4406-8a46-5119f982d3a3",
}


def fetch(path):
    with urlopen(BASE_URL + path, timeout=30) as response:
        return json.load(response)


def main():
    for label, entry_id in SHIFTS.items():
        print("\n" + "=" * 60)
        print(label)
        print("Entry ID:", entry_id)

        try:
            result = fetch(
                f"/backups/available/{entry_id}"
            )

            assigned = result.get("assigned_backups", [])
            potential = result.get("potential_backups", [])

            print("Assigned backups:", len(assigned))
            print("Potential backups:", len(potential))

            for employee in assigned:
                print(
                    "  ELIGIBLE:",
                    employee.get("employee_code"),
                    employee.get("name"),
                )

            for employee in potential:
                print(
                    "  POTENTIAL:",
                    employee.get("employee_code"),
                    employee.get("name"),
                    "(may require a new assignment)"
                )

            if not assigned and not potential:
                print("  No backup candidates found.")

        except (HTTPError, URLError) as error:
            print("  API error:", error)


if __name__ == "__main__":
    main()
