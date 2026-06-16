"""SOAP client for the MyFlightbook web service."""

from zeep import Client as ZeepClient

MFB_WSDL = "https://myflightbook.com/logbook/public/WebService.asmx?WSDL"


class MFBClient:
    def __init__(self, access_token: str):
        """
        access_token: OAuth2 bearer token. Caller obtains it; we just use it.
        """
        self._token = access_token
        self._zeep = ZeepClient(MFB_WSDL)

    def _call(self, method: str, **kwargs):
        """
        Thin wrapper: inject szAuthToken into every SOAP call,
        handle zeep exceptions and HTTP errors,
        return the raw zeep result object.
        """
        try:
            fn = getattr(self._zeep.service, method)
            return fn(szAuthToken=self._token, **kwargs)
        except Exception as e:
            raise RuntimeError(f"MFB SOAP error in {method}: {e}") from e

    def get_aircraft(self) -> list:
        """
        Call AircraftForUser. Returns list of dicts with:
          id (int), tail (str), model (str)
        """
        result = self._call("AircraftForUser")
        aircraft = result if isinstance(result, list) else list(result or [])
        return [
            {
                "id": int(a.AircraftID),
                "tail": str(a.TailNumber),
                "model": str(getattr(a, "ModelDescription", "")),
            }
            for a in aircraft
        ]
