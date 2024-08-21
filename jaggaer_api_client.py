import json
import sys
import requests
import jaggaer_secrets
from datetime import datetime, timedelta

# For pretty output during development
from pprint import pprint


class JaggaerClient:
    def __init__(self, client_id: str, client_secret: str, host: str) -> None:
        # client_id and client_secrets are needed to get an authentication token.
        self._CLIENT_ID = client_id
        self._CLIENT_SECRET = client_secret
        # host may vary depending on test vs prod environment, TBD
        self._HOST = host
        # Initialize other values, which will be set later on demand.
        self._token = None
        self._expiration_time = datetime.now()

    def _obtain_authentication_token(self) -> None:
        """Obtain authentication token via API."""
        api = "/auth/realms/J1p-integrations/protocol/openid-connect/token"
        url = self._HOST + api
        headers = {
            "accept": "application/json",
            "content-type": "application/x-www-form-urlencoded",
        }
        data = {
            "client_id": self._CLIENT_ID,
            "client_secret": self._CLIENT_SECRET,
            "grant_type": "client_credentials",
        }
        response = requests.post(url, headers=headers, data=data)

        # TODO: Handle errors
        # Store token for reuse, along with expiration time
        response_data = response.json()
        self._token = response_data["access_token"]
        self._token_lifespan_secs = response_data["expires_in"]

        # Set expiration time in the future, based on how long token is good.
        self._expiration_time = datetime.now() + timedelta(
            seconds=self._token_lifespan_secs
        )

    def token_is_valid(self) -> bool:
        """Determine whether token should still be valid."""
        # TODO: Decide whether there should be a padding / grace period.
        time_remaining = (self._expiration_time - datetime.now()).total_seconds()
        return time_remaining > 0

    @property
    def token(self) -> str:
        """Return existing token if set and still valid;
        otherwise, obtain and set new token."""
        if (self._token is not None) and self.token_is_valid():
            return self._token
        else:
            self._obtain_authentication_token()
            return self._token

    def retrieve_invoice(self, invoice_id: str) -> dict:
        """Retrieve full data for an invoice from Jaggaer."""
        api = f"/j1p/api/public/ji/v1/invoices/{invoice_id}"
        url = self._HOST + api
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.token}",
        }
        response = requests.get(url, headers=headers)
        response_data = response.json()
        return response_data

    def import_invoice(self, invoice_data: dict):
        """Import data for an invoice into Jaggaer."""

        api = "/j1p/api/public/ji/v1/invoices/ocr/"
        url = self._HOST + api
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.token}",
        }
        response = requests.post(url, headers=headers, json=invoice_data)
        # pprint("***** RESPONSE *****")
        # pprint(vars(response), width=132)
        # pprint("")
        response_data = response.json()
        return response_data


# Temporary test harness
if __name__ == "__main__":
    # Values via importing jaggaer_secrets.py
    client = JaggaerClient(
        client_id=jaggaer_secrets.client_id,
        client_secret=jaggaer_secrets.client_secret,
        host=jaggaer_secrets.host,
    )

    # invoice_id = "2526304"
    # invoice = client.retrieve_invoice(invoice_id)
    # pprint(invoice["header"], width=132)

    # for testing
    # YBP real VCK: 006510005
    # Unknown supplier id in sample data: 279765
    json_file = sys.argv[1]
    with open(json_file) as f:
        invoice_data = json.load(f)
    # Invoice number needs to be unique; just use initials + timestamp during testing
    invoice_number = f"ACK{int(datetime.now().timestamp())}"
    invoice_data["invoiceOcr"]["invoiceOcrHeader"][
        "supplierInvoiceNumber"
    ] = invoice_number
    print(f"Importing {invoice_number}...")

    response_data = client.import_invoice(invoice_data)
    pprint(response_data, width=132)
