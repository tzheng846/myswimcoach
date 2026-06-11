"use client";

import { useMemo } from "react";
import * as THREE from "three";

// Stylized stand-in for the encoder unit until the Fusion 360 GLB export
// lands at /models/device.glb — wheel + housing + tether, same silhouette.
export default function PlaceholderDevice() {
  const tetherGeometry = useMemo(() => {
    const curve = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(0, 1.0, 0.22),
      new THREE.Vector3(1.6, 0.7, 0.5),
      new THREE.Vector3(3.2, -0.4, 0.9)
    );
    return new THREE.TubeGeometry(curve, 32, 0.015, 8, false);
  }, []);

  return (
    <group>
      {/* Encoder wheel */}
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 1.0, 0]}>
        <cylinderGeometry args={[1.0, 1.0, 0.18, 64]} />
        <meshStandardMaterial color="#3a4456" metalness={0.55} roughness={0.45} />
      </mesh>
      {/* Wheel rim */}
      <mesh position={[0, 1.0, 0]}>
        <torusGeometry args={[1.0, 0.055, 16, 64]} />
        <meshStandardMaterial color="#5b6678" metalness={0.6} roughness={0.4} />
      </mesh>
      {/* Magnet hub */}
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 1.0, 0.1]}>
        <cylinderGeometry args={[0.16, 0.16, 0.08, 32]} />
        <meshStandardMaterial
          color="#2196f3"
          emissive="#2196f3"
          emissiveIntensity={0.5}
          metalness={0.6}
          roughness={0.4}
        />
      </mesh>
      {/* Spokes */}
      {[0, 1, 2].map((i) => (
        <mesh
          key={i}
          position={[0, 1.0, 0]}
          rotation={[0, 0, (i * Math.PI) / 3]}
        >
          <boxGeometry args={[1.8, 0.07, 0.06]} />
          <meshStandardMaterial color="#46505f" metalness={0.6} roughness={0.4} />
        </mesh>
      ))}

      {/* Housing / mount body */}
      <mesh position={[0, -0.35, -0.05]}>
        <boxGeometry args={[0.9, 1.1, 0.55]} />
        <meshStandardMaterial color="#2b3240" metalness={0.4} roughness={0.55} />
      </mesh>
      {/* Status LED */}
      <mesh position={[0.3, -0.05, 0.24]}>
        <sphereGeometry args={[0.035, 16, 16]} />
        <meshStandardMaterial
          color="#27ae60"
          emissive="#27ae60"
          emissiveIntensity={1.4}
        />
      </mesh>
      {/* Block clamp */}
      <mesh position={[0, -1.05, -0.05]}>
        <boxGeometry args={[1.2, 0.3, 0.8]} />
        <meshStandardMaterial color="#222936" metalness={0.45} roughness={0.55} />
      </mesh>

      {/* Tether trailing toward the swimmer */}
      <mesh geometry={tetherGeometry}>
        <meshStandardMaterial color="#5b8def" metalness={0.2} roughness={0.7} />
      </mesh>
    </group>
  );
}
