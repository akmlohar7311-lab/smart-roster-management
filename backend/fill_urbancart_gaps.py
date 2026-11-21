
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


BASE_URL = "http://127.0.0.1:8002"

ROSTER_ID = "9ab7d77f-dae4-4f11-a72a-cee52de877a5"

EMPLOYEE_CODE = "EMP031"

URBANCART_ACC = "3e0ff8f9-15a0-42e8-95f4-aff70c572bc2"
URBANCART_CS = "2abad4cc-02fa-4ab5-ab80-3b1d61e3e42d"

DATES = [
    "2026-12-10",
    "2026-12-11",
    "2026-12-12",
]


def create_shift(day, bp_id, process, start, end):

    payload = {
        "employee_code": EMPLOYEE_CODE,
        "brand_process_id": bp_id,
        "work_date": day,
        "start_time": start,
        "end_time": end,
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
            day,
            process,
            start,
            "-",
            end,
        )
        print("  Entry ID:", result["entry_id"])
        return True

    except HTTPError as error:
        body = error.read().decode("utf-8")

        print(
            "NOT CREATED:",
            day,
            process,
            "| HTTP",
            error.code,
        )
        print("  Response:", body)
        return False

    except URLError as error:
        print("API CONNECTION ERROR:", error)
        return False


def main():

    created = 0
    failed = 0

    for day in DATES:

        # Morning: Abandoned Cart Conversions
        if create_shift(
            day,
            URBANCART_ACC,
            "Abandoned Cart Conversions",
            "10:00:00",
            "14:00:00",
        ):
            created += 1
        else:
            failed += 1

        # Afternoon: Customer Support
        if create_shift(
            day,
            URBANCART_CS,
            "Customer Support",
            "14:00:00",
            "18:00:00",
        ):
            created += 1
        else:
            failed += 1

    print("\n" + "=" * 50)
    print("URBANCART COVERAGE REPAIR COMPLETE")
    print("=" * 50)
    print("Created:", created)
    print("Not created:", failed)


if __name__ == "__main__":
    main()
