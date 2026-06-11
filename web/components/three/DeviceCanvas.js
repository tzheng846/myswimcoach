"use client";

import dynamic from "next/dynamic";

// Three.js touches window/WebGL — render client-side only.
const DeviceScene = dynamic(() => import("./DeviceScene"), {
  ssr: false,
  loading: () => null,
});

export default function DeviceCanvas() {
  return <DeviceScene />;
}
