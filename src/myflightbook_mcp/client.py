"""REST client for the MyFlightbook web service (OAuth Resource endpoint).

All methods call https://myflightbook.com/logbook/mvc/oAuth/OAuthResource/{ServiceID}
with Authorization: Bearer <token> and form-encoded POST body, JSON responses.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_BASE_URL = "https://myflightbook.com/logbook/mvc/oAuth/OAuthResource"
_TIMEOUT = 15.0


class MFBClient:
    def __init__(self, access_token: str):
        """
        access_token: OAuth2 bearer token. Caller obtains it; we just use it.
        """
        self._token = access_token

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post(self, service_id: str, params: dict[str, str]) -> Any:
        """POST to the MFB REST OAuth endpoint and return parsed JSON."""
        params = dict(params, json="1")
        body = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(
            f"{_BASE_URL}/{service_id}",
            data=body,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode(errors="replace")
            raise RuntimeError(f"MFB {service_id} HTTP {e.code}: {body_text}") from e
        except Exception as e:
            raise RuntimeError(f"MFB {service_id}: {e}") from e

    @staticmethod
    def _build_le_dict(flight: dict) -> dict[str, Any]:
        """Build a LogbookEntry JSON dict from a caller-supplied flight dict."""
        date = flight["date"]
        le: dict[str, Any] = {
            "FlightID": int(flight.get("flight_id", -1)),
            "AircraftID": int(flight["aircraft_id"]),
            "Date": date if "T" in date else f"{date}T00:00:00",
            "TotalFlightTime": float(flight.get("total_time", 0)),
            "PIC": float(flight.get("pic", 0)),
            "SIC": float(flight.get("sic", 0)),
            "CrossCountry": float(flight.get("cross_country", 0)),
            "Nighttime": float(flight.get("night", 0)),
            "IMC": float(flight.get("imc", 0)),
            "Approaches": int(flight.get("approaches", 0)),
            "Landings": int(flight.get("landings", 0)),
            "FullStopLandings": int(flight.get("full_stop_landings", 0)),
            "NightLandings": int(flight.get("night_landings", 0)),
            "Route": flight.get("route", ""),
            "Comment": flight.get("comment", ""),
            "fIsPublic": bool(flight.get("is_public", False)),
            "CustomProperties": MFBClient._build_cfp_list(flight.get("custom_properties") or []),
        }
        if flight.get("flight_start"):
            le["FlightStart"] = flight["flight_start"]
        if flight.get("flight_end"):
            le["FlightEnd"] = flight["flight_end"]
        return le

    @staticmethod
    def _build_cfp_list(props: list) -> list:
        """Convert custom_properties dicts to MFB CustomFlightProperty JSON."""
        result = []
        for p in props:
            value = p["value"]
            cfp: dict[str, Any] = {
                "PropID": 0,
                "FlightID": 0,
                "PropTypeID": int(p["prop_id"]),
            }
            if isinstance(value, bool):
                cfp["BoolValue"] = value
            elif isinstance(value, int):
                cfp["IntValue"] = value
            elif isinstance(value, float):
                cfp["DecValue"] = value
            else:
                cfp["TextValue"] = str(value)
            result.append(cfp)
        return result

    # ------------------------------------------------------------------
    # Aircraft
    # ------------------------------------------------------------------

    def get_aircraft(self) -> list:
        """
        Call AircraftForUser. Returns list of dicts with:
          id (int), tail (str), model (str)
        """
        result = self._post("AircraftForUser", {})
        if not isinstance(result, list):
            raise RuntimeError(f"AircraftForUser: unexpected response type {type(result)}")
        return [
            {
                "id": int(a["AircraftID"]),
                "tail": str(a.get("TailNumber", "")),
                "model": str(a.get("ModelDescription", "")),
            }
            for a in result
        ]

    def add_aircraft(self, tail_number: str, model_id: int, instance_type: int = 1) -> dict:
        """
        Register a new aircraft by tail number and MFB model ID.
        Requires the 'addaircraft' OAuth scope — re-authorize if you see a scope error.
        model_id: integer MFB model ID (not an ICAO string).
        instance_type: 1 = real aircraft (default), 2 = UAS, 3 = simulator.
        Returns: {"id": int, "tail": str, "model": str}
        """
        result = self._post("AddAircraftForUser", {
            "szTail": tail_number,
            "idModel": str(model_id),
            "idInstanceType": str(instance_type),
        })
        aircraft = result if isinstance(result, list) else []
        for a in aircraft:
            if str(a.get("TailNumber", "")).upper() == tail_number.upper():
                return {
                    "id": int(a["AircraftID"]),
                    "tail": str(a["TailNumber"]),
                    "model": str(a.get("ModelDescription", "")),
                }
        if aircraft:
            a = aircraft[-1]
            return {
                "id": int(a["AircraftID"]),
                "tail": str(a["TailNumber"]),
                "model": str(a.get("ModelDescription", "")),
            }
        raise RuntimeError("AddAircraftForUser: empty response")

    # ------------------------------------------------------------------
    # Property types
    # ------------------------------------------------------------------

    def get_property_types(self) -> list:
        """
        Call AvailablePropertyTypesForUser.
        Returns list of {"id": int, "name": str, "type": str} for all custom
        property types. Use the id values in add_flight's custom_properties.
        """
        result = self._post("AvailablePropertyTypesForUser", {})
        if not isinstance(result, list):
            raise RuntimeError(
                f"AvailablePropertyTypesForUser: unexpected type {type(result)}"
            )
        return [
            {
                "id": int(p["PropTypeID"]),
                "name": str(p.get("Title", "")),
                "type": str(p.get("Type", "")),
            }
            for p in result
        ]

    # ------------------------------------------------------------------
    # Completed flight methods
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

        Note: response assumed to be a LogbookEntry dict with FlightID populated.
        Not verified via live write test (destructive). If FlightID is -1, call
        get_flights() with today's date to locate the new entry.
        """
        le = self._build_le_dict(flight)
        result = self._post("CommitFlightWithOptions", {"le": json.dumps(le), "po": "{}"})
        if isinstance(result, dict):
            if result.get("ErrorString"):
                raise RuntimeError(f"CommitFlightWithOptions: {result['ErrorString']}")
            return int(result.get("FlightID", -1))
        raise RuntimeError(
            f"CommitFlightWithOptions: unexpected response type {type(result)}: {result}"
        )

    def get_flights(self, start_date: str, end_date: str, max_count: int = 50) -> list:
        """
        Query flights via FlightsWithQueryAndOffset.
        start_date / end_date: YYYY-MM-DD strings.
        Returns list of flight dicts for the date range.
        """
        fq = {
            "DateRange": "Custom",
            "DateMin": f"{start_date}T00:00:00",
            "DateMax": f"{end_date}T23:59:59",
            "Distance": "AllFlights",
            "EngineType": "AllEngines",
            "AircraftInstanceTypes": "AllAircraft",
            "IsPublic": False,
            "HasNightLandings": False,
            "HasFullStopLandings": False,
            "HasLandings": False,
            "HasApproaches": False,
            "HasHolds": False,
            "HasXC": False,
            "HasSimIMCTime": False,
            "HasGroundSim": False,
            "HasIMC": False,
            "HasAnyInstrument": False,
            "HasNight": False,
            "HasDual": False,
            "HasCFI": False,
            "HasSIC": False,
            "HasPIC": False,
            "HasTotalTime": False,
            "IsSigned": False,
            "IsComplex": False,
            "HasFlaps": False,
            "IsHighPerformance": False,
            "IsConstantSpeedProp": False,
            "IsRetract": False,
            "IsTechnicallyAdvanced": False,
            "IsGlass": False,
            "IsTailwheel": False,
            "IsMultiEngineHeli": False,
            "IsTurbine": False,
            "HasTelemetry": False,
            "HasImages": False,
            "IsMotorglider": False,
        }
        result = self._post("FlightsWithQueryAndOffset", {
            "fq": json.dumps(fq),
            "offset": "0",
            "maxCount": str(max_count),
        })
        if not isinstance(result, list):
            raise RuntimeError(
                f"FlightsWithQueryAndOffset: unexpected type {type(result)}: {result}"
            )
        return result

    def check_flight(self, flight: dict) -> dict:
        """
        Validate a flight via CheckFlight before committing.
        Same flight dict shape as add_flight.
        Returns {"valid": bool, "messages": list[str]}.
        Empty messages means the flight passed validation.
        """
        le = self._build_le_dict(flight)
        result = self._post("CheckFlight", {"le": json.dumps(le)})
        msgs = result if isinstance(result, list) else []
        messages = [str(m) for m in msgs if m is not None]
        return {"valid": len(messages) == 0, "messages": messages}

    # ------------------------------------------------------------------
    # Pending flight methods
    # ------------------------------------------------------------------

    def create_pending_flight(self, flight: dict) -> str:
        """
        Stage a pending flight via CreatePendingFlight.
        Same flight dict shape as add_flight.
        Returns the MFB-assigned PendingID (string UUID).

        Note: MFB REST returns the full ArrayOfPendingFlight (not just the new
        entry). We identify the new entry by matching AircraftID + Date + Route
        + Comment. Raises if the match is not unique — avoid duplicate entries
        with identical route/date/aircraft/comment.
        """
        le = self._build_le_dict(flight)
        result = self._post("CreatePendingFlight", {"le": json.dumps(le)})
        if not isinstance(result, list):
            raise RuntimeError(
                f"CreatePendingFlight: unexpected response type {type(result)}"
            )
        target_date = le["Date"][:10]
        target_ac = int(le["AircraftID"])
        target_route = le.get("Route", "")
        target_comment = le.get("Comment", "")
        matches = [
            p for p in result
            if int(p.get("AircraftID", -1)) == target_ac
            and str(p.get("Date", ""))[:10] == target_date
            and p.get("Route", "") == target_route
            and p.get("Comment", "") == target_comment
        ]
        if len(matches) == 1:
            return str(matches[0]["PendingID"])
        raise RuntimeError(
            f"CreatePendingFlight: expected 1 matching entry but found {len(matches)} "
            f"(date={target_date}, aircraft={target_ac}, route={target_route!r}). "
            "Check for duplicate pending flights."
        )

    def get_pending_flights(self) -> list:
        """
        List all pending flights via PendingFlightsForUser.
        Returns list of pending flight dicts (LogbookEntry fields + PendingID).
        """
        result = self._post("PendingFlightsForUser", {})
        if not isinstance(result, list):
            raise RuntimeError(f"PendingFlightsForUser: unexpected type {type(result)}")
        return result

    def update_pending_flight(self, pending_id: str, flight: dict) -> None:
        """
        Update an existing pending flight via UpdatePendingFlight.
        pending_id: the PendingID returned by create_pending_flight.
        flight: same dict shape as add_flight.
        """
        le = self._build_le_dict(flight)
        pf = {"PendingID": pending_id, **le}
        self._post("UpdatePendingFlight", {"pf": json.dumps(pf)})

    def commit_pending_flight(self, pending_id: str) -> int:
        """
        Promote a pending flight to a logbook entry via CommitPendingFlight.

        Note: MFB REST returns the remaining ArrayOfPendingFlight, not the new
        FlightID. Returns -1 as sentinel; use get_flights() with today's date
        to retrieve the committed FlightID. Response shape unverified (destructive).
        """
        pf = {"PendingID": pending_id}
        self._post("CommitPendingFlight", {"pf": json.dumps(pf)})
        return -1

    def delete_pending_flight(self, pending_id: str) -> None:
        """Remove a pending flight via DeletePendingFlight."""
        self._post("DeletePendingFlight", {"idpending": pending_id})

    # ------------------------------------------------------------------
    # Currency and totals
    # ------------------------------------------------------------------

    def get_currency(self) -> list:
        """
        Retrieve pilot currency via GetCurrencyForUser.
        Returns list of CurrencyStatusItem dicts (Attribute, Value, Status).
        """
        result = self._post("GetCurrencyForUser", {})
        if not isinstance(result, list):
            raise RuntimeError(f"GetCurrencyForUser: unexpected type {type(result)}")
        return result

    def get_totals(self) -> list:
        """
        Retrieve flight time totals via TotalsForUserWithQuery (empty query = all time).
        Returns list of TotalsItem dicts. The "Value" field is a float (hours or count).

        Note: REST's TotalsForUser returns HTTP 500; TotalsForUserWithQuery is the
        working equivalent — empty FlightQuery applies no date/type filter.
        """
        result = self._post("TotalsForUserWithQuery", {"fq": "{}"})
        if not isinstance(result, list):
            raise RuntimeError(f"TotalsForUserWithQuery: unexpected type {type(result)}")
        return result
