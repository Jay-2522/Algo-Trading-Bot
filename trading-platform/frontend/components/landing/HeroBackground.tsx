"use client";

import { useEffect, useRef } from "react";

function DotGridCanvas() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const pointer = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const context = canvas.getContext("2d");
    if (!context) return;

    const draw = () => {
      const ratio = window.devicePixelRatio || 1;
      const width = window.innerWidth;
      const height = window.innerHeight;

      canvas.width = width * ratio;
      canvas.height = height * ratio;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      context.clearRect(0, 0, width, height);
      context.fillStyle = "rgba(255,255,255,0.04)";

      const offsetX = pointer.current.x * 0.01;
      const offsetY = pointer.current.y * 0.01;

      for (let x = -40; x < width + 40; x += 40) {
        for (let y = -40; y < height + 40; y += 40) {
          context.beginPath();
          context.arc(x + offsetX, y + offsetY, 1.5, 0, Math.PI * 2);
          context.fill();
        }
      }
    };

    const handlePointerMove = (event: PointerEvent) => {
      pointer.current = {
        x: event.clientX - window.innerWidth / 2,
        y: event.clientY - window.innerHeight / 2,
      };
      draw();
    };

    draw();
    window.addEventListener("resize", draw);
    window.addEventListener("pointermove", handlePointerMove, { passive: true });

    return () => {
      window.removeEventListener("resize", draw);
      window.removeEventListener("pointermove", handlePointerMove);
    };
  }, []);

  return <canvas aria-hidden="true" className="dot-grid-canvas" ref={canvasRef} />;
}

export function HeroBackground() {
  return (
    <div aria-hidden="true" className="hero-background">
      <DotGridCanvas />
      <svg className="chart-line chart-line-left" preserveAspectRatio="none" viewBox="0 0 620 360">
        <path d="M0 236 C54 216 76 260 124 228 S197 142 252 166 S323 282 382 224 S465 64 520 104 S588 214 620 164" />
      </svg>
      <svg className="chart-line chart-line-right" preserveAspectRatio="none" viewBox="0 0 620 360">
        <path d="M0 178 C54 124 94 204 142 164 S204 70 260 118 S330 278 390 202 S470 92 526 126 S588 236 620 188" />
      </svg>
      <div className="hero-vignette" />
    </div>
  );
}
