"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";

export type ForexMapMarker = {
  name: string;
  position: [number, number];
  isOpen: boolean;
  countdown: string;
};

function markerIcon(marker: ForexMapMarker) {
  return L.divIcon({
    className: "forex-leaflet-marker-wrapper",
    html: `
      <button class="forex-leaflet-marker ${marker.isOpen ? "open" : "closed"}" data-session-marker="${marker.name}" type="button" aria-label="${marker.name} session marker">
        <span class="forex-leaflet-marker-core"></span>
      </button>
    `,
    iconAnchor: [14, 14],
    iconSize: [28, 28],
    popupAnchor: [0, -16],
    tooltipAnchor: [16, -10],
  });
}

function popupHtml(marker: ForexMapMarker): string {
  return `
    <strong>${marker.name}</strong>
    <span>${marker.isOpen ? "Open" : "Closed"}</span>
    <small>${marker.countdown}</small>
  `;
}

export function ForexSessionsMap({ markers }: { markers: ForexMapMarker[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerLayerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    if ((container as HTMLDivElement & { _leaflet_id?: number })._leaflet_id) {
      delete (container as HTMLDivElement & { _leaflet_id?: number })._leaflet_id;
    }

    const map = L.map(container, {
      attributionControl: false,
      center: [18, 18],
      maxBounds: L.latLngBounds([-70, -180], [82, 180]),
      maxBoundsViscosity: 0.55,
      maxZoom: 6,
      minZoom: 1,
      scrollWheelZoom: true,
      zoom: 1,
      zoomControl: false,
    });

    L.control.zoom({ position: "bottomright" }).addTo(map);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    }).addTo(map);

    const markerLayer = L.layerGroup().addTo(map);
    mapRef.current = map;
    markerLayerRef.current = markerLayer;

    return () => {
      markerLayer.clearLayers();
      map.remove();
      mapRef.current = null;
      markerLayerRef.current = null;
      if ((container as HTMLDivElement & { _leaflet_id?: number })._leaflet_id) {
        delete (container as HTMLDivElement & { _leaflet_id?: number })._leaflet_id;
      }
    };
  }, []);

  useEffect(() => {
    const layer = markerLayerRef.current;
    if (!layer) return;
    layer.clearLayers();
    markers.forEach((marker) => {
      L.marker(marker.position, { icon: markerIcon(marker) })
        .bindTooltip(marker.name, {
          className: "forex-leaflet-tooltip",
          direction: "top",
          offset: [0, -18],
          opacity: 1,
          permanent: true,
        })
        .bindPopup(popupHtml(marker), {
          className: "forex-leaflet-popup",
          closeButton: false,
        })
        .addTo(layer);
    });
  }, [markers]);

  return (
    <div className="forex-leaflet-click-layer">
      <div className="forex-leaflet-map" ref={containerRef} />
    </div>
  );
}
