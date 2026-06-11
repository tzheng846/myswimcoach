"use client";

import { Component, Suspense, useEffect, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import PlaceholderDevice from "./PlaceholderDevice";

const GLB_PATH = "/models/device.glb";

function GLBDevice() {
  const { scene } = useGLTF(GLB_PATH);
  return <primitive object={scene} />;
}

// useGLTF throws (via suspense) when /models/device.glb is absent —
// catch it and show the placeholder instead.
class ModelBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (this.state.failed) return <PlaceholderDevice />;
    return this.props.children;
  }
}

function Rig({ children }) {
  const group = useRef();
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    const onChange = (e) => setReducedMotion(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useFrame((state, delta) => {
    if (!group.current) return;
    if (!reducedMotion) {
      group.current.rotation.y += delta * 0.25;
    }
    // Pointer parallax — subtle tilt, max ~6°
    const maxTilt = 0.1;
    const targetX = -state.pointer.y * maxTilt;
    const targetZ = state.pointer.x * maxTilt;
    group.current.rotation.x += (targetX - group.current.rotation.x) * 0.05;
    group.current.rotation.z += (targetZ - group.current.rotation.z) * 0.05;
  });

  return (
    <group position={[0, -0.25, 0]} scale={1.05}>
      <group ref={group}>{children}</group>
    </group>
  );
}

export default function DeviceScene() {
  return (
    <Canvas
      camera={{ position: [2.4, 1.4, 3.6], fov: 38 }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true }}
      style={{ background: "transparent" }}
    >
      <ambientLight intensity={0.9} />
      <directionalLight position={[4, 6, 5]} intensity={2.6} color="#ffffff" />
      <directionalLight position={[-5, 2, -3]} intensity={2.0} color="#2196f3" />
      <pointLight position={[0, 0, 4]} intensity={6} color="#5b8def" />
      <Rig>
        <ModelBoundary>
          <Suspense fallback={<PlaceholderDevice />}>
            <GLBDevice />
          </Suspense>
        </ModelBoundary>
      </Rig>
    </Canvas>
  );
}
