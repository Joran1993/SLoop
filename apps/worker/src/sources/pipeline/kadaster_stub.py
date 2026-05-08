"""Bron 2: Kadaster — eigendomsoverdrachten en percelen.

Signaalwaarde: 6-18 maanden vóór sloop. Horizon: 12-24 maanden.

Vereist Kadaster API-toegang (betaald). Schakel in via KADASTER_ENABLED=true
in de omgevingsvariabelen zodra de key beschikbaar is.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Iterator

from .base import PipelineSourceAdapter, ParsedSignal, RawSignal

log = logging.getLogger(__name__)

_ENABLED = os.getenv("KADASTER_ENABLED", "false").lower() == "true"


class KadasterAdapter(PipelineSourceAdapter):
    source_name = "kadaster"
    cron_schedule = "0 4 * * 1"  # maandags om 4:00

    def fetch_signals(self, since: datetime) -> Iterator[RawSignal]:
        if not _ENABLED:
            log.info("KadasterAdapter uitgeschakeld (KADASTER_ENABLED=false)")
            return
        raise NotImplementedError("Kadaster adapter nog niet geïmplementeerd")

    def parse_signal(self, raw: RawSignal) -> ParsedSignal | None:
        raise NotImplementedError
