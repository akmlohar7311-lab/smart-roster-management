
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


BASE_URL = "http://127.0.0.1:8002"

ROSTER_ID = "9ab7d77f-dae4-4f11-a72a-cee52de877a5"

SHIFTS = [
    {
        "name": "MegaMart ACC",
        "date": "2026-12-15",
        "brand_process_id": "0ee87929-23ef-4bc2-9caa-13a9ab6f9d60",
    },
    {
        "name": "PrimeNest NDR",
        "date": "2026-12-22",
        "brand_process_id": "be6fb375-2646-42ef-9bb2-5a0a68401a06",
    },
    {
        "name": "PrimeNest NDR",
        "date": "2026-12-23",
        "brand_process_id": "be6fb375-2646-42ef-9bb2-5a0a68401a06",
    },
]


def create_shift(shift):
    payload = {
        "employee_code": "EMP031",
        "brand_process_id": shift["brand_process_id"],
        "work_date": shift["date"],
        "start_time": "10:00:00",
        "end_time": "18:00:00",
    }

    url = (
        f"{BASE_URL}/roster-editor/"
        f"rosters/{ROSTER_ID}/shifts"
    )

    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)

        print(
            "CREATED:",
            shift["date"],
            shift["name"]
        )
        print("Entry ID:", result["entry_id"])
        return True

    except HTTPError as error:
        print(
            "NOT CREATED:",
            shift["date"],
            shift["name"],
            "| HTTP",
            error.code,
        )
        print(
            error.read().decode("utf-8")
        )
        return False

    except URLError as error:
        print("CONNECTION ERROR:", error)
        return False


def main():
    created = 0

    for shift in SHIFTS:
        if create_shift(shift):
            created += 1

    print("\n" + "=" * 50)
    print("REMAINING COVERAGE REPAIR")
    print("=" * 50)
    print("Created:", created)
    print("Not created:", len(SHIFTS) - created)


if __name__ == "__main__":
    main()
