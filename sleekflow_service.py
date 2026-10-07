import os
import requests
from dotenv import load_dotenv


load_dotenv()


class SleekFlowService:

    def __init__(self):
        self.base_url = os.getenv(
            "SLEEKFLOW_API_URL",
            "https://sleekflow.io"
        )

        self.api_key = os.getenv(
            "SLEEKFLOW_API_KEY"
        )

        if not self.api_key:
            raise ValueError(
                "SLEEKFLOW_API_KEY belum ditemukan di .env"
            )

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def get_contacts(self):
        path = os.getenv(
            "SLEEKFLOW_CONTACTS_PATH",
            "/api/contact"
        )

        url = self.base_url.rstrip("/") + "/" + path.lstrip("/")

        response = requests.get(
            url,
            headers=self.headers,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def get_tickets(self):
        url = os.getenv(
            "SLEEKFLOW_TICKETS_URL"
        )

        if not url:
            raise ValueError(
                "SLEEKFLOW_TICKETS_URL belum ditemukan"
            )

        response = requests.get(
            url,
            headers=self.headers,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()
