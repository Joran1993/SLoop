"use client";

import { useEffect, useRef } from "react";
import type { Lead } from "@/lib/api";

interface LeadMapProps {
  leads: Lead[];
  hoveredId: string | null;
  selectedId: string | null;
  onLeadClick: (id: string) => void;
}

const PDOK_STYLE =
  "https://api.pdok.nl/lv/brt/ogc/v1_0/styles/standaard?f=json";

export function LeadMap({
  leads,
  hoveredId,
  selectedId,
  onLeadClick,
}: LeadMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import("maplibre-gl").Map | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    let map: import("maplibre-gl").Map;

    (async () => {
      const maplibre = await import("maplibre-gl");
      await import("maplibre-gl/dist/maplibre-gl.css");

      map = new maplibre.Map({
        container: containerRef.current!,
        style: {
          version: 8,
          sources: {
            "pdok-brt": {
              type: "raster",
              tiles: [
                "https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/standaard/EPSG:3857/{z}/{x}/{y}.png",
              ],
              tileSize: 256,
              attribution: "© PDOK/Kadaster",
            },
          },
          layers: [
            {
              id: "pdok-brt",
              type: "raster",
              source: "pdok-brt",
            },
          ],
        },
        center: [5.2913, 52.1326],
        zoom: 7,
      });

      mapRef.current = map;

      map.on("load", () => {
        map.addSource("leads", {
          type: "geojson",
          data: leadsToGeoJSON(leads),
          cluster: true,
          clusterMaxZoom: 12,
          clusterRadius: 40,
        });

        map.addLayer({
          id: "clusters",
          type: "circle",
          source: "leads",
          filter: ["has", "point_count"],
          paint: {
            "circle-color": "#d97706",
            "circle-radius": [
              "step",
              ["get", "point_count"],
              14, 10,
              18, 50,
              22,
            ],
            "circle-opacity": 0.85,
          },
        });

        map.addLayer({
          id: "cluster-count",
          type: "symbol",
          source: "leads",
          filter: ["has", "point_count"],
          layout: {
            "text-field": "{point_count_abbreviated}",
            "text-size": 11,
            "text-font": ["Noto Sans Regular"],
          },
          paint: { "text-color": "#fff" },
        });

        map.addLayer({
          id: "lead-points",
          type: "circle",
          source: "leads",
          filter: ["!", ["has", "point_count"]],
          paint: {
            "circle-color": [
              "case",
              ["==", ["get", "id"], selectedId ?? ""],
              "#d97706",
              ["==", ["get", "id"], hoveredId ?? ""],
              "#f59e0b",
              ["==", ["get", "has_sloopvergunning"], true],
              "#dc2626",
              [">", ["get", "signal_count"], 0],
              "#6366f1",
              "#1c1c1c",
            ],
            "circle-radius": [
              "case",
              ["==", ["get", "id"], selectedId ?? ""],
              8,
              ["==", ["get", "has_sloopvergunning"], true],
              7,
              [">", ["get", "signal_count"], 0],
              7,
              6,
            ],
            "circle-stroke-width": 1.5,
            "circle-stroke-color": "#fff",
          },
        });

        map.on("click", "lead-points", (e) => {
          const feature = e.features?.[0];
          if (feature?.properties?.id) {
            onLeadClick(feature.properties.id as string);
          }
        });

        map.on("mouseenter", "lead-points", () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "lead-points", () => {
          map.getCanvas().style.cursor = "";
        });
      });
    })();

    return () => {
      map?.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update GeoJSON source when leads change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    const source = map.getSource("leads") as
      | import("maplibre-gl").GeoJSONSource
      | undefined;
    source?.setData(leadsToGeoJSON(leads));
  }, [leads]);

  // Update paint for hover/select without re-rendering map
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    map.setPaintProperty("lead-points", "circle-color", [
      "case",
      ["==", ["get", "id"], selectedId ?? ""],
      "#d97706",
      ["==", ["get", "id"], hoveredId ?? ""],
      "#f59e0b",
      ["==", ["get", "has_sloopvergunning"], true],
      "#dc2626",
      [">", ["get", "signal_count"], 0],
      "#6366f1",
      "#1c1c1c",
    ]);
    map.setPaintProperty("lead-points", "circle-radius", [
      "case",
      ["==", ["get", "id"], selectedId ?? ""],
      8,
      ["==", ["get", "has_sloopvergunning"], true],
      7,
      [">", ["get", "signal_count"], 0],
      7,
      6,
    ]);
  }, [hoveredId, selectedId]);

  return <div ref={containerRef} className="h-full w-full" />;
}

function leadsToGeoJSON(leads: Lead[]) {
  return {
    type: "FeatureCollection" as const,
    features: leads
      .filter((l) => l.longitude != null && l.latitude != null)
      .map((l) => ({
        type: "Feature" as const,
        geometry: {
          type: "Point" as const,
          coordinates: [l.longitude!, l.latitude!],
        },
        properties: {
          id: l.id,
          score: l.score_totaal,
          adres: l.adres,
          signal_count: l.signal_count ?? 0,
          has_sloopvergunning: l.has_sloopvergunning ?? false,
        },
      })),
  };
}
