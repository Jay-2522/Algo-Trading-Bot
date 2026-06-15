"use client";

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { MapContainer, Marker, Popup, TileLayer, Tooltip, ZoomControl } from "react-leaflet";

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

export function ForexSessionsMap({ markers }: { markers: ForexMapMarker[] }) {
  const [selectedMarker, setSelectedMarker] = useState<ForexMapMarker | null>(null);
  const mapShellRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const shell = mapShellRef.current;
    if (!shell) return;
    const handleMarkerClick = (event: Event) => {
      const target = event.target as HTMLElement | null;
      const markerButton = target?.closest<HTMLElement>("[data-session-marker]");
      if (!markerButton) return;
      const marker = markers.find((item) => item.name === markerButton.dataset.sessionMarker);
      if (marker) setSelectedMarker(marker);
    };
    shell.addEventListener("click", handleMarkerClick, true);
    return () => shell.removeEventListener("click", handleMarkerClick, true);
  }, [markers]);
  useEffect(() => {
    const shell = mapShellRef.current;
    if (!shell) return;
    const cleanups: Array<() => void> = [];
    const attachHandlers = () => {
      shell.querySelectorAll<HTMLElement>("[data-session-marker]").forEach((markerButton) => {
        const handleClick = () => {
          const marker = markers.find((item) => item.name === markerButton.dataset.sessionMarker);
          if (marker) setSelectedMarker(marker);
        };
        markerButton.addEventListener("click", handleClick);
        cleanups.push(() => markerButton.removeEventListener("click", handleClick));
      });
    };
    const timeout = window.setTimeout(attachHandlers, 100);
    return () => {
      window.clearTimeout(timeout);
      cleanups.forEach((cleanup) => cleanup());
    };
  }, [markers]);
  return (
    <div className="forex-leaflet-click-layer" ref={mapShellRef}>
      <MapContainer
        attributionControl={false}
        center={[18, 18]}
        className="forex-leaflet-map"
        maxBounds={[[-70, -180], [82, 180]]}
        maxBoundsViscosity={0.55}
        maxZoom={6}
        minZoom={1}
        scrollWheelZoom
        zoom={1}
        zoomControl={false}
      >
        <ZoomControl position="bottomright" />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        {markers.map((marker) => (
          <Marker eventHandlers={{ click: () => setSelectedMarker(marker) }} icon={markerIcon(marker)} key={marker.name} position={marker.position}>
            <Tooltip className="forex-leaflet-tooltip" direction="top" offset={[0, -18]} opacity={1} permanent>
              {marker.name}
            </Tooltip>
          </Marker>
        ))}
        {selectedMarker ? (
          <Popup className="forex-leaflet-popup" closeButton={false} position={selectedMarker.position}>
            <strong>{selectedMarker.name}</strong>
            <span>{selectedMarker.isOpen ? "Open" : "Closed"}</span>
            <small>{selectedMarker.countdown}</small>
          </Popup>
        ) : null}
      </MapContainer>
    </div>
  );
}
