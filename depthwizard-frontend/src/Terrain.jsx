import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useMemo } from "react";
import * as THREE from "three";

import dsmData from "./dsmData";

function TerrainMesh() {
  const geometry = useMemo(() => {
    const rows = dsmData.length;
    const cols = dsmData[0].length;

    const min = Math.min(...dsmData.flat());
    const max = Math.max(...dsmData.flat());

    const positions = [];

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        const x = col - (cols - 1) / 2;
        const z = row - (rows - 1) / 2;

        const normalizedHeight =
          max === min ? 0 : (dsmData[row][col] - min) / (max - min);

        const y = normalizedHeight * 2;

        positions.push(x, y, z);
      }
    }

    const indices = [];

    for (let row = 0; row < rows - 1; row++) {
      for (let col = 0; col < cols - 1; col++) {
        const topLeft = row * cols + col;
        const topRight = topLeft + 1;
        const bottomLeft = (row + 1) * cols + col;
        const bottomRight = bottomLeft + 1;

        indices.push(
          topLeft,
          bottomLeft,
          topRight,

          topRight,
          bottomLeft,
          bottomRight
        );
      }
    }

    const geometry = new THREE.BufferGeometry();

    geometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(positions, 3)
    );

    geometry.setIndex(indices);
    geometry.computeVertexNormals();

    return geometry;
  }, []);

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial color="green" side={THREE.DoubleSide} />
    </mesh>
  );
}

function Terrain() {
  return (
    <Canvas camera={{ position: [4, 4, 4], fov: 50 }}>
      <ambientLight intensity={1} />
      <directionalLight position={[5, 5, 5]} intensity={2} />

      <TerrainMesh />

      <OrbitControls />
    </Canvas>
  );
}

export default Terrain;