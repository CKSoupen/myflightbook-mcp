"""SOAP client for the MyFlightbook web service."""

from datetime import datetime
from decimal import Decimal

from zeep import Client as ZeepClient
from zeep.helpers import serialize_object

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

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cfp_value_fields(value) -> dict:
        """Map a Python value to the correct CustomFlightProperty slot."""
        if isinstance(value, bool):
            return {"BoolValue": value}
        if isinstance(value, int):
            return {"IntValue": value}
        if isinstance(value, float):
            return {"DecValue": Decimal(str(value))}
        if isinstance(value, datetime):
            return {"DateValue": value}
        return {"TextValue": str(value)}

    def _build_logbook_entry(self, flight: dict):
        """Construct a zeep LogbookEntry object from a flight dict."""
        CfpType = self._zeep.get_type("ns0:CustomFlightProperty")
        CfpArrType = self._zeep.get_type("ns0:ArrayOfCustomFlightProperty")
        LeType = self._zeep.get_type("ns0:LogbookEntry")

        raw_props = flight.get("custom_properties") or []
        cfp_objects = [
            CfpType(PropTypeID=p["prop_id"], **self._cfp_value_fields(p["value"]))
            for p in raw_props
        ]
        custom_props = CfpArrType(CustomFlightProperty=cfp_objects) if cfp_objects else None

        return LeType(
            FlightID=flight.get("flight_id", -1),
            AircraftID=flight["aircraft_id"],
            Date=datetime.strptime(flight["date"], "%Y-%m-%d"),
            TotalFlightTime=Decimal(str(flight.get("total_time", 0))),
            PIC=Decimal(str(flight.get("pic", 0))),
            SIC=Decimal(str(flight.get("sic", 0))),
            Landings=flight.get("landings", 0),
            FullStopLandings=flight.get("full_stop_landings", 0),
            NightLandings=flight.get("night_landings", 0),
            Route=flight.get("route", ""),
            Comment=flight.get("comment", ""),
            fIsPublic=flight.get("is_public", False),
            FlightStart=(
                datetime.fromisoformat(flight["flight_start"])
                if flight.get("flight_start")
                else None
            ),
            FlightEnd=(
                datetime.fromisoformat(flight["flight_end"])
                if flight.get("flight_end")
                else None
            ),
            CustomProperties=custom_props,
        )

    # ------------------------------------------------------------------
    # Flight methods
    # ------------------------------------------------------------------

    def add_flight(self, flight: dict) -> int:
        """
        Commit a completed flight via CommitFlightWithOptions.
        flight dict keys:
          aircraft_id (int), date (str YYYY-MM-DD),
          total_time (float), sic (float), pic (float),
          route (str), landings (int), full_stop_landings (int),
          night_landings (int, optional),
          comment (str, optional),
          flight_start (str ISO UTC, optional), flight_end (str ISO UTC, optional),
          is_public (bool, optional, default False),
          custom_properties (list of {"prop_id": int, "value": str|int|float|bool})
        Returns MFB-assigned FlightID (int).
        """
        PostType = self._zeep.get_type("ns0:PostingOptions")
        try:
            entry = self._build_logbook_entry(flight)
        except Exception as e:
            raise RuntimeError(f"add_flight: failed to build LogbookEntry: {e}") from e

        result = self._call("CommitFlightWithOptions", le=entry, po=PostType())
        try:
            return int(result.FlightID)
        except Exception as e:
            raise RuntimeError(f"CommitFlightWithOptions: unexpected result shape: {e}") from e

    def get_flights(self, start_date: str, end_date: str, max_count: int = 50) -> list:
        """
        Query flights via FlightsWithQueryAndOffset.
        Returns list of flight summary dicts for the date range (YYYY-MM-DD).
        """
        FqType = self._zeep.get_type("ns0:FlightQuery")
        fq = FqType(
            DateMin=datetime.strptime(start_date, "%Y-%m-%d"),
            DateMax=datetime.strptime(end_date, "%Y-%m-%d"),
        )
        result = self._call(
            "FlightsWithQueryAndOffset", fq=fq, offset=0, maxCount=max_count
        )
        try:
            flights = result if isinstance(result, list) else list(result or [])
            return [serialize_object(f) for f in flights]
        except Exception as e:
            raise RuntimeError(f"FlightsWithQueryAndOffset: failed to parse response: {e}") from e

    def check_flight(self, flight: dict) -> dict:
        """
        Validate a flight entry via CheckFlight before committing.
        Same flight dict shape as add_flight.
        Returns {"valid": bool, "messages": list[str]}.
        Empty messages list means the flight passed validation.
        """
        try:
            entry = self._build_logbook_entry(flight)
        except Exception as e:
            raise RuntimeError(f"check_flight: failed to build LogbookEntry: {e}") from e

        result = self._call("CheckFlight", le=entry)
        try:
            msgs = result if isinstance(result, list) else list(result or [])
            messages = [str(m) for m in msgs if m is not None]
            return {"valid": len(messages) == 0, "messages": messages}
        except Exception as e:
            raise RuntimeError(f"CheckFlight: failed to parse response: {e}") from e
