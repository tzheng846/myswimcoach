"use client";

import { Component, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import * as THREE from "three";
import PlaceholderDevice from "./PlaceholderDevice";

const GLB_PATH = "/models/device.glb";

// Largest dimension the fitted model spans in scene units. Slightly under the
// placeholder's footprint so the tilted, rotating model stays fully in frame.
const TARGET_SIZE = 2.2;

// Stand the model's long axis (native +Z, ~2:1 the longest dimension) upright
// so it becomes the vertical spin axis — a clean turntable with no precession.
const ORIENTATION = [-Math.PI / 2, 0, 0];

function GLBDevice() {
  const { scene } = useGLTF(GLB_PATH);

  // Clone so we never mutate the cached gltf (HMR/StrictMode re-renders would
  // otherwise compound the recenter/scale and drift the model each reload).
  const fitted = useMemo(() => {
    const root = scene.clone(true);
    const box = new THREE.Box3().setFromObject(root);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    const scale = TARGET_SIZE / maxDim;

    // Recenter to origin, then uniformly scale to the target footprint.
    root.position.sub(center);
    const wrapper = new THREE.Group();
    wrapper.add(root);
    wrapper.scale.setScalar(scale);
    return wrapper;
  }, [scene]);

  return (
    <group rotation={ORIENTATION}>
      <primitive object={fitted} />
    </group>
  );
}

useGLTF.preload(GLB_PATH);

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

  // Outer static group tilts the whole turntable ~17° back + a slight roll for
  // an angled 3/4 hero view; the inner group spins (about the now-vertical long
  // axis) and adds pointer parallax. Tilting here keeps the spin axis leaning
  // with the model — a stable 3/4 rotation, not a wobble.
  return (
    <group position={[0, -0.1, 0]} scale={1} rotation={[0.3, 0, 0.12]}>
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
