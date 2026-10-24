"""Made-up source rows for tests. Not live award data and not a client fixture."""


class JsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


USA_ROW = {
    "Award ID": "AWARD-EXAMPLE-1",
    "Recipient Name": "Example Recipient LLC",
    "Description": "Unrelated facilities maintenance",
    "Award Amount": 125000,
    "Start Date": "2024-01-01",
    "End Date": "2027-03-01",
    "Awarding Agency": "Department of Defense",
    "Awarding Sub Agency": "Department of the Air Force",
    "NAICS Code": "541511",
    "NAICS Description": "Custom Computer Programming Services",
    "Award Type": "Definitive Contract",
    "Place of Performance State Code": "CO",
    "generated_internal_id": "CONT_AWD_EXAMPLE",
}

SAM_ROW = {
    "noticeId": "NOTICE-EXAMPLE-1",
    "title": "Telemetry support services",
    "solicitationNumber": "SOL-EXAMPLE-1",
    "fullParentPathName": "DEPT OF DEFENSE.DEPT OF THE AIR FORCE",
    "naicsCode": "541511",
    "postedDate": "2026-10-20",
    "responseDeadLine": "2026-11-15",
    "typeOfSetAsideDescription": "Total Small Business Set-Aside (FAR 19.5)",
    "active": "Yes",
    "description": "https://api.sam.gov/prod/opportunities/v1/noticedesc?noticeid=NOTICE-EXAMPLE-1",
}
