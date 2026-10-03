import logging

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from .config import SPREADSHEET_ID, SERVICE_ACCOUNT_INFO


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_sheets_service():
    if not SPREADSHEET_ID or not SERVICE_ACCOUNT_INFO:
        logging.warning("Google Sheets configuration is missing.")
        return None

    try:
        credentials = Credentials.from_service_account_info(
            SERVICE_ACCOUNT_INFO,
            scopes=SCOPES,
        )

        return build(
            "sheets",
            "v4",
            credentials=credentials,
            static_discovery=False,
        )

    except Exception as exc:
        logging.error("Failed to initialize Google Sheets service: %s", exc)
        return None


sheets_service = get_sheets_service()


def get_all_projects() -> list[str]:
    if not sheets_service:
        return ["Digital Daari (Fallback)", "Chaitanya AI (Fallback)"]

    try:
        result = (
            sheets_service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range="B2:B",
            )
            .execute()
        )

        values = result.get("values", [])

        projects = sorted(
            {
                row[0].strip()
                for row in values
                if row and row[0].strip()
            }
        )

        return projects if projects else ["Digital Daari (Empty Sheet)"]

    except Exception as exc:
        logging.error("Error fetching projects: %s", exc)
        return ["Digital Daari (Error)"]


def get_project_context(project_name: str) -> str:
    if not sheets_service:
        return "You are ISIRA, a Supreme AI Architect. Context Sync Error."

    try:
        result = (
            sheets_service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range="A:E",
            )
            .execute()
        )

        values = result.get("values", [])

        for row in values:
            if len(row) > 4 and row[1].strip() == project_name:
                return row[4].strip()

        return "You are ISIRA, a Supreme AI Architect. No specific context found."

    except Exception as exc:
        logging.error("Error fetching project context: %s", exc)
        return "You are ISIRA, a Supreme AI Architect. Context Error."


def save_lead(
    project: str,
    query: str,
    response: str,
    image_present: bool = False,
) -> bool:
    if not sheets_service:
        return False

    try:
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        truncated = (
            response[:4000] + "..."
            if len(response) > 4000
            else response
        )

        if image_present and query:
            display_query = f"[IMAGE] {query}"
        elif image_present:
            display_query = "[IMAGE ONLY]"
        else:
            display_query = query

        body = {
            "values": [[
                timestamp,
                project,
                display_query,
                truncated,
            ]]
        }

        (
            sheets_service.spreadsheets()
            .values()
            .append(
                spreadsheetId=SPREADSHEET_ID,
                range="Leads!A:D",
                valueInputOption="USER_ENTERED",
                body=body,
            )
            .execute()
        )

        return True

    except Exception as exc:
        logging.error("Error saving lead: %s", exc)
        return False
