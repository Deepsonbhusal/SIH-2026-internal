import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import {
  useCallback,
  useEffect,
  useState,
} from "react";
import * as THREE from "three";

const TERRAIN_SCALE = 0.06;


/* =========================================================
   LOAD TEXTURE
   ========================================================= */

async function loadTexture(url) {
  console.log("Fetching texture:", url);

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(
      `Texture request failed: ${response.status} ${response.statusText}`
    );
  }

  const blob = await response.blob();

  const objectUrl =
    URL.createObjectURL(blob);

  try {
    const image = await new Promise(
      (resolve, reject) => {
        const img = new Image();

        img.onload = () => {
          resolve(img);
        };

        img.onerror = () => {
          reject(
            new Error(
              "Browser could not decode the terrain texture."
            )
          );
        };

        img.src = objectUrl;
      }
    );

    const texture =
      new THREE.Texture(image);

    texture.colorSpace =
      THREE.SRGBColorSpace;

    texture.wrapS =
      THREE.ClampToEdgeWrapping;

    texture.wrapT =
      THREE.ClampToEdgeWrapping;

    texture.minFilter =
      THREE.LinearFilter;

    texture.magFilter =
      THREE.LinearFilter;

    texture.needsUpdate = true;

    console.log(
      "Texture loaded:",
      image.width,
      "x",
      image.height
    );

    return texture;
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}


/* =========================================================
   LOAD OBJ
   ========================================================= */

async function loadOBJ(url) {
  console.log(
    "Fetching OBJ:",
    url
  );

  const response =
    await fetch(url);

  if (!response.ok) {
    throw new Error(
      `OBJ request failed: ${response.status} ${response.statusText}`
    );
  }

  const text =
    await response.text();

  console.log(
    "OBJ downloaded:",
    text.length,
    "characters"
  );

  if (!text.trim()) {
    throw new Error(
      "OBJ file is empty."
    );
  }

  return text;
}


/* =========================================================
   PARSE OBJ
   ========================================================= */

function parseOBJ(
  text,
  texture
) {
  console.log(
    "Parsing OBJ..."
  );

  const vertices = [];
  const texCoords = [];

  const positions = [];
  const uvs = [];
  const indices = [];

  const vertexMap =
    new Map();

  const lines =
    text.split(/\r?\n/);

  for (const line of lines) {
    const trimmed =
      line.trim();

    if (!trimmed) {
      continue;
    }

    if (
      trimmed.startsWith("#")
    ) {
      continue;
    }

    const parts =
      trimmed.split(/\s+/);

    const type =
      parts[0];

    /* -----------------------------------------------------
       VERTEX
       ----------------------------------------------------- */

    if (type === "v") {
      if (parts.length < 4) {
        continue;
      }

      vertices.push([
        Number(parts[1]),
        Number(parts[2]),
        Number(parts[3]),
      ]);

      continue;
    }

    /* -----------------------------------------------------
       TEXTURE COORDINATE
       ----------------------------------------------------- */

    if (type === "vt") {
      if (parts.length < 3) {
        continue;
      }

      uvs.push(
        Number(parts[1]),
        Number(parts[2])
      );

      texCoords.push([
        Number(parts[1]),
        Number(parts[2]),
      ]);

      continue;
    }

    /* -----------------------------------------------------
       FACE
       ----------------------------------------------------- */

    if (type === "f") {
      const face =
        parts.slice(1);

      if (face.length < 3) {
        continue;
      }

      /*
       * Convert polygons into triangles.
       */

      for (
        let i = 1;
        i < face.length - 1;
        i++
      ) {
        const triangle = [
          face[0],
          face[i],
          face[i + 1],
        ];

        for (
          const vertex of triangle
        ) {
          const indexes =
            vertex.split("/");

          let positionIndex =
            Number(
              indexes[0]
            );

          let uvIndex = 0;

          if (
            indexes.length > 1 &&
            indexes[1] !== ""
          ) {
            uvIndex =
              Number(
                indexes[1]
              );
          }

          /*
           * Handle negative OBJ indexes.
           */

          if (
            positionIndex < 0
          ) {
            positionIndex =
              vertices.length +
              positionIndex +
              1;
          }

          if (
            uvIndex < 0
          ) {
            uvIndex =
              texCoords.length +
              uvIndex +
              1;
          }

          const key =
            `${positionIndex}/${uvIndex}`;

          let newIndex =
            vertexMap.get(key);

          if (
            newIndex ===
            undefined
          ) {
            const position =
              vertices[
                positionIndex - 1
              ];

            const uv =
              uvIndex > 0
                ? texCoords[
                    uvIndex - 1
                  ]
                : [
                    0,
                    0,
                  ];

            if (!position) {
              throw new Error(
                `Invalid OBJ vertex index: ${positionIndex}`
              );
            }

            positions.push(
              position[0],
              position[1],
              position[2]
            );

            uvs.push(
              uv[0],
              uv[1]
            );

            newIndex =
              positions.length /
                3 -
              1;

            vertexMap.set(
              key,
              newIndex
            );
          }

          indices.push(
            newIndex
          );
        }
      }
    }
  }

  console.log(
    "Parsed OBJ:",
    positions.length / 3,
    "vertices"
  );

  console.log(
    "Parsed OBJ:",
    indices.length / 3,
    "triangles"
  );

  if (
    positions.length === 0
  ) {
    throw new Error(
      "OBJ contains no vertices."
    );
  }

  if (
    indices.length === 0
  ) {
    throw new Error(
      "OBJ contains no faces."
    );
  }

  const geometry =
    new THREE.BufferGeometry();

  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(
      positions,
      3
    )
  );

  geometry.setAttribute(
    "uv",
    new THREE.Float32BufferAttribute(
      uvs,
      2
    )
  );

  geometry.setIndex(
    indices
  );

  geometry.computeVertexNormals();

  geometry.computeBoundingBox();

  geometry.computeBoundingSphere();

  const material =
    new THREE.MeshStandardMaterial({
      map: texture,
      side: THREE.DoubleSide,
      roughness: 0.85,
      metalness: 0,
    });

  return new THREE.Mesh(
    geometry,
    material
  );
}


/* =========================================================
   TERRAIN MESH
   ========================================================= */

function TerrainMesh({
  objUrl,
  textureUrl,
  onHeightChange,
  onLoaded,
  onError,
}) {
  const { camera } =
    useThree();

  const [mesh, setMesh] =
    useState(null);

  useEffect(() => {
    let cancelled = false;

    let terrain = null;
    let texture = null;

    async function buildTerrain() {
      try {
        console.log(
          "================================"
        );

        console.log(
          "STARTING TERRAIN LOAD"
        );

        console.log(
          "OBJ URL:",
          objUrl
        );

        console.log(
          "TEXTURE URL:",
          textureUrl
        );

        console.log(
          "================================"
        );

        /*
         * Load both files.
         */

        const [
          objText,
          loadedTexture,
        ] = await Promise.all([
          loadOBJ(objUrl),
          loadTexture(textureUrl),
        ]);

        texture =
          loadedTexture;

        if (cancelled) {
          texture.dispose();
          return;
        }

        /*
         * Create terrain mesh.
         */

        terrain =
          parseOBJ(
            objText,
            texture
          );

        /*
         * Backend OBJ:
         *
         * X = horizontal
         * Y = image row
         * Z = elevation
         *
         * Three.js:
         *
         * X = horizontal
         * Y = up
         * Z = depth
         */

        terrain.rotation.x =
          -Math.PI / 2;

        /*
         * =================================================
         * IMPORTANT FIX
         * =================================================
         *
         * Scale BEFORE calculating the final center.
         *
         * This prevents the terrain from being positioned
         * hundreds of units away from the camera.
         */

        terrain.scale.set(
          TERRAIN_SCALE,
          TERRAIN_SCALE,
          TERRAIN_SCALE
        );

        /*
         * Calculate the bounding box
         * AFTER scaling.
         */

        const box =
          new THREE.Box3().setFromObject(
            terrain
          );

        const center =
          new THREE.Vector3();

        const size =
          new THREE.Vector3();

        box.getCenter(center);
        box.getSize(size);

        console.log(
          "Scaled terrain center:",
          center
        );

        console.log(
          "Scaled terrain size:",
          size
        );

        /*
         * Center terrain in world space.
         */

        terrain.position.x -=
          center.x;

        terrain.position.y -=
          center.y;

        terrain.position.z -=
          center.z;

        /*
         * Camera framing.
         */

        const largestDimension =
          Math.max(
            size.x,
            size.y,
            size.z
          );

        const distance =
          Math.max(
            largestDimension * 1.6,
            8
          );

        camera.position.set(
          distance,
          distance * 0.8,
          distance
        );

        camera.lookAt(
          0,
          0,
          0
        );

        camera.updateProjectionMatrix();

        console.log(
          "Camera position:",
          camera.position
        );

        /*
         * Finish.
         */

        if (cancelled) {
          terrain.geometry.dispose();

          if (
            terrain.material
          ) {
            terrain.material.dispose();
          }

          texture.dispose();

          return;
        }

        setMesh(terrain);

        console.log(
          "================================"
        );

        console.log(
          "3D TERRAIN READY"
        );

        console.log(
          "================================"
        );

        onLoaded();
      } catch (error) {
        console.error(
          "================================"
        );

        console.error(
          "TERRAIN LOAD ERROR"
        );

        console.error(error);

        console.error(
          "================================"
        );

        if (!cancelled) {
          onError(
            error?.message ||
              "Unknown terrain loading error."
          );
        }
      }
    }

    buildTerrain();

    return () => {
      cancelled = true;
    };
  }, [
    objUrl,
    textureUrl,
    camera,
    onLoaded,
    onError,
  ]);

  if (!mesh) {
    return null;
  }

  function handlePointerMove(
    event
  ) {
    /*
     * Since the displayed mesh is scaled,
     * convert the displayed Y back to
     * approximate metric rDSM.
     */

    const metricHeight =
      event.point.y /
      TERRAIN_SCALE;

    onHeightChange(
      Number(
        Math.max(
          0,
          metricHeight
        ).toFixed(2)
      )
    );
  }

  return (
    <primitive
      object={mesh}
      onPointerMove={
        handlePointerMove
      }
      onPointerOut={() =>
        onHeightChange(null)
      }
    />
  );
}


/* =========================================================
   MAIN COMPONENT
   ========================================================= */

function Terrain({
  objUrl,
  textureUrl,
}) {
  const [height, setHeight] =
    useState(null);

  const [loaded, setLoaded] =
    useState(false);

  const [error, setError] =
    useState("");

  /*
   * Stable callbacks.
   */

  const handleLoaded =
    useCallback(() => {
      console.log(
        "Terrain rendered successfully."
      );

      setLoaded(true);
      setError("");
    }, []);

  const handleError =
    useCallback((message) => {
      console.error(
        "Terrain error:",
        message
      );

      setLoaded(false);
      setError(message);
    }, []);

  useEffect(() => {
    setLoaded(false);
    setError("");
    setHeight(null);
  }, [
    objUrl,
    textureUrl,
  ]);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        background: "#151a1d",
      }}
    >

      {height !== null && (
        <div
          style={{
            position: "absolute",
            top: "14px",
            left: "14px",
            zIndex: 20,
            padding: "7px 9px",
            background:
              "rgba(15, 19, 22, 0.82)",
            color: "#eeeeea",
            fontSize: "11px",
            pointerEvents: "none",
          }}
        >
          Metric rDSM{" "}
          <strong>
            {height} m
          </strong>
        </div>
      )}

      {!loaded && !error && (
        <div
          style={{
            position: "absolute",
            bottom: "14px",
            left: "14px",
            zIndex: 20,
            padding: "8px 10px",
            background:
              "rgba(15, 19, 22, 0.86)",
            color: "#eeeeea",
            fontSize: "11px",
            pointerEvents: "none",
          }}
        >
          Loading 3D terrain...
        </div>
      )}

      {error && (
        <div
          style={{
            position: "absolute",
            left: "14px",
            right: "14px",
            bottom: "14px",
            zIndex: 50,
            padding: "10px 12px",
            background:
              "rgba(70, 20, 20, 0.95)",
            color: "#ffffff",
            fontSize: "12px",
            lineHeight: "1.5",
          }}
        >
          <strong>
            3D terrain failed
          </strong>

          <br />

          {error}
        </div>
      )}

      <Canvas
        camera={{
          position: [
            12,
            10,
            12,
          ],
          fov: 45,
          near: 0.1,
          far: 2000,
        }}
      >

        <color
          attach="background"
          args={[
            "#151a1d",
          ]}
        />

        <ambientLight
          intensity={2}
        />

        <directionalLight
          position={[
            10,
            20,
            10,
          ]}
          intensity={3}
        />

        <directionalLight
          position={[
            -10,
            10,
            -10,
          ]}
          intensity={1}
        />

        {objUrl &&
          textureUrl && (
            <TerrainMesh
              key={`${objUrl}-${textureUrl}`}
              objUrl={objUrl}
              textureUrl={textureUrl}
              onHeightChange={
                setHeight
              }
              onLoaded={
                handleLoaded
              }
              onError={
                handleError
              }
            />
          )}

        <OrbitControls
          enableDamping
          dampingFactor={0.08}
          minDistance={2}
          maxDistance={100}
          maxPolarAngle={
            Math.PI / 2.02
          }
          target={[
            0,
            0,
            0,
          ]}
        />

      </Canvas>
    </div>
  );
}

export default Terrain;
