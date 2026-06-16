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

    def _call(self, method: str, token_param: str = "szAuthUserToken", **kwargs):
        """
        Thin wrapper: inject the auth token into every SOAP call.
        Most MFB operations use szAuthUserToken; a few (currency, totals)
        use szAuthToken — pass token_param to override.
        """
        try:
            fn = getattr(self._zeep.service, method)
            return fn(**{token_param: self._token}, **kwargs)
        except Exception as e:
            raise RuntimeError(f"MFB SOAP error in {method}: {e}") from e

    def get_aircraft(self) -> list:
        """
        Call AircraftForUser. Returns list of dicts with:
          id (int), tail (str), model (str)
        """
        result = self._call("AircraftForUser")
        try:
            aircraft = result if isinstance(result, list) else list(result or [])
            return [
                {
                    "id": int(a.AircraftID),
                    "tail": str(a.TailNumber),
                    "model": str(getattr(a, "ModelDescription", "")),
                }
                for a in aircraft
            ]
        except Exception as e:
            raise RuntimeError(f"AircraftForUser: failed to parse response: {e}") from e

    def add_aircraft(self, tail_number: str, model_id: int, instance_type: int = 1) -> dict:
        """
        Register a new aircraft by tail number and MFB model ID.
        model_id: integer MFB model ID (not an ICAO string — use MFB website or
                  MakesAndModels() to find the ID for a given type).
        instance_type: 1 = real aircraft (default), 2 = UAS, 3 = simulator.
        Returns: {"id": int, "tail": str, "model": str}
        """
        result = self._call(
            "AddAircraftForUser",
            szTail=tail_number,
            idModel=model_id,
            idInstanceType=instance_type,
        )
        try:
            aircraft = result if isinstance(result, list) else list(result or [])
            for a in aircraft:
                if str(a.TailNumber).upper() == tail_number.upper():
                    return {
                        "id": int(a.AircraftID),
                        "tail": str(a.TailNumber),
                        "model": str(getattr(a, "ModelDescription", "")),
                    }
            if aircraft:
                a = aircraft[-1]
                return {
                    "id": int(a.AircraftID),
                    "tail": str(a.TailNumber),
                    "model": str(getattr(a, "ModelDescription", "")),
                }
            raise RuntimeError("AddAircraftForUser returned empty list")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"AddAircraftForUser: failed to parse response: {e}") from e

    def get_property_types(self) -> list:
        """
        Call AvailablePropertyTypesForUser.
        Returns list of {"id": int, "name": str, "type": str} for all custom
        property types (Flight Number, Name of PIC, etc.).
        Use the id values in add_flight's custom_properties parameter.
        """
        result = self._call("AvailablePropertyTypesForUser")
        try:
            props = result if isinstance(result, list) else list(result or [])
            return [
                {
                    "id": int(p.PropTypeID),
                    "name": str(p.Title),
                    "type": str(p.Type) if p.Type is not None else "",
                }
                for p in props
            ]
        except Exception as e:
            raise RuntimeError(f"AvailablePropertyTypesForUser: failed to parse response: {e}") from e
